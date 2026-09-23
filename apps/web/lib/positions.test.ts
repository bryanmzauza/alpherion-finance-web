import { describe, expect, it } from "vitest";
import { derivePositions, type TransactionInput } from "@/lib/positions";

const tx = (date: string, side: "buy" | "sell", quantity: string, price: string, fees = "0"): TransactionInput => ({
  assetId: "PETR4",
  date,
  side,
  quantity,
  price,
  fees,
});

describe("preço médio pelo método da Receita", () => {
  it("compras ponderam o preço e somam as taxas ao custo", () => {
    // 100 × 30 + 10 de taxa = 3.010; 100 × 40 = 4.000 → 7.010 / 200 = 35,05.
    const [posicao] = derivePositions([tx("2026-01-10", "buy", "100", "30", "10"), tx("2026-02-10", "buy", "100", "40")]);
    expect(posicao.quantity).toBe("200");
    expect(posicao.avgPrice).toBe("35.05");
    expect(posicao.cost).toBe("7010");
  });

  it("venda não altera o preço médio, só a quantidade e o custo", () => {
    const [posicao] = derivePositions([
      tx("2026-01-10", "buy", "100", "30"),
      tx("2026-02-10", "buy", "100", "40"),
      tx("2026-03-10", "sell", "50", "60"),
    ]);
    expect(posicao.quantity).toBe("150");
    expect(posicao.avgPrice).toBe("35");
    expect(posicao.cost).toBe("5250");
  });

  it("posição zerada recomeça do zero na compra seguinte", () => {
    const [posicao] = derivePositions([
      tx("2026-01-10", "buy", "100", "30"),
      tx("2026-02-10", "sell", "100", "35"),
      tx("2026-03-10", "buy", "10", "50"),
    ]);
    expect(posicao.quantity).toBe("10");
    expect(posicao.avgPrice).toBe("50");
  });

  it("a ordem é a da data, não a de inserção", () => {
    const [posicao] = derivePositions([tx("2026-03-10", "sell", "50", "60"), tx("2026-01-10", "buy", "100", "30")]);
    expect(posicao.quantity).toBe("50");
    expect(posicao.warnings).toEqual([]);
  });

  it("quantidade fracionária de cripto sem erro de ponto flutuante", () => {
    const [posicao] = derivePositions([
      { assetId: "bitcoin", date: "2026-01-01", side: "buy", quantity: "0.1", price: "300000" },
      { assetId: "bitcoin", date: "2026-02-01", side: "buy", quantity: "0.2", price: "360000" },
    ]);
    expect(posicao.quantity).toBe("0.3");
    expect(posicao.avgPrice).toBe("340000");
  });

  it("venda maior que a posição zera, em vez de ficar negativa", () => {
    const posicoes = derivePositions([tx("2026-01-10", "buy", "10", "30"), tx("2026-02-10", "sell", "15", "35")]);
    expect(posicoes).toEqual([]);
  });

  it("venda sem posição anterior é avisada (histórico incompleto)", () => {
    const [posicao] = derivePositions([tx("2026-01-10", "sell", "10", "30"), tx("2026-02-10", "buy", "5", "20")]);
    expect(posicao.quantity).toBe("5");
    expect(posicao.warnings[0]).toMatch(/venda sem posição anterior/);
  });
});

describe("ajustes (posição informada)", () => {
  it("a quantidade do ajuste prevalece, e o preço médio vem do histórico", () => {
    // A B3 diz que hoje há 300 (houve bonificação que o histórico não tem).
    const [posicao] = derivePositions(
      [tx("2026-01-10", "buy", "100", "30"), tx("2026-02-10", "buy", "100", "40")],
      [{ assetId: "PETR4", quantity: "300" }],
    );
    expect(posicao.quantity).toBe("300");
    expect(posicao.avgPrice).toBe("35");
    expect(posicao.cost).toBe("10500");
  });

  it("ajuste com preço médio informado usa o informado", () => {
    const [posicao] = derivePositions([], [{ assetId: "VALE3", quantity: "50", avgPrice: "61.20" }]);
    expect(posicao).toMatchObject({ quantity: "50", avgPrice: "61.2", cost: "3060" });
  });

  it("ajuste sem preço e sem histórico: quantidade sim, preço médio não", () => {
    const [posicao] = derivePositions([], [{ assetId: "ITUB4", quantity: "10" }]);
    expect(posicao).toMatchObject({ quantity: "10", avgPrice: null, cost: null });
  });

  it("ajuste só por valor vira posição por valor", () => {
    const [posicao] = derivePositions([], [{ assetId: "tesouro-selic-2029", valueBrl: "15000.50" }]);
    expect(posicao).toMatchObject({ quantity: null, valueBrl: "15000.5" });
  });
});
