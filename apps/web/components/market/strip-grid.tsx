import type { StripItem } from "@/lib/market";
import { stripValue } from "@/lib/format";
import { Change } from "@/components/market/change";
import { SourceBadge } from "@/components/market/source-badge";
import { Value } from "@/components/market/value";

// A faixa completa de `/mercado` (plano 4.2): Ibovespa, IFIX, IDIV, SMLL, PTAX, Selic,
// CDI 12 m, IPCA 12 m e BTC — cada item com o **seu** `SourceBadge`, porque vêm de três
// fontes, em horários diferentes (B3 no fechamento, BCB no dia útil, cripto a toda hora).
export function StripGrid({ items }: { items: StripItem[] }) {
  return (
    <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((item) => (
        <li key={item.key} className="rounded-lg border border-navy-3 bg-navy-2 p-4">
          <p className="text-table text-ice-70">{item.label}</p>
          <p className="mt-1 flex items-baseline gap-3">
            <span className="font-display text-2xl tabular-nums">
              <Value reason={item.missing_reasons.value}>{stripValue(item.value, item.unit)}</Value>
            </span>
            {item.change_percent !== null ? <Change value={item.change_percent} /> : null}
          </p>
          <SourceBadge source={item.source} className="mt-2 text-xs" />
        </li>
      ))}
    </ul>
  );
}
