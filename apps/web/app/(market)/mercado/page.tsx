import type { Metadata } from "next";
import Link from "next/link";
import { Section } from "@/components/site/section";
import { EventList } from "@/components/market/event-list";
import { MoversList } from "@/components/market/movers-list";
import { SourcesNote } from "@/components/market/sources-note";
import { StripGrid } from "@/components/market/strip-grid";
import { SearchBox } from "@/components/search/search-box";
import { Gold } from "@/components/ui/gold";
import { Tabs } from "@/components/ui/tabs";
import { AGENDA_DOCUMENT_CATEGORIES, addDays, todayIso } from "@/lib/agenda";
import { getEvents, getOverview, optional, type MarketEvent } from "@/lib/market";

// `/mercado` — o portal (site.md §2.1, plano 4.2). Faixa completa, blocos por classe
// com contadores **factuais**, a tab Hoje (três listas, cada uma com a métrica no
// título) e a tab Eventos (proventos da semana, fatos relevantes do dia e macro).
//
// ISR de 5 min, o mesmo tempo da faixa; o `revalidate_pages` renova depois da carga.

export const revalidate = 300;

export const metadata: Metadata = {
  title: "Mercado hoje — índices, câmbio, juros e agenda",
  description:
    "Ibovespa, IFIX, dólar, Selic, CDI, IPCA e bitcoin, as maiores variações e o volume do dia, e a agenda de proventos, fatos relevantes e macro. Cada número com fonte e data.",
  alternates: { canonical: "/mercado" },
};

const PROVENTOS_LIMIT = 100;

export default async function MarketPage() {
  const today = todayIso();
  const [overview, proventos, fatos, macro] = await Promise.all([
    optional(getOverview()),
    optional(
      getEvents({
        from: today,
        to: addDays(today, 6),
        kind: ["ex_date", "payment"],
        limit: PROVENTOS_LIMIT,
      }),
    ),
    optional(
      getEvents({
        from: today,
        to: today,
        kind: ["document"],
        category: AGENDA_DOCUMENT_CATEGORIES,
        limit: 100,
      }),
    ),
    optional(getEvents({ from: today, to: addDays(today, 13), kind: ["macro"], limit: 50 })),
  ]);

  return (
    <Section wide className="pt-12 md:pt-16">
      <h1>
        Mercado <Gold>hoje</Gold>
      </h1>
      <p className="mt-4 max-w-2xl text-ice-70">
        Índices, câmbio, juros e inflação, o que mais variou e o que mais negociou no último pregão,
        e a agenda da semana. Cada número com a fonte ao lado.
      </p>
      <SearchBox size="lg" className="mt-8 max-w-2xl" />

      <section aria-labelledby="indicadores" className="mt-14">
        <h2 id="indicadores">Indicadores</h2>
        <div className="mt-6">
          {overview ? (
            <StripGrid items={overview.strip} />
          ) : (
            <Unavailable text="Os indicadores estão temporariamente indisponíveis." />
          )}
        </div>
      </section>

      <section aria-labelledby="por-classe" className="mt-14">
        <h2 id="por-classe">Por classe</h2>
        <ClassBlocks counters={overview?.counters ?? null} />
      </section>

      <div className="mt-14">
        <Tabs
          tabs={[
            {
              id: "hoje",
              label: "Hoje",
              content: overview ? (
                <div className="grid gap-12 xl:grid-cols-3 xl:gap-8">
                  <MoversList id="maiores-altas" title="Maiores altas" list={overview.gainers} />
                  <MoversList id="maiores-baixas" title="Maiores baixas" list={overview.losers} />
                  <MoversList id="mais-negociadas" title="Mais negociadas" list={overview.most_traded} />
                </div>
              ) : (
                <Unavailable text="As listas do dia estão temporariamente indisponíveis." />
              ),
            },
            {
              id: "eventos",
              label: "Eventos",
              content: (
                <div className="space-y-12">
                  <EventBlock
                    id="proventos-semana"
                    title="Proventos nos próximos 7 dias"
                    intro="Datas-com e pagamentos anunciados pelos emissores."
                    events={proventos}
                    truncated={proventos?.length === PROVENTOS_LIMIT}
                    empty="Nenhuma data-com nem pagamento anunciado para os próximos 7 dias."
                  />
                  <EventBlock
                    id="fatos-hoje"
                    title="Fatos relevantes de hoje"
                    intro="Documentos entregues à CVM na categoria Fato Relevante. Título e link, sem resumo."
                    events={fatos}
                    empty="Nenhum fato relevante entregue à CVM hoje até a última carga."
                  />
                  <EventBlock
                    id="macro"
                    title="Agenda macro das próximas duas semanas"
                    intro="Copom, IPCA, IGP-M, FOMC e vencimentos de opções, com o link do calendário oficial."
                    events={macro}
                    empty="Nenhum evento macro nas próximas duas semanas."
                  />
                  <Link
                    href="/agenda"
                    className="inline-block text-gold underline decoration-gold/40 underline-offset-4 hover:decoration-gold"
                  >
                    Ver a agenda completa da semana →
                  </Link>
                </div>
              ),
            },
          ]}
        />
      </div>

      <SourcesNote
        sources={[
          ...(overview?.strip.map((item) => item.source) ?? []),
          overview?.gainers.source,
        ]}
      />
    </Section>
  );
}

function EventBlock({
  id,
  title,
  intro,
  events,
  empty,
  truncated = false,
}: {
  id: string;
  title: string;
  intro: string;
  events: MarketEvent[] | null;
  empty: string;
  truncated?: boolean;
}) {
  return (
    <section aria-labelledby={id}>
      <h3 id={id} className="font-display text-xl font-semibold">
        {title}
      </h3>
      <p className="mt-1 mb-4 text-table text-ice-70">{intro}</p>
      {events ? <EventList events={events} empty={empty} /> : <Unavailable text="A agenda está temporariamente indisponível." />}
      {truncated ? (
        <p className="mt-3 text-table text-ice-70">
          Mostrando os primeiros {events?.length}.{" "}
          <Link href="/agenda?tipo=proventos" className="text-gold underline underline-offset-4">
            Ver todos na agenda
          </Link>
        </p>
      ) : null}
    </section>
  );
}

const NUMBER = new Intl.NumberFormat("pt-BR");

function ClassBlocks({ counters }: { counters: Record<string, number> | null }) {
  const n = (...keys: string[]) =>
    counters ? keys.reduce((sum, key) => sum + (counters[key] ?? 0), 0) : null;
  const count = (value: number | null, singular: string, plural: string) =>
    value === null ? null : `${NUMBER.format(value)} ${value === 1 ? singular : plural}`;

  const blocks = [
    {
      href: "/acoes",
      label: "Ações",
      facts: [count(n("stock", "unit"), "papel listado", "papéis listados"), count(n("b3_segments"), "segmento B3", "segmentos B3")],
    },
    {
      href: "/fiis",
      label: "FIIs",
      facts: [count(n("fii", "fiagro"), "fundo listado", "fundos listados"), count(n("fii_segments"), "segmento", "segmentos")],
    },
    { href: "/etfs", label: "ETFs", facts: [count(n("etf"), "ETF listado", "ETFs listados")] },
    { href: "/bdrs", label: "BDRs", facts: [count(n("bdr"), "BDR listado", "BDRs listados")] },
    { href: "/indices", label: "Índices", facts: [count(n("indices"), "índice da B3", "índices da B3")] },
    { href: "/tesouro", label: "Tesouro Direto", facts: [count(n("treasury"), "título", "títulos")] },
    { href: "/cripto", label: "Cripto", facts: [count(n("crypto"), "criptoativo acompanhado", "criptoativos acompanhados")] },
    { href: "/setores", label: "Setores", facts: ["árvore da classificação B3 e segmentos de FII"] },
  ];

  return (
    <>
      <ul className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {blocks.map((block) => (
          <li key={block.href}>
            <Link
              href={block.href}
              className="block h-full rounded-lg border border-navy-3 bg-navy-2 p-4 transition-colors hover:border-gold"
            >
              <span className="font-display text-lg font-semibold">{block.label}</span>
              <span className="mt-1 block text-table text-ice-70 tabular-nums">
                {block.facts.filter(Boolean).join(" · ") || "ver lista"}
              </span>
            </Link>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-ice-70">
        Contagens do cadastro carregado (B3, CVM, Tesouro Transparente e CoinGecko), sem juízo sobre
        nenhum deles.
      </p>
    </>
  );
}

function Unavailable({ text }: { text: string }) {
  return <p className="text-table text-ice-70">{text} Tente novamente em alguns minutos.</p>;
}
