import { MARKET_CLASSES, classBySlug } from "@/lib/market-classes";
import { listSecurities, optional } from "@/lib/market";
import { siteUrl } from "@/lib/seo";
import { pathFor } from "@/components/market/ticker-link";

// Sitemaps **segmentados por classe** (§9): `/sitemap/acoes.xml`, `/sitemap/fiis.xml`…
//
// São milhares de URLs somadas. Um sitemap único passaria do limite de 50 mil entradas
// e, pior, faria o Search Console reportar erros de cobertura sem dizer de qual classe.
// Segmentado, dá para ver qual parte do catálogo o Google não está indexando.
//
// `lastmod` é a data da carga, não a de hoje: mentir no `lastmod` faz o crawler parar de
// confiar nele.

export const revalidate = 3600;

export function generateStaticParams() {
  return MARKET_CLASSES.map((c) => ({ classe: `${c.slug}.xml` }));
}

export async function GET(_request: Request, { params }: { params: Promise<{ classe: string }> }) {
  const { classe } = await params;
  const meta = classBySlug(classe.replace(/\.xml$/, ""));
  if (!meta) {
    return new Response("Not found", { status: 404 });
  }

  const page = await optional(listSecurities({ type: meta.type, page_size: 100 }));
  const urls = (page?.items ?? []).map((item) => siteUrl(pathFor(item.type, item.ticker)));

  const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${[siteUrl(`/${meta.slug}`), ...urls]
  .map((loc) => `  <url><loc>${loc}</loc></url>`)
  .join("\n")}
</urlset>
`;

  return new Response(body, {
    headers: {
      "Content-Type": "application/xml; charset=utf-8",
      "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=86400",
    },
  });
}
