import type { IndicatorsData } from "@/lib/market";
import { INDICATOR_GROUPS, type IndicatorMeta } from "@/content/indicadores";
import { compactCurrency, currency, multiple, percent } from "@/lib/format";
import { SourceBadge } from "@/components/market/source-badge";
import { Value } from "@/components/market/value";
import { Tooltip } from "@/components/ui/tooltip";

type Props = {
  indicators: IndicatorsData;
  /** Chaves a mostrar. Sem isto, todos os grupos (ação). */
  only?: readonly string[];
};

// Indicadores agrupados por natureza (§2.1): valuation, rentabilidade, endividamento,
// crescimento. Cada célula tem a definição no tooltip e o motivo quando falta.
//
// A definição é **genérica** — descreve a fórmula, nunca o que o número significa para
// este ativo. "P/L é preço sobre lucro" informa; "P/L de 6 está barato" é análise, e
// análise exige credenciamento (§8.3).
export function IndicatorGrid({ indicators, only }: Props) {
  const groups = INDICATOR_GROUPS.map((group) => ({
    ...group,
    items: only ? group.items.filter((item) => only.includes(item.key)) : group.items,
  })).filter((group) => group.items.length > 0);

  return (
    <section aria-labelledby="indicadores">
      <h2 id="indicadores">Indicadores</h2>
      <div className="mt-6 space-y-8">
        {groups.map((group) => (
          <div key={group.title}>
            <h3 className="text-table font-medium uppercase tracking-wide text-ice-70">
              {group.title}
            </h3>
            <dl className="mt-3 grid grid-cols-2 gap-x-8 gap-y-4 sm:grid-cols-3 lg:grid-cols-4">
              {group.items.map((item) => (
                <Cell key={item.key} meta={item} indicators={indicators} />
              ))}
            </dl>
          </div>
        ))}
      </div>
      <SourceBadge source={indicators.source} className="mt-8" />
    </section>
  );
}

function Cell({ meta, indicators }: { meta: IndicatorMeta; indicators: IndicatorsData }) {
  const raw = (indicators as unknown as Record<string, string | null>)[meta.key] ?? null;
  return (
    <div>
      <dt className="text-table text-ice-70">
        <Tooltip content={meta.definition}>{meta.label}</Tooltip>
      </dt>
      <dd className="text-lg tabular-nums">
        <Value reason={indicators.missing_reasons[meta.key]}>{formatBy(meta.format, raw)}</Value>
      </dd>
    </div>
  );
}

function formatBy(format: IndicatorMeta["format"], value: string | null): string {
  switch (format) {
    case "percent":
      return percent(value);
    case "currency":
      return currency(value);
    case "compact":
      return compactCurrency(value);
    default:
      return multiple(value);
  }
}
