import { randomUUID } from "node:crypto";
import { eq, inArray } from "drizzle-orm";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { transactions, users } from "@/drizzle/schema";
import { db } from "@/lib/db";
import {
  PortfolioNotFound,
  addTransactions,
  createPortfolio,
  deleteTransaction,
  findImportByHash,
  listImports,
  listTransactions,
  ownedPortfolio,
  positionsFor,
  recordImport,
  upsertAdjustments,
  type NewTransaction,
} from "@/lib/portfolio/repo";

// Integração com o Postgres (site.md §7.4): **IDOR** — a pessoa B não lê, não apaga e
// não escreve na carteira da pessoa A, nem sabendo os ids. Roda com `RUN_DB_TESTS=1`
// (o CI sobe um Postgres para isso; localmente, o do compose de dev).

const run = process.env.RUN_DB_TESTS === "1";

const PETR4: NewTransaction["asset"] = { symbol: "PETR4", name: "PETROBRAS PN", assetClass: "stock_br", marketRef: "ticker" };

describe.skipIf(!run)("carteira no banco: isolamento entre usuários", () => {
  const a = randomUUID();
  const b = randomUUID();
  let portfolioA = "";
  let transactionA = "";

  beforeAll(async () => {
    await db.insert(users).values([
      { id: a, email: `idor-a-${a}@teste.invalid` },
      { id: b, email: `idor-b-${b}@teste.invalid` },
    ]);
    portfolioA = (await createPortfolio(a, "Carteira A")).id;
    await createPortfolio(b, "Carteira B");
    await addTransactions(
      a,
      portfolioA,
      [{ asset: PETR4, date: "2026-03-12", side: "buy", quantity: "100", price: "38.52", fees: "4.90" }],
      { source: "manual" },
    );
    [{ id: transactionA }] = await db.select({ id: transactions.id }).from(transactions).where(eq(transactions.portfolioId, portfolioA));
  });

  afterAll(async () => {
    await db.delete(users).where(inArray(users.id, [a, b])); // cascata leva carteiras e movimentações
  });

  it("A lê a própria carteira, com os números decifrados", async () => {
    const [linha] = await listTransactions(a, portfolioA);
    expect(linha).toMatchObject({ symbol: "PETR4", quantity: "100", price: "38.52", fees: "4.90" });
    const [posicao] = await positionsFor(a, portfolioA);
    expect(posicao).toMatchObject({ symbol: "PETR4", quantity: "100", cost: "3856.9" });
  });

  it("B não enxerga a carteira de A", async () => {
    expect(await ownedPortfolio(b, portfolioA)).toBeNull();
    await expect(listTransactions(b, portfolioA)).rejects.toBeInstanceOf(PortfolioNotFound);
    await expect(positionsFor(b, portfolioA)).rejects.toBeInstanceOf(PortfolioNotFound);
  });

  it("B não apaga movimentação de A, mesmo com o id", async () => {
    expect(await deleteTransaction(b, transactionA)).toBe(false);
    expect(await listTransactions(a, portfolioA)).toHaveLength(1);
  });

  it("B não escreve na carteira de A", async () => {
    await expect(
      addTransactions(b, portfolioA, [{ asset: PETR4, date: "2026-03-13", side: "sell", quantity: "100", price: "40", fees: "0" }], {
        source: "manual",
      }),
    ).rejects.toBeInstanceOf(PortfolioNotFound);
    await expect(upsertAdjustments(b, portfolioA, [{ asset: PETR4, quantity: "1" }])).rejects.toBeInstanceOf(PortfolioNotFound);
    await expect(
      recordImport(b, portfolioA, { source: "csv", fileSha256: "x", rowsIn: 1, rowsImported: 1, rowsSkipped: 0, warnings: [] }),
    ).rejects.toBeInstanceOf(PortfolioNotFound);
  });

  it("B não vê as importações de A", async () => {
    await recordImport(a, portfolioA, { source: "csv", fileSha256: "arquivo-de-a", rowsIn: 1, rowsImported: 1, rowsSkipped: 0, warnings: [] });
    expect(await listImports(b)).toEqual([]);
    expect(await findImportByHash(b, portfolioA, "arquivo-de-a")).toBeNull();
    expect(await findImportByHash(a, portfolioA, "arquivo-de-a")).not.toBeNull();
  });

  it("reimportar as mesmas linhas não duplica (dedupe por HMAC)", async () => {
    const linhas: NewTransaction[] = [
      { asset: PETR4, date: "2026-04-01", side: "buy", quantity: "10", price: "40.00", fees: "0" },
      { asset: PETR4, date: "2026-04-02", side: "buy", quantity: "5", price: "41", fees: "0" },
    ];
    expect(await addTransactions(a, portfolioA, linhas, { source: "csv", dedupe: true })).toBe(2);
    // Mesma linha com outra formatação ("40" em vez de "40.00") continua sendo a mesma.
    const reenvio = [{ ...linhas[0], price: "40" }, linhas[1]];
    expect(await addTransactions(a, portfolioA, reenvio, { source: "csv", dedupe: true })).toBe(0);
  });

  it("o número no banco está cifrado", async () => {
    const [bruto] = await db.select({ payload: transactions.payload }).from(transactions).where(eq(transactions.id, transactionA));
    expect(bruto.payload).not.toContain("38.52");
  });
});
