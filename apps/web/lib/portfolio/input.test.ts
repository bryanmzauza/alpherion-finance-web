import { describe, expect, it } from "vitest";
import { summarizeIncome } from "@/lib/portfolio/income";
import { manualTransactionSchema, parseDecimalInput } from "@/lib/portfolio/input";

describe("número digitado", () => {
  it.each([
    ["38,52", "38.52"],
    ["1.234,56", "1234.56"],
    ["R$ 1.234,56", "1234.56"],
    ["38.52", "38.52"],
    ["1.234.567", "1234567"],
    ["0,00000001", "0.00000001"],
    ["", null],
    ["abc", null],
    ["-5", null],
  ])("%s → %s", (raw, expected) => {
    expect(parseDecimalInput(raw)).toBe(expected);
  });
});

describe("lançamento manual", () => {
  const base = {
    asset: { symbol: "PETR4", name: "PETROBRAS", asset_class: "stock_br", market_ref: "ticker" },
    date: "2026-03-12",
    side: "buy",
    quantity: "100",
    price: "38,52",
  };

  it("normaliza os números e põe taxa zero por padrão", () => {
    const parsed = manualTransactionSchema.parse(base);
    expect(parsed).toMatchObject({ price: "38.52", fees: "0" });
  });

  it("recusa quantidade zero, data futura e classe inventada", () => {
    expect(manualTransactionSchema.safeParse({ ...base, quantity: "0" }).success).toBe(false);
    expect(manualTransactionSchema.safeParse({ ...base, date: "2999-01-01" }).success).toBe(false);
    expect(
      manualTransactionSchema.safeParse({ ...base, asset: { ...base.asset, asset_class: "acao-top" } }).success,
    ).toBe(false);
  });
});

describe("resumo de proventos", () => {
  it("soma por ano e por ativo; yield on cost sobre 12 meses e custo atual", () => {
    const rows = [
      { assetId: "a", symbol: "PETR4", date: "2026-03-20", net: "108" },
      { assetId: "a", symbol: "PETR4", date: "2025-03-20", net: "50" },
      { assetId: "b", symbol: "HGLG11", date: "2026-04-15", net: "33" },
    ];
    const summary = summarizeIncome(rows, new Map([["a", 3000], ["b", null]]), new Date("2026-09-23T12:00:00Z"));
    expect(summary.byYear).toEqual([
      { year: "2026", net: 141 },
      { year: "2025", net: 50 },
    ]);
    const petr = summary.byAsset.find((a) => a.symbol === "PETR4")!;
    expect(petr).toMatchObject({ net12m: 108, netTotal: 158 });
    expect(petr.yieldOnCost).toBeCloseTo(0.036);
    expect(summary.byAsset.find((a) => a.symbol === "HGLG11")!.yieldOnCost).toBeNull();
    expect(summary.total12m).toBe(141);
  });
});
