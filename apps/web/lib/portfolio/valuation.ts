import { ApiError, apiFetch } from "@/lib/api-client";
import type { HeldPosition } from "@/lib/portfolio/repo";

// Valorização da carteira pela API (`POST /v1/portfolios/valuation`, site.md §2.3): o
// `web` manda quantidade e preço médio já derivados; preço, valor, resultado e peso
// vêm calculados de lá — "uma API só" (o bot vai usar a mesma conta).

export const MAX_VALUED = 100;

export type ValuedPosition = {
  symbol: string;
  market_ref: HeldPosition["marketRef"];
  asset_class: HeldPosition["assetClass"];
  quantity: string | null;
  avg_price: string | null;
  cost: string | null;
  price: string | null;
  price_date: string | null;
  value: string | null;
  result: string | null;
  result_percent: string | null;
  weight: string | null;
  source: string | null;
  missing_reasons: Record<string, string>;
};

export type Valuation = {
  positions: ValuedPosition[];
  total_value: string;
  total_cost: string | null;
  total_result: string | null;
  partial: boolean;
  as_of: string | null;
};

export type ValuationOutcome = { valuation: Valuation | null; error: string | null; truncated: boolean };

export async function valuePositions(positions: HeldPosition[]): Promise<ValuationOutcome> {
  const eligible = positions.filter((p) => p.quantity !== null || p.valueBrl !== null);
  if (eligible.length === 0) return { valuation: null, error: null, truncated: false };
  const body = {
    positions: eligible.slice(0, MAX_VALUED).map((p) => ({
      symbol: p.symbol,
      market_ref: p.marketRef,
      asset_class: p.assetClass,
      quantity: p.quantity,
      avg_price: p.quantity !== null ? p.avgPrice : null,
      value_brl: p.quantity === null ? p.valueBrl : null,
    })),
  };
  try {
    const valuation = await apiFetch<Valuation>("/v1/portfolios/valuation", { method: "POST", body, cache: "no-store" });
    return { valuation, error: null, truncated: eligible.length > MAX_VALUED };
  } catch (error) {
    console.error("[carteira] valorização indisponível:", error instanceof ApiError ? error.status : (error as Error).name);
    return { valuation: null, error: "cotações indisponíveis agora; tente de novo em alguns minutos", truncated: false };
  }
}
