import { describe, expect, it } from "vitest";
import { eventView } from "@/lib/event-view";
import type { MarketEvent } from "@/lib/market";

const base = { id: "x", date: "2026-09-24", source: "b3", payload: null } as const;

describe("eventView", () => {
  it("provento mostra valor por ação e linka para os proventos do papel certo", () => {
    const view = eventView({
      ...base,
      kind: "ex_date",
      ticker: "MXRF11",
      security_type: "fii",
      title: "MXRF11 — Rendimento (data-com)",
      payload: { tipo: "Rendimento", valor_por_acao: "0.09" },
    } satisfies MarketEvent);
    expect(view.group).toBe("proventos");
    expect(view.badge).toBe("Data-com");
    expect(view.detail).toBe("R$ 0,09 por ação");
    expect(view.href).toBe("/fiis/MXRF11#proventos");
    expect(view.source).toBe("Fonte: B3");
  });

  it("comunicado leva a categoria da CVM e linka para os comunicados", () => {
    const view = eventView({
      ...base,
      kind: "document",
      ticker: "PETR4",
      security_type: "stock",
      title: "PETR4 — Fato Relevante",
      source: "cvm_ipe",
      payload: { categoria: "Fato Relevante", assunto: "Aquisição de ativo" },
    } satisfies MarketEvent);
    expect(view.badge).toBe("Fato Relevante");
    expect(view.detail).toBe("Aquisição de ativo");
    expect(view.href).toBe("/acoes/PETR4#comunicados");
  });

  it("macro linka para o calendário oficial e diz de onde veio", () => {
    const view = eventView({
      ...base,
      kind: "macro",
      ticker: null,
      security_type: null,
      title: "Copom — decisão da taxa Selic",
      source: "agenda",
      payload: { fonte: "https://www.bcb.gov.br/controleinflacao/calendarioreunioescopom", detalhe: null },
    } satisfies MarketEvent);
    expect(view.external).toBe(true);
    expect(view.source).toBe("Fonte: bcb.gov.br");
    expect(view.detail).toBeNull();
  });
});
