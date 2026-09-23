import { apiFetch, ApiError } from "@/lib/api-client";

// Tipos e leitura dos dados de mercado. O `web` NUNCA lê o schema `market` no banco
// (site.md §3.2): tudo passa por aqui, e daqui para a API.
//
// Os tipos espelham `apps/api/alpherion/market/schemas.py`. Duas convenções vêm de lá e
// atravessam o front inteiro:
//
// 1. Todo bloco de número traz `source` — é o que o `SourceBadge` mostra. Nenhum número
//    de mercado aparece na tela sem a sua origem (§5).
// 2. Ausência vem com motivo em `missing_reasons`. A página mostra "—" e põe o motivo no
//    tooltip; nunca zero, nunca o campo sumido.

export type SourceRef = {
  source: string;
  attribution: string;
  document: string | null;
  updated_at: string | null;
};

/** Base de todo bloco vindo da API. */
export type Block = {
  source: SourceRef;
  missing_reasons: Record<string, string>;
};

/** Numérico da API: vem como string (Decimal) ou null. Nunca `number` — ver `toNumber`. */
export type Num = string | null;

export type SecuritySummary = {
  ticker: string;
  type: SecurityType;
  company_name: string;
  trade_name: string | null;
  sector_slug: string | null;
  price: Num;
  change_percent_day: Num;
  volume: Num;
  pe: Num;
  pvp: Num;
  dy_12m: Num;
  roe: Num;
  market_cap: Num;
  /** Motivo de cada `null` (a trava de licença preenche). */
  missing_reasons?: Record<string, string>;
};

export type SecurityType = "stock" | "unit" | "fii" | "fiagro" | "etf" | "bdr";

export type SecurityProfile = Block & {
  ticker: string;
  type: SecurityType;
  company_name: string;
  trade_name: string | null;
  cnpj: string | null;
  cvm_code: number | null;
  isin: string | null;
  sector: string | null;
  subsector: string | null;
  segment: string | null;
  sector_slug: string | null;
  listing_segment: string | null;
  etf_index_slug: string | null;
  bdr_ratio: string | null;
  /** Fração em circulação, do FRE (CVM). */
  free_float?: Num;
  free_float_date?: string | null;
  status: string;
};

export type PriceHeaderData = Block & {
  ticker: string;
  price: Num;
  change_day: Num;
  change_percent_day: Num;
  low_52w: Num;
  high_52w: Num;
  volume: Num;
  quote_date: string | null;
};

export type IndicatorsData = Block & {
  date: string | null;
} & Record<IndicatorKey, Num>;

export type IndicatorKey =
  | "pe"
  | "pb"
  | "pvp"
  | "ev_ebitda"
  | "ev_ebit"
  | "psr"
  | "dy_12m"
  | "payout"
  | "market_cap"
  | "roe"
  | "roic"
  | "roa"
  | "gross_margin"
  | "ebitda_margin"
  | "net_margin"
  | "net_debt_ebitda"
  | "net_debt_equity"
  | "current_ratio"
  | "revenue_cagr_5y"
  | "earnings_cagr_5y"
  | "eps"
  | "bvps";

export type SecurityDetail = {
  profile: SecurityProfile;
  price: PriceHeaderData;
  indicators: IndicatorsData;
};

export type Quote = {
  date: string;
  open: Num;
  high: Num;
  low: Num;
  close: Num;
  close_adjusted: Num;
  volume: Num;
};

export type CorporateEvent = {
  kind: string;
  ex_date: string | null;
  record_date: string | null;
  payment_date: string | null;
  value_per_share: Num;
  ratio: string | null;
  source: string;
};

export type MarketDocument = {
  protocol: string;
  category: string;
  type: string | null;
  subject: string | null;
  delivered_at: string;
  reference_date: string | null;
  url: string;
};

export type StatementLine = { account_code: string; account_name: string; value: Num };

export type Financials = Block & {
  period_end: string;
  period_type: string;
  consolidated: boolean;
  statements: Record<string, StatementLine[]>;
};

export type EventKind = "ex_date" | "payment" | "document" | "macro" | "corporate";

export type MarketEvent = {
  id: string;
  kind: EventKind;
  date: string;
  ticker: string | null;
  /** Classe do papel; `null` em evento macro. */
  security_type: SecurityType | null;
  title: string;
  payload: Record<string, unknown> | null;
  source: string;
};

export type EventCount = { date: string; kind: EventKind; count: number };

export type StripItem = Block & {
  key: string;
  label: string;
  value: Num;
  change_percent: Num;
  unit: string | null;
};

export type Mover = {
  ticker: string;
  type: SecurityType | null;
  company_name: string;
  price: Num;
  change_percent: Num;
  volume: Num;
  missing_reasons?: Record<string, string>;
};

export type MoversList = Block & {
  metric: "change" | "volume";
  direction: "asc" | "desc";
  min_volume: Num;
  items: Mover[];
};

export type SectorNode = {
  slug: string;
  name: string;
  kind: string;
  sector: string | null;
  subsector: string | null;
  securities_count: number;
};

export type SectorDetail = Block &
  SectorNode & {
    /** Soma do valor de mercado dos papéis do setor no último pregão. */
    market_cap: Num;
    market_cap_count: number;
  };

export type IndexSummary = { slug: string; b3_code: string; name: string };

export type IndexDetail = Block &
  IndexSummary & {
    description: string | null;
    rebalance_note: string | null;
    value: Num;
    change_percent: Num;
    date: string | null;
  };

export type IndexMember = {
  ticker: string;
  company_name: string | null;
  weight: Num;
  theoretical_qty: Num;
};

export type IndexComposition = Block & {
  slug: string;
  reference_date: string;
  members: IndexMember[];
};

export type TreasuryBond = Block & {
  slug: string;
  name: string;
  index_type: string;
  maturity: string;
  coupon: boolean;
  date: string | null;
  buy_rate: Num;
  sell_rate: Num;
  buy_price: Num;
  sell_price: Num;
};

export type CryptoItem = Block & {
  id: string;
  symbol: string;
  name: string;
  rank: number | null;
  price: Num;
  change_24h: Num;
  market_cap: Num;
  volume_24h: Num;
};

export type AssetHitType = SecurityType | "index" | "treasury" | "crypto";

export type AssetHit = {
  type: AssetHitType;
  code: string;
  name: string;
  price: Num;
  change_percent: Num;
  missing_reasons?: Record<string, string>;
};

export type AssetSearchGroup = {
  asset_class: "stock" | "fii" | "etf" | "bdr" | "index" | "treasury" | "crypto";
  items: AssetHit[];
};

export type AssetSearchResult = { query: string; groups: AssetSearchGroup[] };

export type Page<T> = { items: T[]; total: number; page: number; page_size: number };

export type MarketOverview = {
  strip: StripItem[];
  counters: Record<string, number>;
  gainers: MoversList;
  losers: MoversList;
  most_traded: MoversList;
  events: MarketEvent[];
};

// --- revalidação ------------------------------------------------------------
// Páginas de mercado são ISR: a carga do pipeline dispara `revalidate_pages`. O tempo
// abaixo é o teto caso a chamada falhe — nunca a fonte primária de atualização.

/** 1 hora: o pipeline revalida antes disso; isto é só a rede de segurança. */
export const REVALIDATE_SECONDS = 3600;

// --- leituras ---------------------------------------------------------------

export function listSecurities(params: {
  type?: SecurityType;
  sector?: string;
  sort?: string;
  dir?: "asc" | "desc";
  page?: number;
  page_size?: number;
  min_volume?: number;
}): Promise<Page<SecuritySummary>> {
  return apiFetch(`/v1/securities?${query(params)}`, { revalidate: REVALIDATE_SECONDS });
}

export function getSecurity(ticker: string): Promise<SecurityDetail> {
  return apiFetch(`/v1/securities/${encodeURIComponent(ticker)}`, {
    revalidate: REVALIDATE_SECONDS,
  });
}

export function getHistory(ticker: string, range = "1a"): Promise<Quote[]> {
  return apiFetch(`/v1/securities/${encodeURIComponent(ticker)}/history?range=${range}`, {
    revalidate: REVALIDATE_SECONDS,
  });
}

export function getDividends(ticker: string): Promise<CorporateEvent[]> {
  return apiFetch(`/v1/securities/${encodeURIComponent(ticker)}/dividends`, {
    revalidate: REVALIDATE_SECONDS,
  });
}

export function getDocuments(ticker: string): Promise<Page<MarketDocument>> {
  return apiFetch(`/v1/securities/${encodeURIComponent(ticker)}/documents`, {
    revalidate: REVALIDATE_SECONDS,
  });
}

export function getFinancials(ticker: string): Promise<Financials> {
  return apiFetch(`/v1/securities/${encodeURIComponent(ticker)}/financials?period=annual`, {
    revalidate: REVALIDATE_SECONDS,
  });
}

export function getStrip(): Promise<StripItem[]> {
  return apiFetch("/v1/market/strip", { revalidate: 300 });
}

export function getOverview(): Promise<MarketOverview> {
  return apiFetch("/v1/market/overview", { revalidate: 300 });
}

/** A agenda muda com a carga do dia; meia hora é a rede de segurança da revalidação. */
const EVENTS_REVALIDATE = 1800;

/** Teto de itens da agenda numa resposta (`repository.MAX_EVENTS` na API). */
export const MAX_EVENTS = 500;

export type EventQuery = {
  from?: string;
  to?: string;
  kind?: EventKind[];
  type?: SecurityType;
  ticker?: string;
  /** Categorias CVM de comunicado ("Fato Relevante"). Não filtra provento nem macro. */
  category?: string[];
  limit?: number;
};

export function getEvents(params: EventQuery = {}): Promise<MarketEvent[]> {
  return apiFetch(`/v1/market/events?${query(params)}`, { revalidate: EVENTS_REVALIDATE });
}

export function getEventCounts(params: Omit<EventQuery, "ticker" | "limit">): Promise<EventCount[]> {
  return apiFetch(`/v1/market/events/calendar?${query(params)}`, {
    revalidate: EVENTS_REVALIDATE,
  });
}

export function getSectors(): Promise<SectorNode[]> {
  return apiFetch("/v1/sectors", { revalidate: REVALIDATE_SECONDS });
}

export function getSector(slug: string): Promise<SectorDetail> {
  return apiFetch(`/v1/sectors/${encodeURIComponent(slug)}`, { revalidate: REVALIDATE_SECONDS });
}

/** Busca global. Do servidor (a `/busca` e o route handler), nunca do navegador. */
export function searchAssets(q: string, limit = 6): Promise<AssetSearchResult> {
  return apiFetch(`/v1/assets/search?${query({ q, limit })}`, { revalidate: 300 });
}

export function getIndices(): Promise<IndexSummary[]> {
  return apiFetch("/v1/indices", { revalidate: REVALIDATE_SECONDS });
}

export function getIndex(slug: string): Promise<IndexDetail> {
  return apiFetch(`/v1/indices/${encodeURIComponent(slug)}`, { revalidate: REVALIDATE_SECONDS });
}

export function getIndexComposition(slug: string): Promise<IndexComposition> {
  return apiFetch(`/v1/indices/${encodeURIComponent(slug)}/composition`, {
    revalidate: REVALIDATE_SECONDS,
  });
}

export function getTreasury(): Promise<TreasuryBond[]> {
  return apiFetch("/v1/treasury", { revalidate: REVALIDATE_SECONDS });
}

export function getCrypto(): Promise<CryptoItem[]> {
  return apiFetch("/v1/crypto", { revalidate: 300 });
}

/**
 * Busca que **não derruba a página**: um bloco que falha vira "—" com o motivo, e o
 * resto continua. Uma página de ativo não pode sumir porque a CVM não respondeu.
 */
export async function optional<T>(promise: Promise<T>): Promise<T | null> {
  try {
    return await promise;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    console.error("[market] bloco indisponível:", error);
    return null;
  }
}

/** Query string; lista vira parâmetro repetido (`kind=ex_date&kind=payment`). */
export function query(params: Record<string, string | number | string[] | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (Array.isArray(value)) {
      for (const item of value) search.append(key, item);
    } else if (value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }
  return search.toString();
}
