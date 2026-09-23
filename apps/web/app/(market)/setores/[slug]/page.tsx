import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Section } from "@/components/site/section";
import {
  Pagination,
  SortableSecurityTable,
  type ColumnKey,
} from "@/components/market/sortable-security-table";
import { SourceBadge } from "@/components/market/source-badge";
import { SourcesNote } from "@/components/market/sources-note";
import { Value } from "@/components/market/value";
import { JsonLd } from "@/components/site/json-ld";
import { pathFor } from "@/components/market/ticker-link";
import { compactCurrency } from "@/lib/format";
import { ApiError } from "@/lib/api-client";
import { getSector, listSecurities, optional, type SectorDetail } from "@/lib/market";
import { isDefaultSort, parseSort, sortPhrase, sortTitle, type SortField } from "@/lib/market-sort";
import { breadcrumbJsonLd, siteUrl } from "@/lib/seo";

type Params = { slug: string };
type Search = { sort?: string; dir?: string; page?: string };

// `/setores/[slug]` (site.md §2.1, plano 4.4): os papéis do segmento com cotação,
// variação, liquidez, P/L, P/VP, DY 12 m e valor de mercado; ordem escolhida pelo leitor
// (padrão: liquidez), com o estado na URL. Os agregados são fato — contagem e soma —,
// nunca média de múltiplo nem "setor descontado".

const PAGE_SIZE = 100;

const SORTABLE: SortField[] = ["volume", "change", "ticker", "market_cap", "dy_12m", "pe", "pvp", "roe"];

const COLUMNS: Record<string, ColumnKey[]> = {
  b3_segment: ["price", "change", "volume", "pe", "pvp", "dy_12m", "market_cap"],
  // FII não tem lucro por ação no sentido da DFP: P/L e valor de mercado ficam de fora.
  fii_segment: ["price", "change", "volume", "pvp", "dy_12m"],
};

async function loadSector(slug: string): Promise<SectorDetail | "missing" | null> {
  try {
    return await getSector(slug);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return "missing";
    console.error("[setor] indisponível:", error);
    return null;
  }
}

export async function generateMetadata({
  params,
  searchParams,
}: {
  params: Promise<Params>;
  searchParams: Promise<Search>;
}): Promise<Metadata> {
  const { slug } = await params;
  const query = await searchParams;
  const sector = await optional(getSector(slug));
  if (!sector) return {};
  const sort = parseSort(query, SORTABLE);
  const suffix = isDefaultSort(sort) ? "" : ` — ${sortTitle(sort).toLowerCase()}`;
  return {
    title: `${sector.name}: papéis do segmento na B3${suffix}`,
    description: `${sector.securities_count} ${sector.securities_count === 1 ? "papel" : "papéis"} do segmento ${sector.name}${sector.sector ? ` (${sector.sector})` : ""}, com cotação, liquidez e indicadores. Cada número com fonte e data.`,
    alternates: { canonical: `/setores/${sector.slug}` },
    ...(Object.keys(query).length > 0 ? { robots: { index: false, follow: true } } : {}),
  };
}

export default async function SectorPage({
  params,
  searchParams,
}: {
  params: Promise<Params>;
  searchParams: Promise<Search>;
}) {
  const { slug } = await params;
  const sector = await loadSector(slug);
  if (sector === "missing") notFound();

  const query = await searchParams;
  const sort = parseSort(query, SORTABLE);
  const pageNumber = Math.max(1, Math.min(100, Number.parseInt(query.page ?? "1", 10) || 1));
  const page = sector
    ? await optional(
        listSecurities({ sector: slug, sort: sort.field, dir: sort.dir, page: pageNumber, page_size: PAGE_SIZE }),
      )
    : null;
  const basePath = `/setores/${slug}`;

  if (!sector) {
    return (
      <Section wide className="pt-16 md:pt-20">
        <h1>Setor</h1>
        <p className="mt-4 text-ice-70">Este setor está temporariamente indisponível. Tente novamente em alguns minutos.</p>
      </Section>
    );
  }

  const trail = [sector.sector, sector.subsector].filter(
    (part, index, all): part is string => Boolean(part) && all.indexOf(part) === index && part !== sector.name,
  );

  return (
    <>
      <JsonLd
        data={breadcrumbJsonLd([
          { name: "Início", path: "/" },
          { name: "Setores", path: "/setores" },
          { name: sector.name, path: basePath },
        ])}
      />
      {page && page.items.length > 0 ? (
        <JsonLd
          data={{
            "@context": "https://schema.org",
            "@type": "ItemList",
            name: `Papéis do segmento ${sector.name}`,
            numberOfItems: page.total,
            itemListElement: page.items.map((item, index) => ({
              "@type": "ListItem",
              position: (page.page - 1) * page.page_size + index + 1,
              url: siteUrl(pathFor(item.type, item.ticker)),
              name: `${item.ticker} — ${item.trade_name ?? item.company_name}`,
            })),
          }}
        />
      ) : null}

      <Section wide className="pt-16 md:pt-20">
        <nav aria-label="Trilha" className="text-table text-ice-70">
          <Link href="/setores" className="underline underline-offset-4 hover:text-ice">
            Setores
          </Link>
          {trail.map((part) => (
            <span key={part}> / {part}</span>
          ))}
        </nav>
        <h1 className="mt-3">{sector.name}</h1>

        <dl className="mt-8 grid max-w-2xl grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="rounded-lg border border-navy-3 bg-navy-2 p-4">
            <dt className="text-table text-ice-70">Papéis no segmento</dt>
            <dd className="mt-1 font-display text-2xl tabular-nums">{sector.securities_count}</dd>
          </div>
          <div className="rounded-lg border border-navy-3 bg-navy-2 p-4">
            <dt className="text-table text-ice-70">Valor de mercado somado</dt>
            <dd className="mt-1 font-display text-2xl tabular-nums">
              <Value reason={sector.missing_reasons.market_cap}>{compactCurrency(sector.market_cap)}</Value>
            </dd>
            {sector.market_cap !== null ? (
              <dd className="mt-1 text-xs text-ice-70">
                soma de {sector.market_cap_count} {sector.market_cap_count === 1 ? "papel" : "papéis"} com valor de
                mercado no dia
              </dd>
            ) : null}
          </div>
        </dl>
        <SourceBadge source={sector.source} className="mt-3" />

        <div className="mt-12">
          {page ? (
            <>
              <h2 className="sr-only">{sortTitle(sort)}</h2>
              <p className="mb-4 text-table text-ice-70">
                {page.total} {page.total === 1 ? "papel" : "papéis"} · {sortPhrase(sort)}. Clique no cabeçalho de uma
                coluna para mudar a ordem.
              </p>
              <SortableSecurityTable
                rows={page.items}
                columns={COLUMNS[sector.kind] ?? COLUMNS.b3_segment}
                sort={sort}
                basePath={basePath}
                caption={`Papéis do segmento ${sector.name}`}
              />
              <Pagination
                page={page.page}
                pages={Math.ceil(page.total / page.page_size)}
                basePath={basePath}
                sort={sort}
              />
            </>
          ) : (
            <p className="text-ice-70">A lista de papéis está temporariamente indisponível.</p>
          )}
        </div>

        <SourcesNote sources={[sector.source, "Fonte: B3 (cotação)", "Fonte: CVM (indicadores)"]} />
      </Section>
    </>
  );
}
