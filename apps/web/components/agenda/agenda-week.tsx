import { EventList } from "@/components/market/event-list";
import { SourcesNote } from "@/components/market/sources-note";
import { AgendaFilters } from "@/components/agenda/agenda-filters";
import { QueryLink } from "@/components/agenda/query-link";
import { JsonLd } from "@/components/site/json-ld";
import { Gold } from "@/components/ui/gold";
import {
  AGENDA_DOCUMENT_CATEGORIES,
  isoWeek,
  monthOf,
  monthPath,
  shiftWeek,
  todayIso,
  weekDays,
  weekPath,
  type Week,
} from "@/lib/agenda";
import { eventView } from "@/lib/event-view";
import { MAX_EVENTS, getEvents, optional, type MarketEvent } from "@/lib/market";
import { agendaEventsJsonLd, siteUrl } from "@/lib/seo";
import { cn } from "@/lib/cn";

// A semana da agenda (`/agenda` e `/agenda/[ano]-[semana]`): sete dias, cada um com
// âncora (`#dia-2026-09-23`), proventos, fatos relevantes e macro. Só fato com data e
// fonte (site.md §2.1) — quem monta é o `transform/events.py` da API.

const DAY = new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" });
const RANGE_DAY = new Intl.DateTimeFormat("pt-BR", { day: "numeric", month: "long", timeZone: "UTC" });
const YEAR = new Intl.DateTimeFormat("pt-BR", { year: "numeric", timeZone: "UTC" });

const utc = (iso: string) => new Date(`${iso}T00:00:00Z`);

export async function AgendaWeek({ week }: { week: Week }) {
  const days = weekDays(week);
  const today = todayIso();
  const events = await optional(
    getEvents({
      from: days[0],
      to: days[6],
      category: AGENDA_DOCUMENT_CATEGORIES,
      limit: MAX_EVENTS,
    }),
  );
  const byDay = new Map<string, MarketEvent[]>(days.map((day) => [day, []]));
  for (const event of events ?? []) byDay.get(event.date)?.push(event);

  const isCurrent = days.includes(today);
  const previous = shiftWeek(week, -1);
  const next = shiftWeek(week, 1);

  return (
    <>
      {events && events.length > 0 ? (
        <JsonLd
          data={agendaEventsJsonLd(
            events.map((event) => {
              const view = eventView(event);
              return {
                name: event.title,
                date: event.date,
                description: view.detail,
                url: view.external && view.href ? view.href : siteUrl(view.href ?? `${weekPath(week)}#dia-${event.date}`),
              };
            }),
          )}
        />
      ) : null}

      <p className="text-table uppercase tracking-wide text-ice-70">
        Semana {week.week} de {week.year}
        {isCurrent ? " · esta semana" : ""}
      </p>
      <h1 className="mt-2">
        Agenda da <Gold>semana</Gold>
      </h1>
      <p className="mt-4 max-w-2xl text-ice-70">
        {RANGE_DAY.format(utc(days[0]))} a {RANGE_DAY.format(utc(days[6]))} de {YEAR.format(utc(days[6]))}. Datas-com e
        pagamentos de proventos anunciados, fatos relevantes entregues à CVM e a agenda macro — só o que tem data e fonte.
      </p>

      <nav aria-label="Outras semanas" className="mt-6 flex flex-wrap items-center gap-x-6 gap-y-2 text-table">
        <QueryLink href={weekPath(previous)} className="text-gold underline underline-offset-4">
          ← Semana anterior
        </QueryLink>
        {!isCurrent ? (
          <QueryLink href="/agenda" className="text-gold underline underline-offset-4">
            Esta semana
          </QueryLink>
        ) : null}
        <QueryLink href={weekPath(next)} className="text-gold underline underline-offset-4">
          Próxima semana →
        </QueryLink>
        <QueryLink href={monthPath(monthOf(days[3]))} className="text-ice-70 underline underline-offset-4 hover:text-ice">
          Ver o mês
        </QueryLink>
      </nav>

      <div className="mt-8">
        <AgendaFilters />
      </div>

      {events === null ? (
        <p className="mt-10 text-ice-70">A agenda está temporariamente indisponível. Tente novamente em alguns minutos.</p>
      ) : (
        <div data-agenda className="mt-10 space-y-10">
          {events.length >= MAX_EVENTS ? (
            <p className="text-table text-warn">
              Esta semana tem mais de {MAX_EVENTS} eventos; a lista mostra os primeiros {MAX_EVENTS}, em ordem de data.
            </p>
          ) : null}
          {days.map((day) => {
            const list = byDay.get(day) ?? [];
            return (
              <section key={day} id={`dia-${day}`} aria-labelledby={`titulo-${day}`} className="scroll-mt-24">
                <h2 id={`titulo-${day}`} className={cn("text-xl first-letter:uppercase", day === today && "text-gold")}>
                  {DAY.format(utc(day))}
                  {day === today ? <span className="ml-2 text-table font-sans font-normal">hoje</span> : null}
                </h2>
                <div className="mt-3">
                  <EventList events={list} showDate={false} empty="Nenhum evento com data neste dia." />
                </div>
              </section>
            );
          })}
        </div>
      )}

      <SourcesNote
        sources={["Fonte: B3 (proventos)", "Fonte: CVM (fatos relevantes)", "calendários oficiais do BCB, IBGE, FGV, Federal Reserve e B3 (macro)"]}
      />
    </>
  );
}

export function currentWeek(): Week {
  return isoWeek(todayIso());
}
