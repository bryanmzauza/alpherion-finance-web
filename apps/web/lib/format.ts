// Formatação dos números de mercado (site.md §5).
//
// A regra que vale acima de todas: **valor ausente mostra "—", nunca zero**. Zero é um
// número e o leitor o lê como um ("a empresa distribuiu R$ 0,00") — quando a verdade é
// que o dado não existe. Por isso todo formatador aqui devolve `DASH` em vez de `0` e
// todo componente que mostra número recebe o motivo junto.
//
// A API manda `Decimal` como **string** para não perder centavo no JSON. A conversão
// para `number` acontece só na hora de formatar, onde o arredondamento já é o desejado.

export const DASH = "—";

const BRL = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const NUMBER = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const PERCENT = new Intl.NumberFormat("pt-BR", {
  style: "percent",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const DATE = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeZone: "UTC" });
const DATE_LONG = new Intl.DateTimeFormat("pt-BR", { dateStyle: "long", timeZone: "UTC" });

export function toNumber(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function currency(value: string | number | null | undefined): string {
  const n = toNumber(value);
  return n === null ? DASH : BRL.format(n);
}

export function decimal(value: string | number | null | undefined, digits = 2): string {
  const n = toNumber(value);
  if (n === null) return DASH;
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(n);
}

/** Fração → porcentagem: 0,0812 vira "8,12%". A API sempre manda fração. */
export function percent(value: string | number | null | undefined): string {
  const n = toNumber(value);
  return n === null ? DASH : PERCENT.format(n);
}

/** Percentual com sinal explícito — usado em variação do dia. */
export function signedPercent(value: string | number | null | undefined): string {
  const n = toNumber(value);
  if (n === null) return DASH;
  return `${n > 0 ? "+" : ""}${PERCENT.format(n)}`;
}

/** Valores grandes em escala legível: R$ 1,2 bi. Mantém o sinal. */
export function compactCurrency(value: string | number | null | undefined): string {
  const n = toNumber(value);
  if (n === null) return DASH;
  const abs = Math.abs(n);
  const [divisor, suffix] =
    abs >= 1e12 ? [1e12, " tri"] : abs >= 1e9 ? [1e9, " bi"] : abs >= 1e6 ? [1e6, " mi"] : [1, ""];
  return `R$ ${NUMBER.format(n / divisor)}${suffix}`;
}

/** Múltiplo (P/L, P/VP, EV/EBITDA): número puro com duas casas. */
export function multiple(value: string | number | null | undefined): string {
  const n = toNumber(value);
  return n === null ? DASH : NUMBER.format(n);
}

export function date(value: string | null | undefined): string {
  if (!value) return DASH;
  const parsed = new Date(value.length <= 10 ? `${value}T00:00:00Z` : value);
  return Number.isNaN(parsed.getTime()) ? DASH : DATE.format(parsed);
}

export function dateLong(value: string | null | undefined): string {
  if (!value) return DASH;
  const parsed = new Date(value.length <= 10 ? `${value}T00:00:00Z` : value);
  return Number.isNaN(parsed.getTime()) ? DASH : DATE_LONG.format(parsed);
}

/** Direção de uma variação, para a cor. `null` é neutro — ausência não é queda. */
export function direction(value: string | number | null | undefined): "up" | "down" | "flat" {
  const n = toNumber(value);
  if (n === null || n === 0) return "flat";
  return n > 0 ? "up" : "down";
}

/**
 * Valor de um item da faixa, pela unidade que a API declara (`StripItem.unit`):
 * índice em pontos inteiros, câmbio com quatro casas (é como a PTAX é publicada),
 * taxa em pontos percentuais ("10,90%" — a API manda 10.9, não 0.109) e cripto em reais.
 */
export function stripValue(value: string | number | null | undefined, unit: string | null): string {
  const n = toNumber(value);
  if (n === null) return DASH;
  switch (unit) {
    case "pts":
      return decimal(n, 0);
    case "R$":
      return `R$ ${decimal(n, 4)}`;
    case "%":
      return `${decimal(n, 2)}%`;
    case "BRL":
      return BRL.format(Math.round(n));
    default:
      return decimal(n, 2);
  }
}

/** Valor por ação de provento: até 8 casas, porque é assim que o emissor anuncia. */
export function perShare(value: string | number | null | undefined): string {
  const n = toNumber(value);
  if (n === null) return DASH;
  return `R$ ${new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 8 }).format(n)}`;
}
