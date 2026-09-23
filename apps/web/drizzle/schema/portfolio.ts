import { boolean, date, index, integer, jsonb, smallint, text, timestamp, uniqueIndex, uuid } from "drizzle-orm/pg-core";
import { app } from "./app";
import { users } from "./auth";

// Carteira, movimentações e proventos recebidos (site.md §4.2, §7.4).
//
// **O que é cifrado.** Quantidade, preço, taxas, valores e observação de cada linha vão
// num único campo `payload` cifrado na aplicação (AES-256-GCM, `lib/crypto.ts`) com a
// `key_version` da chave usada. Um dump do banco mostra que alguém comprou PETR4 em
// 12/03, mas não quanto nem a que preço. Ficam em claro só o que as consultas e o dedupe
// precisam: carteira, ativo, data, tipo e origem.
//
// **Dedupe.** `external_key` é um HMAC (com chave derivada da de cifra) de ativo, data,
// tipo, quantidade e preço. Um hash simples dessas colunas seria reversível por força
// bruta — quantidade e preço têm poucas combinações plausíveis — e vazaria o que o
// `payload` esconde.
//
// **Posição não é tabela.** É derivada em memória (`lib/positions.ts`) de `transactions`
// + `position_adjustments`, porque os números estão cifrados (§7.4).

export const assetClass = app.enum("asset_class", [
  "crypto",
  "stablecoin",
  "stock_br",
  "bdr",
  "etf_br",
  "fii",
  "fixed_income",
  "treasury",
  "other",
]);

/** Como o ativo se liga ao schema `market` (pela API): ticker, id do CoinGecko ou slug do título. */
export const marketRef = app.enum("market_ref", ["ticker", "coingecko_id", "treasury_slug", "none"]);

export const assets = app.table(
  "assets",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    symbol: text("symbol").notNull(),
    name: text("name").notNull(),
    assetClass: assetClass("asset_class").notNull(),
    marketRef: marketRef("market_ref").notNull().default("ticker"),
    currency: text("currency").notNull().default("BRL"),
    /** Ativo → fatores de risco (Etapa 6). Padrão por classe; ver `lib/factor-map.ts`. */
    factorMap: jsonb("factor_map").$type<Record<string, number>>(),
    active: boolean("active").notNull().default(true),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [uniqueIndex("assets_class_symbol_idx").on(t.assetClass, t.symbol)],
);

export const portfolios = app.table(
  "portfolios",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    userId: uuid("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    name: text("name").notNull(),
    baseCurrency: text("base_currency").notNull().default("BRL"),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [index("portfolios_user_id_idx").on(t.userId)],
);

export const importSource = app.enum("import_source", ["csv", "b3_posicao", "b3_negociacao", "b3_proventos"]);
export const importStatus = app.enum("import_status", ["imported", "failed"]);

/** Um envio de arquivo. **Sem o arquivo**: só o hash (dedupe de reenvio) e as contagens. */
export const importBatches = app.table(
  "import_batches",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    userId: uuid("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    portfolioId: uuid("portfolio_id")
      .notNull()
      .references(() => portfolios.id, { onDelete: "cascade" }),
    source: importSource("source").notNull(),
    fileSha256: text("file_sha256").notNull(),
    rowsIn: integer("rows_in").notNull(),
    rowsImported: integer("rows_imported").notNull(),
    rowsSkipped: integer("rows_skipped").notNull(),
    /** Avisos por linha, sem dado pessoal ("linha 12: ativo XPTO11 não encontrado"). */
    warnings: jsonb("warnings").$type<string[]>(),
    status: importStatus("status").notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [
    index("import_batches_user_id_idx").on(t.userId),
    // O mesmo arquivo na mesma carteira não entra duas vezes.
    uniqueIndex("import_batches_portfolio_file_idx").on(t.portfolioId, t.fileSha256),
  ],
);

export const transactionSide = app.enum("transaction_side", ["buy", "sell"]);
export const entrySource = app.enum("entry_source", ["manual", "csv", "b3_import", "b3_api"]);

const encrypted = {
  /** JSON cifrado (AES-256-GCM) com os números da linha — ver `lib/crypto.ts`. */
  payload: text("payload").notNull(),
  keyVersion: smallint("key_version").notNull(),
};

export const transactions = app.table(
  "transactions",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    portfolioId: uuid("portfolio_id")
      .notNull()
      .references(() => portfolios.id, { onDelete: "cascade" }),
    assetId: uuid("asset_id")
      .notNull()
      .references(() => assets.id),
    date: date("date").notNull(),
    side: transactionSide("side").notNull(),
    ...encrypted,
    source: entrySource("source").notNull(),
    importBatchId: uuid("import_batch_id").references(() => importBatches.id, { onDelete: "set null" }),
    externalKey: text("external_key"),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [
    index("transactions_portfolio_date_idx").on(t.portfolioId, t.date),
    uniqueIndex("transactions_portfolio_external_key_idx").on(t.portfolioId, t.externalKey),
  ],
);

export const incomeKind = app.enum("income_kind", ["dividend", "jcp", "fii_income", "interest", "other"]);

/** Provento **recebido** pelo usuário (≠ `market.corporate_actions`, o anunciado pelo emissor). */
export const incomeEvents = app.table(
  "income_events",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    portfolioId: uuid("portfolio_id")
      .notNull()
      .references(() => portfolios.id, { onDelete: "cascade" }),
    assetId: uuid("asset_id")
      .notNull()
      .references(() => assets.id),
    date: date("date").notNull(),
    kind: incomeKind("kind").notNull(),
    ...encrypted,
    source: entrySource("source").notNull(),
    importBatchId: uuid("import_batch_id").references(() => importBatches.id, { onDelete: "set null" }),
    externalKey: text("external_key"),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [
    index("income_events_portfolio_date_idx").on(t.portfolioId, t.date),
    uniqueIndex("income_events_portfolio_external_key_idx").on(t.portfolioId, t.externalKey),
  ],
);

/**
 * Posição informada sem histórico (o "adicionar à mão", e a posição importada da B3).
 * O `payload` cifrado traz `quantity` **ou** `value_brl`, e opcionalmente `avg_price` —
 * a regra do "ou" é validada na aplicação (o banco não enxerga o conteúdo cifrado).
 */
export const positionAdjustments = app.table(
  "position_adjustments",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    portfolioId: uuid("portfolio_id")
      .notNull()
      .references(() => portfolios.id, { onDelete: "cascade" }),
    assetId: uuid("asset_id")
      .notNull()
      .references(() => assets.id),
    ...encrypted,
    source: entrySource("source").notNull().default("manual"),
    updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [uniqueIndex("position_adjustments_portfolio_asset_idx").on(t.portfolioId, t.assetId)],
);
