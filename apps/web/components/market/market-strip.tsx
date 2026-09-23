import Link from "next/link";
import type { StripItem } from "@/lib/market";
import { getStrip, optional } from "@/lib/market";
import { DASH, direction, signedPercent, stripValue } from "@/lib/format";
import { cn } from "@/lib/cn";

// Faixa do header (site.md §2.1): Ibovespa · IFIX · dólar (PTAX) · CDI 12 m · BTC.
//
// Server component e **zero JS no cliente**: está em toda página pública, inclusive na
// landing, e o orçamento de JS de lá não comporta nada que não seja o próprio Next.
// Por isso o motivo de um "—" vai em `title` + texto para leitor de tela, e não no
// `Tooltip` (que é client component).
//
// `revalidate: 300` no fetch (`getStrip`): a página continua estática e a faixa se
// renova a cada 5 min. Se a API não responder, os rótulos ficam com "—" e a página sai
// do mesmo jeito — faixa com buraco, nunca página quebrada.

const FALLBACK: { key: string; label: string }[] = [
  { key: "ibovespa", label: "Ibovespa" },
  { key: "ifix", label: "IFIX" },
  { key: "ptax_venda", label: "Dólar (PTAX)" },
  { key: "cdi_12m", label: "CDI 12 m" },
  { key: "bitcoin", label: "Bitcoin" },
];

const UNAVAILABLE = "faixa indisponível no momento";

const TREND = { up: "text-ok", down: "text-risk-text", flat: "text-ice-70" } as const;

export async function MarketStrip() {
  const items = await optional(getStrip());

  return (
    <div className="border-b border-navy-3 bg-navy-2">
      <div className="mx-auto flex h-9 w-full max-w-site items-center gap-6 px-4 text-xs md:px-6">
        <ul
          aria-label="Faixa de mercado"
          className="flex min-w-0 flex-1 items-center gap-5 overflow-x-auto whitespace-nowrap [scrollbar-width:none]"
        >
          {items
            ? items.map((item) => <StripEntry key={item.key} item={item} />)
            : FALLBACK.map((item) => (
                <li key={item.key} className="flex items-baseline gap-1.5">
                  <span className="text-ice-70">{item.label}</span>
                  <Missing reason={UNAVAILABLE} />
                </li>
              ))}
        </ul>
        <Link
          href="/mercado"
          className="hidden shrink-0 text-ice-70 underline-offset-4 hover:text-ice hover:underline sm:inline"
        >
          Ver mercado
        </Link>
      </div>
    </div>
  );
}

function StripEntry({ item }: { item: StripItem }) {
  const trend = direction(item.change_percent);
  // A fonte de cada número, em `title` (§5: nenhum número sem fonte). A faixa completa
  // de /mercado mostra o `SourceBadge` visível.
  const source = [item.source.attribution, item.source.document].filter(Boolean).join(" · ");
  return (
    <li className="flex items-baseline gap-1.5" title={source}>
      <span className="text-ice-70">{item.label}</span>
      {item.value === null ? (
        <Missing reason={item.missing_reasons.value} />
      ) : (
        <span className="tabular-nums">{stripValue(item.value, item.unit)}</span>
      )}
      {item.change_percent !== null ? (
        <span className={cn("tabular-nums", TREND[trend])}>
          {signedPercent(item.change_percent)}
        </span>
      ) : null}
      <span className="sr-only">({source})</span>
    </li>
  );
}

function Missing({ reason }: { reason?: string }) {
  return (
    <span className="text-ice-70" title={reason}>
      {DASH}
      {reason ? <span className="sr-only"> ({reason})</span> : null}
    </span>
  );
}
