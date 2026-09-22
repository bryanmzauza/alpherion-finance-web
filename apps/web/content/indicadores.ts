// Definição de cada indicador (site.md §1: "todo termo é definido na primeira vez").
//
// As definições são **genéricas e sem juízo de valor**: descrevem o que a fórmula mede,
// nunca o que o número significa para o ativo da página. "P/L alto pode indicar
// expectativa de crescimento" é glossário; "PETR4 está barata" é análise, e análise
// exige credenciamento (Res. CVM 20, §8.3).
//
// O glossário completo é `/indicadores`, no v1.x; estas são as definições curtas do
// tooltip. Fórmulas em `apps/api/alpherion/data/transform/indicators.py`.

export type IndicatorMeta = {
  key: string;
  label: string;
  definition: string;
  /** Como formatar: múltiplo, porcentagem ou dinheiro. */
  format: "multiple" | "percent" | "currency" | "compact";
};

export type IndicatorGroup = {
  title: string;
  items: IndicatorMeta[];
};

export const INDICATOR_GROUPS: IndicatorGroup[] = [
  {
    title: "Valuation",
    items: [
      {
        key: "pe",
        label: "P/L",
        definition: "Preço da ação dividido pelo lucro por ação dos últimos 12 meses.",
        format: "multiple",
      },
      {
        key: "pb",
        label: "P/VP",
        definition: "Preço da ação dividido pelo valor patrimonial por ação.",
        format: "multiple",
      },
      {
        key: "ev_ebitda",
        label: "EV/EBITDA",
        definition:
          "Valor da empresa (valor de mercado mais dívida líquida) dividido pelo EBITDA.",
        format: "multiple",
      },
      {
        key: "ev_ebit",
        label: "EV/EBIT",
        definition: "Valor da empresa dividido pelo resultado antes de juros e impostos.",
        format: "multiple",
      },
      {
        key: "psr",
        label: "PSR",
        definition: "Valor de mercado dividido pela receita líquida dos últimos 12 meses.",
        format: "multiple",
      },
      {
        key: "dy_12m",
        label: "Dividend yield 12 m",
        definition:
          "Proventos por ação pagos nos últimos 12 meses divididos pela cotação atual.",
        format: "percent",
      },
      {
        key: "payout",
        label: "Payout",
        definition: "Parcela do lucro por ação distribuída como provento nos últimos 12 meses.",
        format: "percent",
      },
      {
        key: "market_cap",
        label: "Valor de mercado",
        definition: "Cotação multiplicada pela quantidade total de ações.",
        format: "compact",
      },
    ],
  },
  {
    title: "Rentabilidade",
    items: [
      {
        key: "roe",
        label: "ROE",
        definition: "Lucro líquido dividido pelo patrimônio líquido.",
        format: "percent",
      },
      {
        key: "roic",
        label: "ROIC",
        definition:
          "Resultado operacional após impostos dividido pelo capital investido (patrimônio líquido mais dívida líquida). Usa alíquota de 34%.",
        format: "percent",
      },
      {
        key: "roa",
        label: "ROA",
        definition: "Lucro líquido dividido pelo ativo total.",
        format: "percent",
      },
      {
        key: "gross_margin",
        label: "Margem bruta",
        definition: "Resultado bruto dividido pela receita líquida.",
        format: "percent",
      },
      {
        key: "ebitda_margin",
        label: "Margem EBITDA",
        definition: "EBITDA dividido pela receita líquida.",
        format: "percent",
      },
      {
        key: "net_margin",
        label: "Margem líquida",
        definition: "Lucro líquido dividido pela receita líquida.",
        format: "percent",
      },
    ],
  },
  {
    title: "Endividamento",
    items: [
      {
        key: "net_debt_ebitda",
        label: "Dív. líq./EBITDA",
        definition:
          "Dívida líquida (empréstimos menos caixa e aplicações) dividida pelo EBITDA.",
        format: "multiple",
      },
      {
        key: "net_debt_equity",
        label: "Dív. líq./PL",
        definition: "Dívida líquida dividida pelo patrimônio líquido.",
        format: "multiple",
      },
      {
        key: "current_ratio",
        label: "Liquidez corrente",
        definition: "Ativo circulante dividido pelo passivo circulante.",
        format: "multiple",
      },
    ],
  },
  {
    title: "Crescimento e por ação",
    items: [
      {
        key: "revenue_cagr_5y",
        label: "CAGR receita 5 a",
        definition: "Crescimento anual composto da receita líquida em cinco anos.",
        format: "percent",
      },
      {
        key: "earnings_cagr_5y",
        label: "CAGR lucro 5 a",
        definition: "Crescimento anual composto do lucro líquido em cinco anos.",
        format: "percent",
      },
      {
        key: "eps",
        label: "LPA",
        definition: "Lucro líquido dividido pela quantidade de ações.",
        format: "currency",
      },
      {
        key: "bvps",
        label: "VPA",
        definition: "Patrimônio líquido dividido pela quantidade de ações.",
        format: "currency",
      },
    ],
  },
];

/** Grupos que fazem sentido para um FII (não têm DRE de companhia). */
export const FII_INDICATOR_KEYS = ["pvp", "dy_12m", "market_cap"] as const;
