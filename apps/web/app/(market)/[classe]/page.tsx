import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Section } from "@/components/site/section";
import {
  Pagination,
  SortableSecurityTable,
  type ColumnKey,
} from "@/components/market/sortable-security-table";
import { Gold } from "@/components/ui/gold";
import { MARKET_CLASSES, classBySlug } from "@/lib/market-classes";
import { listSecurities, optional } from "@/lib/market";
import {
  SORT_PRESETS,
  SORTABLE_BY_CLASS,
  isDefaultSort,
  parseSort,
  sortPhrase,
  sortQuery,
  sortTitle,
} from "@/lib/market-sort";
import { cn } from "@/lib/cn";

type Params = { classe: string };
type Search = { sort?: string; dir?: string; page?: string };

// Uma página para as quatro classes: `/acoes`, `/fiis`, `/etfs`, `/bdrs`. O que muda é
// o filtro e o texto, que vivem em `lib/market-classes.ts`.
//
// Ordenação por URL (plano 4.5): `?sort=dy_12m&dir=desc` com o título "Maior dividend
// yield 12 m" — a métrica, sem juízo. A página com parâmetros é `noindex`: a versão que
// o Google indexa é uma só por classe, na ordem padrão (liquidez).
export function generateStaticParams(): Params[] {
  return MARKET_CLASSES.map((c) => ({ classe: c.slug }));
}

// Só as quatro classes conhecidas; qualquer outro caminho é 404 (nada de página vazia).
export const dynamicParams = false;

const PAGE_SIZE = 100;

const COLUMNS: Record<string, ColumnKey[]> = {
  acoes: ["price", "change", "volume", "pe", "pvp", "dy_12m", "roe", "market_cap"],
  fiis: ["price", "change", "volume", "pvp", "dy_12m"],
  etfs: ["price", "change", "volume"],
  bdrs: ["price", "change", "volume"],
};

export async function generateMetadata({
  params,
  searchParams,
}: {
  params: Promise<Params>;
  searchParams: Promise<Search>;
}): Promise<Metadata> {
  const { classe } = await params;
  const query = await searchParams;
  const meta = classBySlug(classe);
  if (!meta) return {};
  const sort = parseSort(query, SORTABLE_BY_CLASS[classe]);
  const hasParams = Object.keys(query).length > 0;
  return {
    title: isDefaultSort(sort) ? meta.title : `${meta.label} — ${sortTitle(sort).toLowerCase()}`,
    description: meta.description,
    alternates: { canonical: `/${meta.slug}` },
    ...(hasParams ? { robots: { index: false, follow: true } } : {}),
  };
}

export default async function ClassPage({
  params,
  searchParams,
}: {
  params: Promise<Params>;
  searchParams: Promise<Search>;
}) {
  const { classe } = await params;
  const meta = classBySlug(classe);
  if (!meta) notFound();

  const query = await searchParams;
  const sort = parseSort(query, SORTABLE_BY_CLASS[classe]);
  const pageNumber = Math.max(1, Math.min(1000, Number.parseInt(query.page ?? "1", 10) || 1));

  const page = await optional(
    listSecurities({
      type: meta.type,
      sort: sort.field,
      dir: sort.dir,
      page: pageNumber,
      page_size: PAGE_SIZE,
    }),
  );
  const presets = SORT_PRESETS[classe] ?? [];
  const basePath = `/${meta.slug}`;

  return (
    <Section wide className="pt-16 md:pt-20">
      <h1>
        <Gold>{meta.label}</Gold> na B3
      </h1>
      <p className="mt-4 max-w-2xl text-ice-70">{meta.intro}</p>

      {presets.length > 0 ? (
        <nav aria-label="Ordenar a lista por" className="mt-8">
          <ul className="flex flex-wrap gap-2">
            {presets.map((preset) => {
              const active = preset.field === sort.field && preset.dir === sort.dir;
              return (
                <li key={`${preset.field}-${preset.dir}`}>
                  <Link
                    href={`${basePath}${sortQuery(preset)}`}
                    aria-current={active ? "true" : undefined}
                    className={cn(
                      "inline-block rounded-full border px-4 py-1.5 text-table",
                      active
                        ? "border-gold text-gold"
                        : "border-navy-3 text-ice-70 hover:border-gold hover:text-ice",
                    )}
                  >
                    {sortTitle(preset)}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      ) : null}

      <div className="mt-8">
        {page ? (
          <>
            <h2 className="sr-only">{sortTitle(sort)}</h2>
            <p className="mb-4 text-table text-ice-70">
              {page.total} {page.total === 1 ? "papel listado" : "papéis listados"} · {sortPhrase(sort)}
              {sort.field !== "volume" ? " (papel sem o número fica no fim)" : ""}
            </p>
            <SortableSecurityTable
              rows={page.items}
              columns={COLUMNS[classe] ?? COLUMNS.etfs}
              sort={sort}
              basePath={basePath}
              caption={`${meta.label} listados na B3`}
            />
            <Pagination
              page={page.page}
              pages={Math.ceil(page.total / page.page_size)}
              basePath={basePath}
              sort={sort}
            />
          </>
        ) : (
          <p className="text-ice-70">
            A lista está temporariamente indisponível. Tente novamente em alguns minutos.
          </p>
        )}
      </div>
    </Section>
  );
}
