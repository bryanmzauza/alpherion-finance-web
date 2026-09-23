import type { Metadata } from "next";
import { Section } from "@/components/site/section";
import { SectorTree } from "@/components/market/sector-tree";
import { JsonLd } from "@/components/site/json-ld";
import { Gold } from "@/components/ui/gold";
import { getSectors, optional } from "@/lib/market";
import { breadcrumbJsonLd } from "@/lib/seo";

// `/setores` — a árvore de setores (site.md §2.1, plano 4.4). ISR: muda quando a B3
// reclassifica uma empresa, o que é raro; a revalidação diária cobre.
export const revalidate = 3600;

export const metadata: Metadata = {
  title: "Setores da B3 — empresas e fundos por segmento",
  description:
    "Setores, subsetores e segmentos da classificação da B3 e os segmentos de fundos imobiliários, com quantos papéis há em cada um.",
  alternates: { canonical: "/setores" },
};

export default async function SectorsPage() {
  const sectors = await optional(getSectors());

  return (
    <>
      <JsonLd
        data={breadcrumbJsonLd([
          { name: "Início", path: "/" },
          { name: "Setores", path: "/setores" },
        ])}
      />
      <Section wide className="pt-16 md:pt-20">
        <h1>
          <Gold>Setores</Gold> da B3
        </h1>
        <p className="mt-4 max-w-2xl text-ice-70">
          Cada empresa listada pertence a um segmento da classificação da B3; cada fundo imobiliário, a um
          segmento de FII. Abra um segmento para ver os papéis com cotação e indicadores.
        </p>
        <div className="mt-12">
          {sectors ? (
            <SectorTree nodes={sectors} />
          ) : (
            <p className="text-ice-70">A árvore de setores está temporariamente indisponível.</p>
          )}
        </div>
        <p className="mt-12 text-table text-ice-70">Classificação setorial: Fonte: B3.</p>
      </Section>
    </>
  );
}
