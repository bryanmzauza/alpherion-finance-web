import { describe, expect, it } from "vitest";
import {
  DASH,
  compactCurrency,
  currency,
  stripValue,
  date,
  direction,
  multiple,
  percent,
  signedPercent,
  toNumber,
} from "./format";

// O Intl põe espaço **inseparável** entre "R$" e o número — é o certo: evita que a
// quebra de linha separe o símbolo do valor. Os testes comparam com espaço normal.
const plain = (value: string) => value.replace(/\u00a0/g, " ");

// A regra que estes testes prendem é a do site.md §3.5: **valor ausente vira "—", nunca
// zero**. Zero é um número e o leitor o lê como um — "a empresa distribuiu R$ 0,00"
// quando a verdade é que o dado não existe.

describe("ausência nunca vira zero", () => {
  it.each([null, undefined, ""])("%s vira traço em todo formatador", (value) => {
    expect(currency(value)).toBe(DASH);
    expect(percent(value)).toBe(DASH);
    expect(multiple(value)).toBe(DASH);
    expect(compactCurrency(value)).toBe(DASH);
    expect(signedPercent(value)).toBe(DASH);
    expect(date(value)).toBe(DASH);
  });

  it("string não numérica também vira traço, não NaN", () => {
    expect(currency("indisponível")).toBe(DASH);
    expect(toNumber("abc")).toBeNull();
  });

  it("zero de verdade é formatado como zero", () => {
    expect(currency("0")).toContain("0,00");
    expect(percent("0")).toContain("0,00%");
  });
});

describe("Decimal vem como string e não perde centavo", () => {
  it("formata o valor exato que a API mandou", () => {
    expect(plain(currency("38.50"))).toBe("R$ 38,50");
    expect(plain(currency("1234.56"))).toBe("R$ 1.234,56");
  });

  it("múltiplo com duas casas", () => {
    expect(multiple("6.2")).toBe("6,20");
  });
});

describe("percentual", () => {
  it("a API manda fração; a tela mostra porcentagem", () => {
    expect(plain(percent("0.0812"))).toBe("8,12%");
    expect(plain(percent("0.21"))).toBe("21,00%");
  });

  it("variação do dia leva sinal explícito", () => {
    expect(plain(signedPercent("0.043"))).toBe("+4,30%");
    expect(plain(signedPercent("-0.043"))).toBe("-4,30%");
  });
});

describe("valores grandes", () => {
  it("usa a escala que o leitor entende", () => {
    expect(plain(compactCurrency("500000000000"))).toBe("R$ 500,00 bi");
    expect(plain(compactCurrency("1200000000"))).toBe("R$ 1,20 bi");
    expect(plain(compactCurrency("1500000"))).toBe("R$ 1,50 mi");
    expect(plain(compactCurrency("999"))).toBe("R$ 999,00");
  });

  it("mantém o sinal de valores negativos (dívida líquida negativa é caixa)", () => {
    expect(plain(compactCurrency("-2000000"))).toBe("R$ -2,00 mi");
  });
});

describe("datas", () => {
  it("formata a data da API sem deslocar por fuso", () => {
    expect(date("2026-09-18")).toBe("18/09/2026");
  });

  it("data inválida vira traço, não 'Invalid Date'", () => {
    expect(date("qualquer coisa")).toBe(DASH);
  });
});

describe("direção da variação", () => {
  it("ausência é neutra — não é queda", () => {
    expect(direction(null)).toBe("flat");
    expect(direction("0")).toBe("flat");
  });

  it("sinal decide a cor", () => {
    expect(direction("0.01")).toBe("up");
    expect(direction("-0.01")).toBe("down");
  });
});

describe("stripValue", () => {
  it("formata pela unidade que a API declara", () => {
    expect(stripValue("142512.37", "pts")).toBe("142.512");
    expect(stripValue("5.4321", "R$")).toBe("R$ 5,4321");
    expect(stripValue("10.9", "%")).toBe("10,90%");
    expect(stripValue("350123.4", "BRL")).toMatch(/^R\$\s350\.123,00$/);
  });

  it("ausente é traço, nunca zero", () => {
    expect(stripValue(null, "pts")).toBe("—");
  });
});
