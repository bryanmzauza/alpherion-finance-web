import { and, asc, desc, eq, inArray, sql } from "drizzle-orm";
import {
  assets,
  importBatches,
  incomeEvents,
  portfolios,
  positionAdjustments,
  transactions,
  type assetClass,
  type entrySource,
  type importSource,
  type incomeKind,
  type marketRef,
} from "@/drizzle/schema";
import { audit } from "@/lib/audit";
import { decryptJson, encryptJson, keyedHash } from "@/lib/crypto";
import { db } from "@/lib/db";
import { defaultFactorMap } from "@/lib/factor-map";
import { derivePositions, type Position } from "@/lib/positions";

// Acesso à carteira (site.md §4.2, §7.4). **Toda função recebe o `userId` da sessão** e
// filtra por ele — nunca por um id vindo do cliente sem esse filtro. Uma carteira de
// outra pessoa, para esta camada, simplesmente não existe (IDOR: `repo.int.test.ts`).
//
// A cifra e o dedupe moram aqui, e só aqui: quem chama grava e lê números em claro.

type AssetClass = (typeof assetClass.enumValues)[number];
type MarketRef = (typeof marketRef.enumValues)[number];
type EntrySource = (typeof entrySource.enumValues)[number];
type ImportSource = (typeof importSource.enumValues)[number];
type IncomeKind = (typeof incomeKind.enumValues)[number];

export type TransactionPayload = { quantity: string; price: string; fees: string; note?: string | null };
/** Bruto só quando a fonte traz (a B3 manda o JCP já líquido de IR). */
export type IncomePayload = { gross: string | null; net: string };
export type AdjustmentPayload = { quantity?: string | null; valueBrl?: string | null; avgPrice?: string | null; note?: string | null };

export type AssetRef = { symbol: string; name: string; assetClass: AssetClass; marketRef: MarketRef };

const ctx = (table: string, portfolioId: string) => `${table}:${portfolioId}`;

// --- carteira ---------------------------------------------------------------

export async function getPortfolio(userId: string) {
  const [row] = await db
    .select()
    .from(portfolios)
    .where(eq(portfolios.userId, userId))
    .orderBy(asc(portfolios.createdAt))
    .limit(1);
  return row ?? null;
}

/** A carteira, se for desta pessoa; `null` para qualquer outra (inclusive de outro usuário). */
export async function ownedPortfolio(userId: string, portfolioId: string) {
  const [row] = await db
    .select()
    .from(portfolios)
    .where(and(eq(portfolios.id, portfolioId), eq(portfolios.userId, userId)))
    .limit(1);
  return row ?? null;
}

export async function createPortfolio(userId: string, name: string, meta: { ip?: string | null; userAgent?: string | null } = {}) {
  const existing = await getPortfolio(userId);
  if (existing) return existing; // uma por usuário no v1 (§4.2)
  const [row] = await db.insert(portfolios).values({ userId, name }).returning();
  await audit("portfolio_create", { userId, ...meta, details: { portfolio_id: row.id } });
  return row;
}

// --- ativos (catálogo compartilhado, sem dado de usuário) -------------------

export async function ensureAssets(refs: AssetRef[]): Promise<Map<string, string>> {
  const unique = new Map(refs.map((r) => [assetKey(r), { ...r, symbol: canonicalSymbol(r) }]));
  if (unique.size === 0) return new Map();
  await db
    .insert(assets)
    .values(
      [...unique.values()].map((r) => ({
        symbol: r.symbol,
        name: r.name.slice(0, 200),
        assetClass: r.assetClass,
        marketRef: r.marketRef,
        factorMap: defaultFactorMap(r.symbol, r.assetClass),
      })),
    )
    .onConflictDoNothing({ target: [assets.assetClass, assets.symbol] });
  const rows = await db
    .select({ id: assets.id, symbol: assets.symbol, assetClass: assets.assetClass })
    .from(assets)
    .where(inArray(assets.symbol, [...new Set([...unique.values()].map((r) => r.symbol))]));
  return new Map(rows.map((r) => [`${r.assetClass}:${r.symbol}`, r.id]));
}

/** Classes cujo símbolo é ticker da B3 (caixa alta). Slug do Tesouro e id do CoinGecko são minúsculos. */
const TICKER_CLASSES = new Set<AssetClass>(["stock_br", "bdr", "etf_br", "fii"]);

export const canonicalSymbol = (ref: Pick<AssetRef, "assetClass" | "symbol">) =>
  TICKER_CLASSES.has(ref.assetClass) ? ref.symbol.trim().toUpperCase() : ref.symbol.trim();

export const assetKey = (ref: Pick<AssetRef, "assetClass" | "symbol">) => `${ref.assetClass}:${canonicalSymbol(ref)}`;

// --- movimentações ----------------------------------------------------------

export type NewTransaction = {
  asset: AssetRef;
  date: string;
  side: "buy" | "sell";
  /** 2, 3… para a segunda, terceira linha idêntica do mesmo arquivo (negócios distintos). */
  occurrence?: number;
} & TransactionPayload;

/**
 * Chave de dedupe de uma movimentação importada: HMAC de ativo, data, tipo, qtd e preço,
 * mais a ocorrência quando é a segunda linha idêntica do arquivo (duas execuções iguais
 * no mesmo dia são dois negócios; reimportar o arquivo gera as mesmas ocorrências).
 */
export const transactionKey = (t: NewTransaction) =>
  keyedHash([
    assetKey(t.asset),
    t.date,
    t.side,
    normalizeNumber(t.quantity),
    normalizeNumber(t.price),
    ...((t.occurrence ?? 1) > 1 ? [`#${t.occurrence}`] : []),
  ]);

export async function addTransactions(
  userId: string,
  portfolioId: string,
  rows: NewTransaction[],
  opts: { source: EntrySource; importBatchId?: string | null; dedupe?: boolean },
): Promise<number> {
  const portfolio = await ownedPortfolio(userId, portfolioId);
  if (!portfolio) throw new PortfolioNotFound();
  if (rows.length === 0) return 0;
  const ids = await ensureAssets(rows.map((r) => r.asset));
  const values = rows.map((r) => {
    const encrypted = encryptJson(
      { quantity: r.quantity, price: r.price, fees: r.fees, note: r.note ?? null } satisfies TransactionPayload,
      ctx("transactions", portfolio.id),
    );
    return {
      portfolioId: portfolio.id,
      assetId: ids.get(assetKey(r.asset))!,
      date: r.date,
      side: r.side,
      payload: encrypted.payload,
      keyVersion: encrypted.keyVersion,
      source: opts.source,
      importBatchId: opts.importBatchId ?? null,
      externalKey: opts.dedupe ? transactionKey(r) : null,
    };
  });
  const inserted = await db.insert(transactions).values(values).onConflictDoNothing().returning({ id: transactions.id });
  return inserted.length;
}

export async function listTransactions(userId: string, portfolioId: string) {
  const portfolio = await ownedPortfolio(userId, portfolioId);
  if (!portfolio) throw new PortfolioNotFound();
  const rows = await db
    .select({
      id: transactions.id,
      date: transactions.date,
      side: transactions.side,
      source: transactions.source,
      payload: transactions.payload,
      keyVersion: transactions.keyVersion,
      assetId: assets.id,
      symbol: assets.symbol,
      name: assets.name,
      assetClass: assets.assetClass,
    })
    .from(transactions)
    .innerJoin(assets, eq(assets.id, transactions.assetId))
    .where(eq(transactions.portfolioId, portfolio.id))
    .orderBy(desc(transactions.date), desc(transactions.createdAt));
  return rows.map(({ payload, keyVersion, ...rest }) => ({
    ...rest,
    ...decryptJson<TransactionPayload>({ payload, keyVersion }, ctx("transactions", portfolio.id)),
  }));
}

/** Apaga uma movimentação **desta pessoa**; de outra, não acha e devolve `false`. */
export async function deleteTransaction(userId: string, transactionId: string, meta: { ip?: string | null } = {}): Promise<boolean> {
  const deleted = await db
    .delete(transactions)
    .where(
      and(
        eq(transactions.id, transactionId),
        inArray(transactions.portfolioId, db.select({ id: portfolios.id }).from(portfolios).where(eq(portfolios.userId, userId))),
      ),
    )
    .returning({ id: transactions.id });
  if (deleted.length > 0) await audit("transaction_delete", { userId, ip: meta.ip, details: { transaction_id: transactionId } });
  return deleted.length > 0;
}

// --- proventos recebidos ----------------------------------------------------

export type NewIncome = { asset: AssetRef; date: string; kind: IncomeKind; occurrence?: number } & IncomePayload;

export const incomeKey = (i: NewIncome) =>
  keyedHash([
    assetKey(i.asset),
    i.date,
    i.kind,
    i.gross === null ? "" : normalizeNumber(i.gross),
    normalizeNumber(i.net),
    ...((i.occurrence ?? 1) > 1 ? [`#${i.occurrence}`] : []),
  ]);

export async function addIncome(
  userId: string,
  portfolioId: string,
  rows: NewIncome[],
  opts: { source: EntrySource; importBatchId?: string | null },
): Promise<number> {
  const portfolio = await ownedPortfolio(userId, portfolioId);
  if (!portfolio) throw new PortfolioNotFound();
  if (rows.length === 0) return 0;
  const ids = await ensureAssets(rows.map((r) => r.asset));
  const inserted = await db
    .insert(incomeEvents)
    .values(
      rows.map((r) => {
        const encrypted = encryptJson({ gross: r.gross, net: r.net } satisfies IncomePayload, ctx("income_events", portfolio.id));
        return {
          portfolioId: portfolio.id,
          assetId: ids.get(assetKey(r.asset))!,
          date: r.date,
          kind: r.kind,
          payload: encrypted.payload,
          keyVersion: encrypted.keyVersion,
          source: opts.source,
          importBatchId: opts.importBatchId ?? null,
          externalKey: incomeKey(r),
        };
      }),
    )
    .onConflictDoNothing()
    .returning({ id: incomeEvents.id });
  return inserted.length;
}

export async function listIncome(userId: string, portfolioId: string) {
  const portfolio = await ownedPortfolio(userId, portfolioId);
  if (!portfolio) throw new PortfolioNotFound();
  const rows = await db
    .select({
      id: incomeEvents.id,
      date: incomeEvents.date,
      kind: incomeEvents.kind,
      payload: incomeEvents.payload,
      keyVersion: incomeEvents.keyVersion,
      assetId: assets.id,
      symbol: assets.symbol,
      name: assets.name,
      assetClass: assets.assetClass,
    })
    .from(incomeEvents)
    .innerJoin(assets, eq(assets.id, incomeEvents.assetId))
    .where(eq(incomeEvents.portfolioId, portfolio.id))
    .orderBy(desc(incomeEvents.date));
  return rows.map(({ payload, keyVersion, ...rest }) => ({
    ...rest,
    ...decryptJson<IncomePayload>({ payload, keyVersion }, ctx("income_events", portfolio.id)),
  }));
}

// --- ajustes (posição informada) --------------------------------------------

export type NewAdjustment = { asset: AssetRef } & AdjustmentPayload;

export async function upsertAdjustments(
  userId: string,
  portfolioId: string,
  rows: NewAdjustment[],
  opts: { source: EntrySource } = { source: "manual" },
): Promise<number> {
  const portfolio = await ownedPortfolio(userId, portfolioId);
  if (!portfolio) throw new PortfolioNotFound();
  if (rows.length === 0) return 0;
  for (const row of rows) {
    const hasQuantity = Boolean(row.quantity);
    const hasValue = Boolean(row.valueBrl);
    if (hasQuantity === hasValue) throw new Error("ajuste precisa de quantidade OU de valor em reais");
  }
  const ids = await ensureAssets(rows.map((r) => r.asset));
  const values = rows.map((r) => {
    const encrypted = encryptJson(
      { quantity: r.quantity ?? null, valueBrl: r.valueBrl ?? null, avgPrice: r.avgPrice ?? null, note: r.note ?? null } satisfies AdjustmentPayload,
      ctx("position_adjustments", portfolio.id),
    );
    return {
      portfolioId: portfolio.id,
      assetId: ids.get(assetKey(r.asset))!,
      payload: encrypted.payload,
      keyVersion: encrypted.keyVersion,
      source: opts.source,
      updatedAt: new Date(),
    };
  });
  await db
    .insert(positionAdjustments)
    .values(values)
    .onConflictDoUpdate({
      target: [positionAdjustments.portfolioId, positionAdjustments.assetId],
      set: {
        payload: sql`excluded.payload`,
        keyVersion: sql`excluded.key_version`,
        source: sql`excluded.source`,
        updatedAt: sql`excluded.updated_at`,
      },
    });
  return values.length;
}

async function listAdjustments(portfolioId: string) {
  const rows = await db
    .select({
      assetId: positionAdjustments.assetId,
      payload: positionAdjustments.payload,
      keyVersion: positionAdjustments.keyVersion,
    })
    .from(positionAdjustments)
    .where(eq(positionAdjustments.portfolioId, portfolioId));
  return rows.map((r) => ({
    assetId: r.assetId,
    ...decryptJson<AdjustmentPayload>({ payload: r.payload, keyVersion: r.keyVersion }, ctx("position_adjustments", portfolioId)),
  }));
}

// --- posições ---------------------------------------------------------------

export type HeldPosition = Position & { symbol: string; name: string; assetClass: AssetClass; marketRef: MarketRef };

export async function positionsFor(userId: string, portfolioId: string): Promise<HeldPosition[]> {
  const portfolio = await ownedPortfolio(userId, portfolioId);
  if (!portfolio) throw new PortfolioNotFound();
  const [txs, adjustments] = await Promise.all([listTransactions(userId, portfolio.id), listAdjustments(portfolio.id)]);
  const positions = derivePositions(
    txs.map((t) => ({ assetId: t.assetId, date: t.date, side: t.side, quantity: t.quantity, price: t.price, fees: t.fees })),
    adjustments.map((a) => ({ assetId: a.assetId, quantity: a.quantity, valueBrl: a.valueBrl, avgPrice: a.avgPrice })),
  );
  if (positions.length === 0) return [];
  const info = await db
    .select({ id: assets.id, symbol: assets.symbol, name: assets.name, assetClass: assets.assetClass, marketRef: assets.marketRef })
    .from(assets)
    .where(inArray(assets.id, positions.map((p) => p.assetId)));
  const byId = new Map(info.map((a) => [a.id, a]));
  return positions.map((p) => {
    const asset = byId.get(p.assetId)!;
    return { ...p, symbol: asset.symbol, name: asset.name, assetClass: asset.assetClass, marketRef: asset.marketRef };
  });
}

// --- importação -------------------------------------------------------------

/** Quantas destas chaves já existem na carteira (para a prévia dizer "N já importadas"). */
export async function existingKeys(userId: string, portfolioId: string, keys: { transactions: string[]; income: string[] }) {
  const portfolio = await ownedPortfolio(userId, portfolioId);
  if (!portfolio) throw new PortfolioNotFound();
  const [tx, inc] = await Promise.all([
    keys.transactions.length
      ? db
          .select({ key: transactions.externalKey })
          .from(transactions)
          .where(and(eq(transactions.portfolioId, portfolio.id), inArray(transactions.externalKey, keys.transactions)))
      : [],
    keys.income.length
      ? db
          .select({ key: incomeEvents.externalKey })
          .from(incomeEvents)
          .where(and(eq(incomeEvents.portfolioId, portfolio.id), inArray(incomeEvents.externalKey, keys.income)))
      : [],
  ]);
  return {
    transactions: new Set(tx.map((r) => r.key).filter((k): k is string => k !== null)),
    income: new Set(inc.map((r) => r.key).filter((k): k is string => k !== null)),
  };
}

export async function findImportByHash(userId: string, portfolioId: string, fileSha256: string) {
  const [row] = await db
    .select({ id: importBatches.id, createdAt: importBatches.createdAt })
    .from(importBatches)
    .where(and(eq(importBatches.userId, userId), eq(importBatches.portfolioId, portfolioId), eq(importBatches.fileSha256, fileSha256)))
    .limit(1);
  return row ?? null;
}

export async function recordImport(
  userId: string,
  portfolioId: string,
  batch: { source: ImportSource; fileSha256: string; rowsIn: number; rowsImported: number; rowsSkipped: number; warnings: string[] },
) {
  const portfolio = await ownedPortfolio(userId, portfolioId);
  if (!portfolio) throw new PortfolioNotFound();
  // O mesmo arquivo de novo (índice único carteira + sha256) reaproveita o lote: o
  // dedupe das linhas é que decide o que entra.
  const [row] = await db
    .insert(importBatches)
    .values({ userId, portfolioId: portfolio.id, status: "imported", ...batch, warnings: batch.warnings.slice(0, 200) })
    .onConflictDoNothing({ target: [importBatches.portfolioId, importBatches.fileSha256] })
    .returning({ id: importBatches.id });
  if (row) return row.id;
  const existing = await findImportByHash(userId, portfolio.id, batch.fileSha256);
  if (!existing) throw new PortfolioNotFound();
  return existing.id;
}

export async function listImports(userId: string) {
  return db
    .select({
      id: importBatches.id,
      source: importBatches.source,
      rowsIn: importBatches.rowsIn,
      rowsImported: importBatches.rowsImported,
      rowsSkipped: importBatches.rowsSkipped,
      createdAt: importBatches.createdAt,
    })
    .from(importBatches)
    .where(eq(importBatches.userId, userId))
    .orderBy(desc(importBatches.createdAt));
}

export class PortfolioNotFound extends Error {
  constructor() {
    super("carteira não encontrada");
    this.name = "PortfolioNotFound";
  }
}

/** "38,50" e "38.500" viram "38.5": o dedupe não pode depender da formatação da planilha. */
export function normalizeNumber(value: string): string {
  const text = value.trim().replace(",", ".");
  if (!/^-?\d+(\.\d+)?$/.test(text)) return text;
  const [int, frac = ""] = text.split(".");
  const cleanFrac = frac.replace(/0+$/, "");
  return `${String(BigInt(int))}${cleanFrac ? `.${cleanFrac}` : ""}`;
}
