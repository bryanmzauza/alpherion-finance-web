import type { Metadata } from "next";
import { notFound, permanentRedirect } from "next/navigation";
import { Section } from "@/components/site/section";
import { AssetCTA } from "@/components/market/asset-cta";
import { DividendTable } from "@/components/market/dividend-table";
import { DocumentList } from "@/components/market/document-list";
import { FinancialTable } from "@/components/market/financial-table";
import { HistoryChart } from "@/components/market/history-chart";
import { IndicatorGrid } from "@/components/market/indicator-grid";
import { PriceHeader } from "@/components/market/price-header";
import { SameSectorList } from "@/components/market/same-sector-list";
import { SourceBadge } from "@/components/market/source-badge";
import { JsonLd } from "@/components/site/json-ld";
import { FII_INDICATOR_KEYS } from "@/content/indicadores";
import { classBySlug, classByType } from "@/lib/market-classes";
import { pathFor } from "@/components/market/ticker-link";
import {
  getDividends,
  getDocuments,
  getFinancials,
  getHistory,
  getSecurity,
  listSecurities,
  optional,
} from "@/lib/market";
import { companyJsonLd, breadcrumbJsonLd } from "@/lib/seo";

type Params = { classe: string; ticker: string };

export const revalidate = 3600;

export async function generateMetadata({
  params,
}: {
  params: Promise<Params>;
}): Promise<Metadata> {
  const { classe, ticker } = await params;
  const meta = classBySlug(classe);
  const detail = await optional(getSecurity(ticker));
  if (!meta || !detail) return {};

  const name = detail.profile.trade_name ?? detail.profile.company_name;
  return {
    // Título padronizado (§9): ticker, o que a página tem, marca.
    title: `${detail.profile.ticker} — cotação, proventos e indicadores`,
    description: `${name}: cotação, histórico, proventos, indicadores e demonstrações de ${detail.profile.ticker}, com a fonte de cada número.`,
    alternates: { canonical: pathFor(detail.profile.type, detail.profile.ticker) },
  };
}

export default async function SecurityPage({ params }: { params: Promise<Params> }) {
  const { classe, ticker } = await params;
  const requested = ticker.toUpperCase();

  // Ticker em minúsculo na URL → canônica em maiúsculo (301). Endereço de ativo tem
  // uma forma só; duas formas indexadas dividem o sinal de SEO ao meio.
  if (ticker !== requested) {
    permanentRedirect(`/${classe}/${requested}`);
  }

  const detail = await optional(getSecurity(requested));
  if (!detail) notFound();

  // Ticker na classe errada (`/acoes/MXRF11`) → 301 para a classe certa, em vez de 404:
  // o link existe por aí e o leitor procurou o papel certo.
  const canonical = classByType(detail.profile.type);
  if (canonical && canonical.slug !== classe) {
    permanentRedirect(pathFor(detail.profile.type, requested));
  }
  if (!classBySlug(classe)) notFound();

  const isFii = detail.profile.type === "fii" || detail.profile.type === "fiagro";

  // Blocos independentes: cada um pode faltar sem levar a página junto.
  const [history, dividends, documents, financials, sameSector] = await Promise.all([
    optional(getHistory(requested, "1a")),
    optional(getDividends(requested)),
    optional(getDocuments(requested)),
    isFii ? Promise.resolve(null) : optional(getFinancials(requested)),
    detail.profile.sector_slug
      ? optional(listSecurities({ sector: detail.profile.sector_slug, page_size: 10 }))
      : Promise.resolve(null),
  ]);

  return (
    <>
      <JsonLd data={companyJsonLd(detail.profile)} />
      <JsonLd
        data={breadcrumbJsonLd([
          { name: "Início", path: "/" },
          { name: classBySlug(classe)?.label ?? classe, path: `/${classe}` },
          { name: detail.profile.ticker, path: pathFor(detail.profile.type, requested) },
        ])}
      />

      <Section wide className="pt-12 md:pt-16">
        <PriceHeader profile={detail.profile} price={detail.price} />

        <div className="mt-12 space-y-16">
          <section aria-labelledby="historico">
            <h2 id="historico">Histórico</h2>
            <div className="mt-6">
              <HistoryChart quotes={history ?? []} label={`Cotação de ${requested}`} />
            </div>
            <SourceBadge source={detail.price.source} className="mt-4" />
          </section>

          <IndicatorGrid
            indicators={detail.indicators}
            only={isFii ? FII_INDICATOR_KEYS : undefined}
          />

          <section aria-labelledby="proventos">
            <h2 id="proventos">Proventos e eventos</h2>
            <p className="mt-2 text-table text-ice-70">
              O que o emissor anunciou — não é o que você recebeu, nem projeção.
            </p>
            <div className="mt-6">
              <DividendTable events={dividends ?? []} />
            </div>
          </section>

          {financials ? <FinancialTable financials={financials} /> : null}

          <section aria-labelledby="comunicados">
            <h2 id="comunicados">Comunicados à CVM</h2>
            <p className="mt-2 text-table text-ice-70">
              Título, categoria, data e link para o documento na CVM. Sem resumo.
            </p>
            <div className="mt-6">
              <DocumentList documents={documents?.items ?? []} />
            </div>
          </section>

          <Registration profile={detail.profile} />

          {sameSector ? (
            <SameSectorList
              securities={sameSector.items}
              sectorSlug={detail.profile.sector_slug}
              sectorName={detail.profile.segment ?? detail.profile.sector}
              currentTicker={requested}
            />
          ) : null}

          <AssetCTA ticker={detail.profile.ticker} />
        </div>
      </Section>
    </>
  );
}

function Registration({ profile }: { profile: Awaited<ReturnType<typeof getSecurity>>["profile"] }) {
  const rows: [string, string | null][] = [
    ["Razão social", profile.company_name],
    ["CNPJ", formatCnpj(profile.cnpj)],
    ["Código CVM", profile.cvm_code ? String(profile.cvm_code) : null],
    ["ISIN", profile.isin],
    ["Setor", profile.sector],
    ["Subsetor", profile.subsector],
    ["Segmento", profile.segment],
    ["Segmento de listagem", profile.listing_segment],
    ["Razão do BDR", profile.bdr_ratio],
    ["Índice replicado", profile.etf_index_slug],
  ];

  return (
    <section aria-labelledby="cadastro">
      <h2 id="cadastro">Cadastro</h2>
      <dl className="mt-6 grid gap-x-8 gap-y-3 sm:grid-cols-2">
        {rows
          .filter(([, value]) => value)
          .map(([label, value]) => (
            <div key={label} className="flex gap-2">
              <dt className="text-ice-70">{label}:</dt>
              <dd>{value}</dd>
            </div>
          ))}
      </dl>
      <SourceBadge source={profile.source} className="mt-6" />
    </section>
  );
}

function formatCnpj(cnpj: string | null): string | null {
  if (!cnpj || cnpj.length !== 14) return cnpj;
  return `${cnpj.slice(0, 2)}.${cnpj.slice(2, 5)}.${cnpj.slice(5, 8)}/${cnpj.slice(8, 12)}-${cnpj.slice(12)}`;
}
