import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Section } from "@/components/site/section";
import { SecurityTable } from "@/components/market/security-table";
import { Gold } from "@/components/ui/gold";
import { MARKET_CLASSES, classBySlug } from "@/lib/market-classes";
import { listSecurities, optional } from "@/lib/market";

type Params = { classe: string };

// Uma página para as quatro classes: `/acoes`, `/fiis`, `/etfs`, `/bdrs`. O que muda é
// o filtro e o texto, que vivem em `lib/market-classes.ts`.
export function generateStaticParams(): Params[] {
  return MARKET_CLASSES.map((c) => ({ classe: c.slug }));
}

// Só as quatro classes conhecidas; qualquer outro caminho é 404 (nada de página vazia).
export const dynamicParams = false;

export async function generateMetadata({
  params,
}: {
  params: Promise<Params>;
}): Promise<Metadata> {
  const { classe } = await params;
  const meta = classBySlug(classe);
  if (!meta) return {};
  return {
    title: meta.title,
    description: meta.description,
    alternates: { canonical: `/${meta.slug}` },
  };
}

export default async function ClassPage({ params }: { params: Promise<Params> }) {
  const { classe } = await params;
  const meta = classBySlug(classe);
  if (!meta) notFound();

  const page = await optional(listSecurities({ type: meta.type, page_size: 100 }));

  return (
    <Section wide className="pt-16 md:pt-20">
      <h1>
        <Gold>{meta.label}</Gold> na B3
      </h1>
      <p className="mt-4 max-w-2xl text-ice-70">{meta.intro}</p>

      <div className="mt-8">
        {page ? (
          <>
            <p className="mb-4 text-table text-ice-70">
              {page.total} {page.total === 1 ? "papel listado" : "papéis listados"} · ordenados por
              volume financeiro do dia
            </p>
            <SecurityTable securities={page.items} />
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
