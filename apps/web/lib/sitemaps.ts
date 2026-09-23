import { MARKET_CLASSES } from "@/lib/market-classes";

// Sitemaps segmentados (site.md §9, plano 4.6): um por classe de papel, um de setores e
// um da agenda. A mesma lista alimenta a rota `/sitemaps/[x].xml` e o `robots.txt`.
export const EXTRA_SITEMAPS = [...MARKET_CLASSES.map((c) => c.slug), "setores", "agenda"];

/** Semanas da agenda no sitemap: as últimas 52 (as indexáveis) e as próximas 4. */
export const AGENDA_SITEMAP_WEEKS = { past: 52, future: 4 };
