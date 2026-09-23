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

// Os sete caminhos de dado de mercado, na ordem em que aparecem na landing (§5, seção 5)
// e no menu do portal (Etapa 4.1). Um lugar só: a landing e o header não podem divergir.
// `menu` é o rótulo curto do header, quando difere do da landing.
export const MARKET_LINKS: { href: string; label: string; hint: string; menu?: string }[] = [
  { href: "/acoes", label: "Ações", hint: "cotação, proventos, indicadores" },
  { href: "/fiis", label: "FIIs", hint: "rendimentos e P/VP" },
  { href: "/etfs", label: "ETFs", hint: "índice replicado" },
  { href: "/bdrs", label: "BDRs", hint: "razão de conversão" },
  { href: "/indices", label: "Índices", hint: "carteira teórica datada" },
  { href: "/tesouro", label: "Tesouro Direto", hint: "taxa e preço do dia", menu: "Tesouro" },
  { href: "/cripto", label: "Cripto", hint: "cotação em reais" },
];

// Menu do site público (site.md §2.1): Ações · FIIs · ETFs · BDRs · Índices · Tesouro ·
// Cripto · Setores · Agenda · Raio-X · Vídeos. "Mercado" abre a lista porque é a porta
// do portal — a faixa do header também leva para lá. Sobre e Contato ficam no rodapé.
export const PORTAL_NAV: { href: string; label: string }[] = [
  { href: "/mercado", label: "Mercado" },
  ...MARKET_LINKS.map((link) => ({ href: link.href, label: link.menu ?? link.label })),
  { href: "/setores", label: "Setores" },
  { href: "/agenda", label: "Agenda" },
  { href: "/raio-x", label: "Raio-X" },
  { href: "/videos", label: "Vídeos" },
];
