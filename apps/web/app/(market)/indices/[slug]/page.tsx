import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Section } from "@/components/site/section";
import { IndexCompositionTable } from "@/components/market/index-composition-table";
import { SourceBadge } from "@/components/market/source-badge";
import { Value } from "@/components/market/value";
import { date, decimal, signedPercent } from "@/lib/format";
import { getIndex, getIndexComposition, optional } from "@/lib/market";

type Params = { slug: string };

export const revalidate = 3600;

export async function generateMetadata({
  params,
}: {
  params: Promise<Params>;
}): Promise<Metadata> {
  const { slug } = await params;
  const index = await optional(getIndex(slug));
  if (!index) return {};
  return {
    title: `${index.name} — fechamento e carteira teórica`,
    description: `${index.name} (${index.b3_code}): fechamento, variação e a carteira teórica vigente, com a data da carteira.`,
    alternates: { canonical: `/indices/${index.slug}` },
  };
}

export default async function IndexPage({ params }: { params: Promise<Params> }) {
  const { slug } = await params;
  const index = await optional(getIndex(slug));
  if (!index) notFound();

  const composition = await optional(getIndexComposition(slug));

  return (
    <Section wide className="pt-12 md:pt-16">
      <header className="border-b border-navy-3 pb-8">
        <p className="text-table uppercase tracking-wide text-ice-70">Índice · {index.b3_code}</p>
        <h1 className="mt-2">{index.name}</h1>
        <div className="mt-6 flex flex-wrap items-baseline gap-x-6 gap-y-2">
          <span className="text-h1 font-display tabular-nums">
            <Value reason={index.missing_reasons.value}>{decimal(index.value)}</Value>
          </span>
          <span className="text-h2 tabular-nums text-ice-70">
            <Value reason={index.missing_reasons.change_percent}>
              {signedPercent(index.change_percent)}
            </Value>
          </span>
          {index.date ? (
            <span className="text-table text-ice-70">fechamento de {date(index.date)}</span>
          ) : null}
        </div>
        {index.description ? <p className="mt-4 max-w-2xl text-ice-70">{index.description}</p> : null}
        <SourceBadge source={index.source} className="mt-6" />
      </header>

      <div className="mt-12">
        {composition ? (
          <IndexCompositionTable composition={composition} />
        ) : (
          <p className="text-ice-70">
            A carteira teórica deste índice ainda não foi carregada.
          </p>
        )}
      </div>
    </Section>
  );
}
