import { z } from "zod";
import { assetClass, importSource, incomeKind, marketRef } from "@/drizzle/schema";
import { audit } from "@/lib/audit";
import {
  PortfolioNotFound,
  addIncome,
  addTransactions,
  existingKeys,
  findImportByHash,
  incomeKey,
  ownedPortfolio,
  recordImport,
  transactionKey,
  upsertAdjustments,
  type NewAdjustment,
  type NewIncome,
  type NewTransaction,
} from "@/lib/portfolio/repo";

// Importação (site.md §7.4, plano 5.3): a API lê o arquivo e devolve a **prévia**; o
// `web` marca o que já existe, a pessoa confere e confirma, e só então o `web` grava
// (cifrado). O arquivo não fica em lugar nenhum — da prévia sobra o `sha256`.
//
// A confirmação traz a prévia de volta do navegador. Ela é validada inteira aqui: não
// há nada nela que a pessoa não pudesse lançar à mão na própria carteira, então o que
// importa é o formato e os limites, não a origem.

const decimal = z.string().regex(/^\d{1,15}(\.\d{1,10})?$/, "número inválido");
const isoDate = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);

const assetSchema = z.object({
  symbol: z.string().min(1).max(80),
  name: z.string().min(1).max(200),
  asset_class: z.enum(assetClass.enumValues),
  market_ref: z.enum(marketRef.enumValues),
  known: z.boolean().optional(),
});

const origin = z.object({ file: z.number().int().min(1).max(3), sheet: z.string().max(60), row: z.number().int() });

export const previewTransaction = z.object({
  origin,
  asset: assetSchema,
  date: isoDate,
  side: z.enum(["buy", "sell"]),
  quantity: decimal,
  price: decimal,
  fees: decimal,
  occurrence: z.number().int().min(1).max(1000).default(1),
});

export const previewIncome = z.object({
  origin,
  asset: assetSchema,
  date: isoDate,
  kind: z.enum(incomeKind.enumValues),
  gross: decimal.nullable(),
  net: decimal,
  occurrence: z.number().int().min(1).max(1000).default(1),
});

export const previewPosition = z.object({
  origin,
  asset: assetSchema,
  quantity: decimal.nullable(),
  value_brl: decimal.nullable(),
  avg_price: decimal.nullable(),
});

export const previewFile = z.object({
  file: z.number().int().min(1).max(3),
  kind: z.enum(["b3_posicao", "b3_negociacao", "b3_proventos", "csv"]).nullable(),
  rows_in: z.number().int().min(0),
  rows_ok: z.number().int().min(0),
  rows_skipped: z.number().int().min(0),
});

export const previewWarning = z.object({ origin: origin.nullable().optional(), message: z.string().max(500) });

export const importPreviewSchema = z.object({
  files: z.array(previewFile).min(1).max(3),
  transactions: z.array(previewTransaction).max(20_000),
  income: z.array(previewIncome).max(20_000),
  positions: z.array(previewPosition).max(1_000),
  warnings: z.array(previewWarning).max(400),
});

export type ImportPreview = z.infer<typeof importPreviewSchema>;

/** A prévia como a tela a mostra: com o que já está na carteira marcado. */
export type AnnotatedPreview = ImportPreview & {
  hashes: string[];
  alreadyImportedFiles: number[];
  existing: { transactions: boolean[]; income: boolean[] };
};

export const confirmSchema = z.object({
  preview: importPreviewSchema,
  hashes: z.array(z.string().regex(/^[0-9a-f]{64}$/)).min(1).max(3),
});

const toTransaction = (t: ImportPreview["transactions"][number]): NewTransaction => ({
  asset: { symbol: t.asset.symbol, name: t.asset.name, assetClass: t.asset.asset_class, marketRef: t.asset.market_ref },
  date: t.date,
  side: t.side,
  quantity: t.quantity,
  price: t.price,
  fees: t.fees,
  occurrence: t.occurrence,
});

const toIncome = (i: ImportPreview["income"][number]): NewIncome => ({
  asset: { symbol: i.asset.symbol, name: i.asset.name, assetClass: i.asset.asset_class, marketRef: i.asset.market_ref },
  date: i.date,
  kind: i.kind,
  gross: i.gross,
  net: i.net,
  occurrence: i.occurrence,
});

const toAdjustment = (p: ImportPreview["positions"][number]): NewAdjustment => ({
  asset: { symbol: p.asset.symbol, name: p.asset.name, assetClass: p.asset.asset_class, marketRef: p.asset.market_ref },
  quantity: p.quantity,
  valueBrl: p.quantity ? null : p.value_brl,
  avgPrice: p.avg_price,
});

/** Marca, na prévia, os arquivos e as linhas que já estão na carteira. */
export async function annotatePreview(
  userId: string,
  portfolioId: string,
  preview: ImportPreview,
  hashes: string[],
): Promise<AnnotatedPreview> {
  const found = await Promise.all(hashes.map((h) => findImportByHash(userId, portfolioId, h)));
  const txKeys = preview.transactions.map((t) => transactionKey(toTransaction(t)));
  const incKeys = preview.income.map((i) => incomeKey(toIncome(i)));
  const existing = await existingKeys(userId, portfolioId, { transactions: txKeys, income: incKeys });
  return {
    ...preview,
    hashes,
    alreadyImportedFiles: found.flatMap((row, index) => (row ? [index + 1] : [])),
    existing: {
      transactions: txKeys.map((k) => existing.transactions.has(k)),
      income: incKeys.map((k) => existing.income.has(k)),
    },
  };
}

export type ImportResult = { transactions: number; income: number; positions: number; skipped: number };

const SOURCE_BY_KIND = {
  b3_posicao: "b3_posicao",
  b3_negociacao: "b3_negociacao",
  b3_proventos: "b3_proventos",
  csv: "csv",
} as const satisfies Record<string, (typeof importSource.enumValues)[number]>;

/**
 * Grava uma prévia confirmada: um `import_batches` por arquivo reconhecido, movimentações
 * e proventos com dedupe (reenvio não duplica), posição informada como ajuste.
 */
export async function confirmImport(
  userId: string,
  portfolioId: string,
  input: z.infer<typeof confirmSchema>,
  meta: { ip?: string | null; userAgent?: string | null } = {},
): Promise<ImportResult> {
  const portfolio = await ownedPortfolio(userId, portfolioId);
  if (!portfolio) throw new PortfolioNotFound();
  const { preview, hashes } = input;
  const result: ImportResult = { transactions: 0, income: 0, positions: 0, skipped: 0 };

  for (const file of preview.files) {
    if (!file.kind) continue;
    const hash = hashes[file.file - 1];
    if (!hash) continue;
    const txs = preview.transactions.filter((t) => t.origin.file === file.file).map(toTransaction);
    const inc = preview.income.filter((i) => i.origin.file === file.file).map(toIncome);
    const pos = preview.positions.filter((p) => p.origin.file === file.file).map(toAdjustment);
    const entrySource = file.kind === "csv" ? "csv" : "b3_import";
    const warnings = preview.warnings
      .filter((w) => !w.origin || w.origin.file === file.file)
      .map((w) => (w.origin ? `${w.origin.sheet} linha ${w.origin.row}: ${w.message}` : w.message));

    const batchId = await recordImport(userId, portfolio.id, {
      source: SOURCE_BY_KIND[file.kind],
      fileSha256: hash,
      rowsIn: file.rows_in,
      rowsImported: file.rows_ok,
      rowsSkipped: file.rows_skipped,
      warnings,
    });
    const addedTx = await addTransactions(userId, portfolio.id, txs, { source: entrySource, importBatchId: batchId, dedupe: true });
    const addedInc = await addIncome(userId, portfolio.id, inc, { source: entrySource, importBatchId: batchId });
    const adjusted = await upsertAdjustments(userId, portfolio.id, pos, { source: entrySource });
    result.transactions += addedTx;
    result.income += addedInc;
    result.positions += adjusted;
    result.skipped += txs.length - addedTx + (inc.length - addedInc);
  }

  // Sem números nem ativos no log de auditoria: só o que aconteceu e quanto.
  await audit("import", {
    userId,
    ...meta,
    details: { portfolio_id: portfolio.id, files: preview.files.map((f) => f.kind ?? "desconhecido").join(","), ...result },
  });
  return result;
}
