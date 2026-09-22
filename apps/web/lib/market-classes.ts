import type { SecurityType } from "@/lib/market";

// As classes de ativo do v1.0, num lugar só (site.md §2.1).
//
// Cada rota de classe (`/acoes`, `/fiis`, `/etfs`, `/bdrs`) é a mesma página com outro
// filtro. Centralizar aqui evita o que sempre acontece quando se copia página: uma
// classe ganha um texto novo e as outras três ficam para trás.
//
// `title` e `description` são **descritivos**: dizem o que a lista é e por que está
// naquela ordem. Nada de "as melhores", "oportunidades" ou "para comprar" — a ordem
// padrão é liquidez e o título diz isso (§4.5, ADR-018).

export type MarketClass = {
  slug: string;
  type: SecurityType;
  /** Plural, como aparece no H1. */
  label: string;
  /** Singular, para o cabeçalho da página do ativo. */
  singular: string;
  title: string;
  description: string;
  intro: string;
};

export const MARKET_CLASSES: MarketClass[] = [
  {
    slug: "acoes",
    type: "stock",
    label: "Ações",
    singular: "Ação",
    title: "Ações da B3 — cotação, dividendos e indicadores",
    description:
      "Todas as ações listadas na B3, com cotação, proventos, indicadores e demonstrações da CVM. Cada número com fonte e data.",
    intro:
      "Empresas listadas na B3, ordenadas por volume financeiro do dia. Todo número tem a fonte ao lado.",
  },
  {
    slug: "fiis",
    type: "fii",
    label: "Fundos imobiliários",
    singular: "Fundo imobiliário",
    title: "FIIs — cotação, rendimentos e P/VP",
    description:
      "Fundos imobiliários listados na B3, com cotação, rendimentos, P/VP e informes da CVM. Cada número com fonte e data.",
    intro:
      "Fundos imobiliários listados na B3, ordenados por volume financeiro do dia. Todo número tem a fonte ao lado.",
  },
  {
    slug: "etfs",
    type: "etf",
    label: "ETFs",
    singular: "ETF",
    title: "ETFs da B3 — cotação e índice replicado",
    description:
      "ETFs listados na B3, com cotação, histórico e o índice que cada um replica. Cada número com fonte e data.",
    intro:
      "ETFs listados na B3, ordenados por volume financeiro do dia. Todo número tem a fonte ao lado.",
  },
  {
    slug: "bdrs",
    type: "bdr",
    label: "BDRs",
    singular: "BDR",
    title: "BDRs — cotação e razão de conversão",
    description:
      "BDRs listados na B3, com cotação, histórico e a razão de conversão de cada um. Cada número com fonte e data.",
    intro:
      "BDRs listados na B3, ordenados por volume financeiro do dia. Todo número tem a fonte ao lado.",
  },
];

export function classBySlug(slug: string): MarketClass | undefined {
  return MARKET_CLASSES.find((c) => c.slug === slug);
}

export function classByType(type: SecurityType): MarketClass | undefined {
  // `unit` mora em /acoes e `fiagro` em /fiis: são a mesma página, com o mesmo leitor.
  const alias: Partial<Record<SecurityType, SecurityType>> = { unit: "stock", fiagro: "fii" };
  const target = alias[type] ?? type;
  return MARKET_CLASSES.find((c) => c.type === target);
}
