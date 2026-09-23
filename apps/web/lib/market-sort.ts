// Ordenação das listas de papéis (site.md §2.1 "Rankings", plano 4.5, ADR-018).
//
// Não existe rota "ranking". Existe uma lista ordenada **pelo critério que o leitor
// escolheu**, e o título diz qual é: "Maior dividend yield 12 m", nunca "melhores
// pagadoras". Os campos espelham `repository.SORTABLE` da API — a API recusa qualquer
// outro com 422, e aqui um valor fora da lista volta para o padrão (liquidez).
//
// O título é montado a partir do rótulo do campo e da direção, sem adjetivo. O teste de
// lint de conteúdo (`content-lint.test.ts`) passa por este arquivo.

export type SortField =
  | "volume"
  | "change"
  | "ticker"
  | "company_name"
  | "market_cap"
  | "dy_12m"
  | "pe"
  | "pvp"
  | "roe";

export type SortDir = "asc" | "desc";

export type Sort = { field: SortField; dir: SortDir };

/** Padrão neutro: volume financeiro do dia (§2.1). */
export const DEFAULT_SORT: Sort = { field: "volume", dir: "desc" };

/** Rótulo de cada campo, como entra no título ("Maior volume financeiro do dia"). */
export const SORT_LABELS: Record<SortField, string> = {
  volume: "volume financeiro do dia",
  change: "variação do dia",
  ticker: "código",
  company_name: "nome",
  market_cap: "valor de mercado",
  dy_12m: "dividend yield 12 m",
  pe: "P/L",
  pvp: "P/VP",
  roe: "ROE",
};

const SORT_FIELDS = Object.keys(SORT_LABELS) as SortField[];

export function parseSort(
  params: { sort?: string | string[]; dir?: string | string[] },
  allowed: readonly SortField[] = SORT_FIELDS,
): Sort {
  const field = first(params.sort);
  const dir = first(params.dir);
  if (!field || !allowed.includes(field as SortField)) return DEFAULT_SORT;
  return { field: field as SortField, dir: dir === "asc" ? "asc" : "desc" };
}

export function isDefaultSort(sort: Sort): boolean {
  return sort.field === DEFAULT_SORT.field && sort.dir === DEFAULT_SORT.dir;
}

/** "Maior dividend yield 12 m", "Menor P/VP", "Código de A a Z". Só a métrica. */
export function sortTitle({ field, dir }: Sort): string {
  if (field === "ticker" || field === "company_name") {
    const label = SORT_LABELS[field];
    return `${label[0].toUpperCase()}${label.slice(1)} de ${dir === "asc" ? "A a Z" : "Z a A"}`;
  }
  return `${dir === "desc" ? "Maior" : "Menor"} ${SORT_LABELS[field]}`;
}

/** Frase para o subtítulo: "ordenados por dividend yield 12 m, do maior para o menor". */
export function sortPhrase({ field, dir }: Sort): string {
  if (field === "ticker" || field === "company_name") {
    return `ordenados por ${SORT_LABELS[field]}, de ${dir === "asc" ? "A a Z" : "Z a A"}`;
  }
  return `ordenados por ${SORT_LABELS[field]}, do ${dir === "desc" ? "maior para o menor" : "menor para o maior"}`;
}

export function sortQuery(sort: Sort, extra: Record<string, string> = {}): string {
  const params = new URLSearchParams(extra);
  if (!isDefaultSort(sort)) {
    params.set("sort", sort.field);
    params.set("dir", sort.dir);
  }
  const text = params.toString();
  return text ? `?${text}` : "";
}

/**
 * Presets de cada classe (plano 4.5). Um preset é só um atalho para uma ordenação —
 * título neutro, métrica visível na tabela. Ficam de fora de propósito:
 *
 * - "Menor P/L" nas ações: P/L negativo (prejuízo) viria primeiro e o "menor P/L" seria
 *   a empresa que mais perdeu dinheiro — um número certo com leitura errada.
 * - Qualquer combinação de indicadores ("P/L baixo e DY alto"): isso é tese de
 *   investimento, e tese é opinião (ADR-018).
 */
export const SORT_PRESETS: Record<string, Sort[]> = {
  acoes: [
    DEFAULT_SORT,
    { field: "market_cap", dir: "desc" },
    { field: "dy_12m", dir: "desc" },
    { field: "roe", dir: "desc" },
    { field: "change", dir: "desc" },
  ],
  fiis: [
    DEFAULT_SORT,
    { field: "dy_12m", dir: "desc" },
    { field: "pvp", dir: "asc" },
    { field: "change", dir: "desc" },
  ],
};

/** Campos que cada classe aceita por URL. ETF e BDR não têm indicador da CVM. */
export const SORTABLE_BY_CLASS: Record<string, SortField[]> = {
  acoes: ["volume", "change", "ticker", "market_cap", "dy_12m", "pe", "pvp", "roe"],
  fiis: ["volume", "change", "ticker", "dy_12m", "pvp"],
  etfs: ["volume", "change", "ticker"],
  bdrs: ["volume", "change", "ticker"],
};

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}
