// Eventos do Umami (site.md §3.4). Sem PII nos dados do evento.
export type UmamiEvent = "subscribe_submit" | "subscribe_confirm" | "analysis_run" | "b3_import" | "asset_cta_click";

type Umami = { track: (name: string, data?: Record<string, string | number | boolean>) => void };

declare global {
  interface Window {
    umami?: Umami;
  }
}

export function track(name: UmamiEvent, data?: Record<string, string | number | boolean>): void {
  if (typeof window === "undefined") return;
  window.umami?.track(name, data);
}
