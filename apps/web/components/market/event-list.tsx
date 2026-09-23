import Link from "next/link";
import type { MarketEvent } from "@/lib/market";
import { eventView } from "@/lib/event-view";
import { classOf } from "@/lib/agenda";
import { date as formatDate } from "@/lib/format";
import { Badge } from "@/components/ui/badge";

// Lista de eventos da agenda (plano 3.5/4.2): data, tipo, o que aconteceu, valor e
// fonte. Usada na tab Eventos de `/mercado` e dentro de cada dia da `/agenda`.
//
// Os atributos `data-grupo` e `data-classe` são o gancho do filtro da `/agenda`
// (`AgendaFilters`), que esconde itens por CSS sem refazer a página.

type Props = {
  events: MarketEvent[];
  /** Mostrar a data em cada item (a lista de um dia só não precisa). */
  showDate?: boolean;
  empty?: string;
};

export function EventList({ events, showDate = true, empty = "Nenhum evento neste período." }: Props) {
  if (events.length === 0) {
    return <p className="text-table text-ice-70">{empty}</p>;
  }

  return (
    <ul className="divide-y divide-navy-3 rounded-lg border border-navy-3 bg-navy-2">
      {events.map((event) => {
        const view = eventView(event);
        return (
          <li
            key={event.id}
            data-grupo={view.group}
            data-classe={classOf(event.security_type)}
            className="flex flex-col gap-1 px-4 py-3 text-table sm:flex-row sm:items-baseline sm:gap-4"
          >
            {showDate ? (
              <time dateTime={event.date} className="w-20 shrink-0 tabular-nums text-ice-70">
                {formatDate(event.date)}
              </time>
            ) : null}
            <Badge tone={view.group === "macro" ? "gold" : "neutral"} className="w-fit shrink-0">
              {view.badge}
            </Badge>
            <span className="min-w-0 flex-1">
              {view.href ? (
                <Link
                  href={view.href}
                  {...(view.external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
                  className="underline decoration-ice-70/40 underline-offset-4 hover:decoration-ice"
                >
                  {view.title}
                </Link>
              ) : (
                view.title
              )}
              {view.detail ? <span className="text-ice-70"> · {view.detail}</span> : null}
            </span>
            <span className="shrink-0 text-xs text-ice-70">{view.source}</span>
          </li>
        );
      })}
    </ul>
  );
}
