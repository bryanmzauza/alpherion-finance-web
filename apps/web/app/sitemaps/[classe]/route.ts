import { classBySlug } from "@/lib/market-classes";
import { getSectors, listSecurities, optional } from "@/lib/market";
import { siteUrl } from "@/lib/seo";
import { AGENDA_SITEMAP_WEEKS, EXTRA_SITEMAPS } from "@/lib/sitemaps";
import { isoWeek, shiftWeek, todayIso, weekPath } from "@/lib/agenda";
import { pathFor } from "@/components/market/ticker-link";

// Sitemaps **segmentados** (§9): `/sitemaps/acoes.xml`, `/sitemaps/fiis.xml`…, e desde a
// Etapa 4 `/sitemaps/setores.xml` e `/sitemaps/agenda.xml`.
//
// `/sitemaps/` e não `/sitemap/`: o `app/sitemap.ts` vira em dev a rota dinâmica
// `/sitemap/[__metadata_id__]`, e duas rotas dinâmicas no mesmo segmento derrubam o
// `next dev` inteiro ("different slug names for the same dynamic path").
//
// São milhares de URLs somadas. Um sitemap único passaria do limite de 50 mil entradas
// e, pior, faria o Search Console reportar erros de cobertura sem dizer de qual parte.
// Segmentado, dá para ver qual parte do catálogo o Google não está indexando.
//
// `lastmod` é a data da carga, não a de hoje: mentir no `lastmod` faz o crawler parar de
// confiar nele. (Por isso as semanas da agenda saem sem `lastmod`.)

export const revalidate = 3600;

export function generateStaticParams() {
  return EXTRA_SITEMAPS.map((slug) => ({ classe: `${slug}.xml` }));
}

export async function GET(_request: Request, { params }: { params: Promise<{ classe: string }> }) {
  const { classe } = await params;
  const slug = classe.replace(/\.xml$/, "");

  let urls: string[] | null = null;
  if (slug === "setores") {
    const sectors = await optional(getSectors());
    urls = [siteUrl("/setores"), ...(sectors ?? []).map((s) => siteUrl(`/setores/${s.slug}`))];
  } else if (slug === "agenda") {
    urls = [siteUrl("/agenda"), ...agendaWeeks().map((path) => siteUrl(path))];
  } else {
    const meta = classBySlug(slug);
    if (meta) {
      urls = [siteUrl(`/${meta.slug}`), ...(await allSecurities(meta.type))];
    }
  }

  if (urls === null) {
    return new Response("Not found", { status: 404 });
  }

  const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.map((loc) => `  <url><loc>${loc}</loc></url>`).join("\n")}
</urlset>
`;

  return new Response(body, {
    headers: {
      "Content-Type": "application/xml; charset=utf-8",
      "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=86400",
    },
  });
}

/** Todas as páginas de ativo da classe — a API pagina de 100 em 100. */
async function allSecurities(type: Parameters<typeof listSecurities>[0]["type"]): Promise<string[]> {
  const urls: string[] = [];
  for (let page = 1; page <= MAX_PAGES; page += 1) {
    const result = await optional(listSecurities({ type, page, page_size: 100, sort: "ticker", dir: "asc" }));
    if (!result) break;
    urls.push(...result.items.map((item) => siteUrl(pathFor(item.type, item.ticker))));
    if (page * result.page_size >= result.total) break;
  }
  return urls;
}

/** Teto de páginas por sitemap: 50 × 100 = 5 mil papéis, bem acima de qualquer classe da B3. */
const MAX_PAGES = 50;

/** As semanas indexáveis da agenda (as páginas de mais de 12 meses são `noindex`). */
function agendaWeeks(): string[] {
  const current = isoWeek(todayIso());
  const paths: string[] = [];
  for (let delta = -AGENDA_SITEMAP_WEEKS.past; delta <= AGENDA_SITEMAP_WEEKS.future; delta += 1) {
    paths.push(weekPath(shiftWeek(current, delta)));
  }
  return paths;
}
