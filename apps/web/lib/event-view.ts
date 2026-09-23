import { pathFor } from "@/components/market/ticker-link";
import { groupOf, type EventGroup } from "@/lib/agenda";
import { perShare } from "@/lib/format";
import type { MarketEvent } from "@/lib/market";

// Como um item da agenda aparece na tela: rótulo do tipo, detalhe, link e fonte.
//
// Tudo sai do que a API mandou — nenhum texto aqui qualifica o evento ("importante",
// "atenção"). Um provento é tipo, data e valor por ação; um comunicado é a categoria da
// CVM; um evento macro é o que o órgão anunciou, com o link do calendário oficial.

export type EventView = {
  group: EventGroup;
  badge: string;
  title: string;
  detail: string | null;
  /** Página interna do papel, ou o calendário oficial no caso de evento macro. */
  href: string | null;
  external: boolean;
  source: string;
};

const KIND_BADGE: Record<MarketEvent["kind"], string> = {
  ex_date: "Data-com",
  payment: "Pagamento",
  document: "Comunicado",
  macro: "Macro",
  corporate: "Evento societário",
};

const SOURCE_LABEL: Record<string, string> = {
  b3: "Fonte: B3",
  cvm: "Fonte: CVM",
  cvm_ipe: "Fonte: CVM (IPE)",
};

export function eventView(event: MarketEvent): EventView {
  const payload = event.payload ?? {};
  const text = (key: string) => {
    const value = payload[key];
    return typeof value === "string" && value.trim() ? value.trim() : null;
  };

  if (event.kind === "macro") {
    const url = text("fonte");
    return {
      group: "macro",
      badge: KIND_BADGE.macro,
      title: event.title,
      detail: text("detalhe"),
      href: url,
      external: url !== null,
      source: url ? `Fonte: ${hostOf(url)}` : "Agenda macro",
    };
  }

  const ticker = event.ticker;
  const base = ticker ? pathFor(event.security_type ?? "stock", ticker) : null;

  if (event.kind === "document") {
    return {
      group: "comunicados",
      badge: text("categoria") ?? KIND_BADGE.document,
      title: event.title,
      detail: text("assunto"),
      href: base ? `${base}#comunicados` : null,
      external: false,
      source: SOURCE_LABEL[event.source] ?? `Fonte: ${event.source.toUpperCase()}`,
    };
  }

  const value = text("valor_por_acao");
  const ratio = text("proporcao");
  return {
    group: groupOf(event.kind),
    badge: KIND_BADGE[event.kind],
    title: event.title,
    detail: value ? `${perShare(value)} por ação` : ratio ? `Proporção ${ratio}` : null,
    href: base ? `${base}#proventos` : null,
    external: false,
    source: SOURCE_LABEL[event.source] ?? `Fonte: ${event.source.toUpperCase()}`,
  };
}

function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}
