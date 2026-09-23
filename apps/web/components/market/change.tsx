import { direction, signedPercent } from "@/lib/format";
import { Value } from "@/components/market/value";
import { cn } from "@/lib/cn";

const TREND = { up: "text-ok", down: "text-risk-text", flat: "text-ice-70" } as const;

// Variação com sinal e cor semântica (§5). O sinal vai no texto — a cor nunca carrega
// a informação sozinha. A API manda fração (0,0123 = +1,23%).
export function Change({
  value,
  reason,
  className,
}: {
  value: string | number | null;
  reason?: string;
  className?: string;
}) {
  return (
    <span className={cn("tabular-nums", TREND[direction(value)], className)}>
      <Value reason={reason}>{signedPercent(value)}</Value>
    </span>
  );
}
