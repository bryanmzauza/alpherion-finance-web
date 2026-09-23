import type { assetClass, incomeKind } from "@/drizzle/schema";

// Rótulos e formatação da carteira (pt-BR). Só funções puras: importável no cliente.

export const CLASS_LABEL: Record<(typeof assetClass.enumValues)[number], string> = {
  stock_br: "Ação",
  fii: "FII",
  etf_br: "ETF",
  bdr: "BDR",
  treasury: "Tesouro",
  fixed_income: "Renda fixa",
  crypto: "Cripto",
  stablecoin: "Stablecoin",
  other: "Outro",
};

export const INCOME_LABEL: Record<(typeof incomeKind.enumValues)[number], string> = {
  dividend: "Dividendo",
  jcp: "JCP",
  fii_income: "Rendimento",
  interest: "Juros",
  other: "Outro",
};

const QUANTITY = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 8 });

/** Quantidade sem casas inúteis: 100 → "100"; 0,01500000 → "0,015". */
export function quantity(value: string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  return Number.isFinite(n) ? QUANTITY.format(n) : "—";
}

/** Tipo do resultado da busca global → classe da carteira. Índice não é ativo que se tem. */
export const HIT_CLASS = {
  stock: "stock_br",
  unit: "stock_br",
  fii: "fii",
  fiagro: "fii",
  etf: "etf_br",
  bdr: "bdr",
  treasury: "treasury",
  crypto: "crypto",
} as const;

export const HIT_REF = {
  stock: "ticker",
  unit: "ticker",
  fii: "ticker",
  fiagro: "ticker",
  etf: "ticker",
  bdr: "ticker",
  treasury: "treasury_slug",
  crypto: "coingecko_id",
} as const;
