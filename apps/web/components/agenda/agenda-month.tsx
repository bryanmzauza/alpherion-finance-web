import { AgendaFilters } from "@/components/agenda/agenda-filters";
import { QueryLink } from "@/components/agenda/query-link";
import { Gold } from "@/components/ui/gold";
import {
  AGENDA_DOCUMENT_CATEGORIES,
  EVENT_GROUPS,
  groupOf,
  isoWeek,
  monthGrid,
  monthPath,
  shiftMonth,
  todayIso,
  weekPath,
  type EventGroup,
  type Month,
} from "@/lib/agenda";
import { getEventCounts, optional } from "@/lib/market";
import { cn } from "@/lib/cn";

// Vista mensal da agenda (plano 4.3). Um mês do mercado inteiro passa do teto de itens
// de uma resposta, então o mês mostra **contagens** por dia e tipo, e cada dia leva à
// semana (`/agenda/2026-40#dia-2026-10-01`), onde estão os itens. Contar é fato; o que o
// mês não faz é escolher "os eventos importantes".

const MONTH = new Intl.DateTimeFormat("pt-BR", { month: "long", timeZone: "UTC" });
const WEEKDAYS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"];

const LABELS: Record<EventGroup, [string, string]> = {
  proventos: ["provento", "proventos"],
  comunicados: ["fato relevante", "fatos relevantes"],
  macro: ["macro", "macro"],
};

export async function AgendaMonth({ month }: { month: Month }) {
  const grid = monthGrid(month);
  const first = grid[0][0];
  const last = grid.at(-1)!.at(-1)!;
  const today = todayIso();
  const counts = await optional(
    getEventCounts({ from: first, to: last, category: AGENDA_DOCUMENT_CATEGORIES }),
  );

  const byDay = new Map<string, Map<EventGroup, number>>();
  for (const row of counts ?? []) {
    const day = byDay.get(row.date) ?? new Map<EventGroup, number>();
    const group = groupOf(row.kind);
    day.set(group, (day.get(group) ?? 0) + row.count);
    byDay.set(row.date, day);
  }

  const monthName = MONTH.format(new Date(Date.UTC(month.year, month.month - 1, 1)));
  const inMonth = (iso: string) => Number(iso.slice(5, 7)) === month.month;

  return (
    <>
      <p className="text-table uppercase tracking-wide text-ice-70">Agenda do mês</p>
      <h1 className="mt-2">
        Agenda de <Gold>{monthName}</Gold> de {month.year}
      </h1>
      <p className="mt-4 max-w-2xl text-ice-70">
        Quantos proventos, fatos relevantes e eventos macro caem em cada dia. Clique no dia para ver a lista na
        semana.
      </p>

      <nav aria-label="Outros meses" className="mt-6 flex flex-wrap gap-x-6 gap-y-2 text-table">
        <QueryLink href={monthPath(shiftMonth(month, -1))} className="text-gold underline underline-offset-4">
          ← Mês anterior
        </QueryLink>
        <QueryLink href={monthPath(shiftMonth(month, 1))} className="text-gold underline underline-offset-4">
          Próximo mês →
        </QueryLink>
        <QueryLink href="/agenda" className="text-ice-70 underline underline-offset-4 hover:text-ice">
          Semana atual
        </QueryLink>
      </nav>

      <div className="mt-8">
        <AgendaFilters classes={false} />
      </div>

      {counts === null ? (
        <p className="mt-10 text-ice-70">A agenda está temporariamente indisponível. Tente novamente em alguns minutos.</p>
      ) : (
        <div data-agenda className="mt-10">
          <div className="hidden grid-cols-7 gap-px text-center text-xs uppercase text-ice-70 md:grid" aria-hidden="true">
            {WEEKDAYS.map((day) => (
              <span key={day} className="pb-2">
                {day}
              </span>
            ))}
          </div>
          <ol className="grid grid-cols-1 gap-2 md:grid-cols-7 md:gap-px md:overflow-hidden md:rounded-lg md:border md:border-navy-3 md:bg-navy-3">
            {grid.flat().map((day) => {
              const groups = byDay.get(day);
              const total = groups ? [...groups.values()].reduce((a, b) => a + b, 0) : 0;
              return (
                <li
                  key={day}
                  className={cn(
                    "bg-navy-2 md:min-h-28",
                    !inMonth(day) && "hidden md:block md:opacity-50",
                    inMonth(day) && total === 0 && "hidden md:block",
                  )}
                >
                  <QueryLink href={`${weekPath(isoWeek(day))}#dia-${day}`}
                    className="block h-full rounded-lg border border-navy-3 p-3 hover:bg-navy-3 md:rounded-none md:border-0"
                  >
                    <time
                      dateTime={day}
                      className={cn("text-table tabular-nums", day === today ? "font-semibold text-gold" : "text-ice-70")}
                    >
                      {Number(day.slice(8))}
                      <span className="md:sr-only"> de {MONTH.format(new Date(`${day}T00:00:00Z`))}</span>
                    </time>
                    <ul className="mt-1 space-y-0.5 text-xs">
                      {EVENT_GROUPS.map(({ slug }) => {
                        const n = groups?.get(slug) ?? 0;
                        if (n === 0) return null;
                        const [one, many] = LABELS[slug];
                        return (
                          <li key={slug} data-grupo={slug} className="tabular-nums">
                            {n} {n === 1 ? one : many}
                          </li>
                        );
                      })}
                    </ul>
                  </QueryLink>
                </li>
              );
            })}
          </ol>
        </div>
      )}
    </>
  );
}
