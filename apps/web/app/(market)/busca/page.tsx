import type { Metadata } from "next";
import Link from "next/link";
import { Section } from "@/components/site/section";
import { Value } from "@/components/market/value";
import { SearchBox } from "@/components/search/search-box";
import { Table, Td, Th, Thead, Tr } from "@/components/ui/table";
import { GROUP_LABELS, MAX_QUERY, MIN_QUERY, hitHref } from "@/lib/asset-search";
import { currency } from "@/lib/format";
import { searchAssets, optional, type AssetSearchGroup } from "@/lib/market";
import { MARKET_LINKS } from "@/lib/market-classes";

// `/busca?q=` — resultado da busca global (site.md §2.1, plano 4.5): agrupado por
// classe, com cotação e link. SSR (cada termo é uma página) e `noindex`: busca interna
// indexada vira milhares de páginas finas que competem com as páginas de ativo.

type Search = { q?: string | string[] };

export const metadata: Metadata = {
  title: "Busca",
  robots: { index: false, follow: true },
};

/** Por classe na página de resultados — mais que no autocomplete do header. */
const PER_GROUP = 20;

export default async function SearchPage({ searchParams }: { searchParams: Promise<Search> }) {
  const raw = (await searchParams).q;
  const term = (Array.isArray(raw) ? raw[0] : raw ?? "").trim().slice(0, MAX_QUERY);
  const valid = term.length >= MIN_QUERY;
  const result = valid ? await optional(searchAssets(term, PER_GROUP)) : null;
  const total = result?.groups.reduce((sum, g) => sum + g.items.length, 0) ?? 0;

  return (
    <Section wide className="pt-16 md:pt-20">
      <h1>Busca</h1>
      <SearchBox size="lg" defaultValue={term} className="mt-6 max-w-2xl" />

      <div className="mt-10" aria-live="polite">
        {!valid ? (
          <p className="text-ice-70">Digite pelo menos {MIN_QUERY} letras: um ticker (PETR4), o nome da empresa ou do índice.</p>
        ) : result === null ? (
          <p className="text-ice-70">A busca está temporariamente indisponível. Tente novamente em alguns minutos.</p>
        ) : total === 0 ? (
          <NoResults term={term} />
        ) : (
          <>
            <p className="text-table text-ice-70">
              {total} {total === 1 ? "resultado" : "resultados"} para “{term}”
            </p>
            <div className="mt-8 space-y-12">
              {result.groups.map((group) => (
                <ResultGroup key={group.asset_class} group={group} />
              ))}
            </div>
          </>
        )}
      </div>
    </Section>
  );
}

function ResultGroup({ group }: { group: AssetSearchGroup }) {
  const label = GROUP_LABELS[group.asset_class];
  const hasPrice = !["index", "treasury", "crypto"].includes(group.asset_class);
  const id = `grupo-${group.asset_class}`;
  return (
    <section aria-labelledby={id}>
      <h2 id={id}>{label}</h2>
      <div className="mt-4">
        <Table caption={`Resultados em ${label}`}>
          <Thead>
            <Tr>
              <Th>{hasPrice ? "Papel" : "Nome"}</Th>
              {hasPrice ? <Th className="hidden sm:table-cell">Empresa</Th> : null}
              {hasPrice ? <Th className="text-right">Cotação</Th> : null}
            </Tr>
          </Thead>
          <tbody>
            {group.items.map((hit) => (
              <Tr key={`${hit.type}:${hit.code}`}>
                <Td>
                  <Link href={hitHref(hit)} className="underline decoration-ice-70/40 underline-offset-4 hover:decoration-ice">
                    {hasPrice ? hit.code : hit.name}
                  </Link>
                </Td>
                {hasPrice ? <Td className="hidden sm:table-cell">{hit.name}</Td> : null}
                {hasPrice ? (
                  <Td numeric className="tabular-nums">
                    <Value reason={hit.missing_reasons?.price}>{currency(hit.price)}</Value>
                  </Td>
                ) : null}
              </Tr>
            ))}
          </tbody>
        </Table>
      </div>
      {hasPrice ? <p className="mt-2 text-xs text-ice-70">Cotação do último pregão. Fonte: B3.</p> : null}
    </section>
  );
}

function NoResults({ term }: { term: string }) {
  return (
    <div>
      <p className="text-ice-70">Nada encontrado para “{term}”. Confira o código ou procure pela lista da classe:</p>
      <ul className="mt-4 flex flex-wrap gap-2">
        {MARKET_LINKS.map((link) => (
          <li key={link.href}>
            <Link
              href={link.href}
              className="inline-block rounded-full border border-navy-3 px-4 py-2 text-table hover:border-gold hover:text-gold"
            >
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
