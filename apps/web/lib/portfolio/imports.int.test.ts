import { randomUUID } from "node:crypto";
import { inArray } from "drizzle-orm";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { users } from "@/drizzle/schema";
import { db } from "@/lib/db";
import { annotatePreview, confirmImport, confirmSchema, type ImportPreview } from "@/lib/portfolio/imports";
import { PortfolioNotFound, createPortfolio, listIncome, listTransactions, positionsFor } from "@/lib/portfolio/repo";

// Confirmação de importação contra o Postgres (`RUN_DB_TESTS=1`), com a prévia no
// formato que a API devolve para as fixtures de `apps/api/tests/fixtures/b3/`.

const run = process.env.RUN_DB_TESTS === "1";

const PETR4 = { symbol: "PETR4", name: "PETROBRAS", asset_class: "stock_br", market_ref: "ticker", known: true } as const;
const IPCA = { symbol: "ipca-2035-05-15", name: "Tesouro IPCA+ 2035", asset_class: "treasury", market_ref: "treasury_slug", known: true } as const;

const PREVIEW: ImportPreview = {
  files: [
    { file: 1, kind: "b3_negociacao", rows_in: 3, rows_ok: 3, rows_skipped: 0 },
    { file: 2, kind: "b3_proventos", rows_in: 1, rows_ok: 1, rows_skipped: 0 },
    { file: 3, kind: "b3_posicao", rows_in: 2, rows_ok: 2, rows_skipped: 0 },
  ],
  transactions: [
    { origin: { file: 1, sheet: "Negociação", row: 6 }, asset: PETR4, date: "2024-01-10", side: "buy", quantity: "100", price: "30.0", fees: "0", occurrence: 1 },
    { origin: { file: 1, sheet: "Negociação", row: 7 }, asset: PETR4, date: "2024-03-15", side: "buy", quantity: "50", price: "34.0", fees: "0", occurrence: 1 },
    // Segunda execução idêntica no mesmo dia: outro negócio, não repetição.
    { origin: { file: 1, sheet: "Negociação", row: 8 }, asset: PETR4, date: "2024-03-15", side: "buy", quantity: "50", price: "34.0", fees: "0", occurrence: 2 },
  ],
  income: [
    { origin: { file: 2, sheet: "Movimentação", row: 2 }, asset: PETR4, date: "2024-03-20", kind: "jcp", gross: null, net: "42.5", occurrence: 1 },
  ],
  positions: [
    { origin: { file: 3, sheet: "Acoes", row: 6 }, asset: PETR4, quantity: "180", value_brl: null, avg_price: null },
    { origin: { file: 3, sheet: "Tesouro Direto", row: 2 }, asset: IPCA, quantity: "1.5", value_brl: null, avg_price: "2000.000000" },
  ],
  warnings: [{ origin: null, message: "o extrato de negociação da B3 não traz taxas" }],
};
const HASHES = ["a".repeat(64), "b".repeat(64), "c".repeat(64)];

describe.skipIf(!run)("importação confirmada", () => {
  const a = randomUUID();
  const b = randomUUID();
  let portfolioA = "";

  beforeAll(async () => {
    await db.insert(users).values([
      { id: a, email: `imp-a-${a}@teste.invalid` },
      { id: b, email: `imp-b-${b}@teste.invalid` },
    ]);
    portfolioA = (await createPortfolio(a, "A")).id;
    await createPortfolio(b, "B");
  });

  afterAll(async () => {
    await db.delete(users).where(inArray(users.id, [a, b]));
  });

  it("o JSON da prévia passa na validação da confirmação", () => {
    expect(confirmSchema.safeParse({ preview: PREVIEW, hashes: HASHES }).success).toBe(true);
  });

  it("grava tudo, com as duas execuções idênticas, e a posição do arquivo prevalece", async () => {
    const result = await confirmImport(a, portfolioA, { preview: PREVIEW, hashes: HASHES });
    expect(result).toEqual({ transactions: 3, income: 1, positions: 2, skipped: 0 });
    expect(await listTransactions(a, portfolioA)).toHaveLength(3);
    expect(await listIncome(a, portfolioA)).toMatchObject([{ kind: "jcp", gross: null, net: "42.5" }]);

    const positions = await positionsFor(a, portfolioA);
    const petr = positions.find((p) => p.symbol === "PETR4")!;
    // Quantidade do arquivo de posição (180), preço médio do histórico: (3000 + 3400) / 200.
    expect(petr).toMatchObject({ quantity: "180", avgPrice: "32" });
    expect(positions.find((p) => p.symbol === "ipca-2035-05-15")).toMatchObject({ quantity: "1.5", avgPrice: "2000" });
  });

  it("reenviar os mesmos arquivos não duplica nada e a prévia mostra o que já existe", async () => {
    const annotated = await annotatePreview(a, portfolioA, PREVIEW, HASHES);
    expect(annotated.alreadyImportedFiles).toEqual([1, 2, 3]);
    expect(annotated.existing.transactions).toEqual([true, true, true]);
    expect(annotated.existing.income).toEqual([true]);

    const again = await confirmImport(a, portfolioA, { preview: PREVIEW, hashes: HASHES });
    expect(again).toMatchObject({ transactions: 0, income: 0, skipped: 4 });
    expect(await listTransactions(a, portfolioA)).toHaveLength(3);
  });

  it("B não importa para a carteira de A", async () => {
    await expect(confirmImport(b, portfolioA, { preview: PREVIEW, hashes: HASHES })).rejects.toBeInstanceOf(
      PortfolioNotFound,
    );
    await expect(annotatePreview(b, portfolioA, PREVIEW, HASHES)).rejects.toBeInstanceOf(PortfolioNotFound);
  });
});
