import type { Metadata } from "next";
import Link from "next/link";
import { Section } from "@/components/site/section";
import { Gold } from "@/components/ui/gold";
import { getIndices, optional } from "@/lib/market";

export const metadata: Metadata = {
  title: "Índices da B3 — Ibovespa, IFIX, IDIV e outros",
  description:
    "Índices da B3 com fechamento e carteira teórica datada: Ibovespa, IFIX, IDIV, SMLL, IBrX 100 e outros.",
  alternates: { canonical: "/indices" },
};

export const revalidate = 3600;

export default async function IndicesPage() {
  const indices = (await optional(getIndices())) ?? [];

  return (
    <Section wide className="pt-16 md:pt-20">
      <h1>
        Índices da <Gold>B3</Gold>
      </h1>
      <p className="mt-4 max-w-2xl text-ice-70">
        Fechamento e carteira teórica de cada índice, sempre com a data da carteira à vista.
      </p>

      <ul className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {indices.map((index) => (
          <li key={index.slug}>
            <Link
              href={`/indices/${index.slug}`}
              className="block rounded-lg border border-navy-3 bg-navy-2 p-5 hover:border-gold"
            >
              <span className="text-h2 font-display">{index.name}</span>
              <span className="mt-1 block text-table text-ice-70">{index.b3_code}</span>
            </Link>
          </li>
        ))}
      </ul>
      {indices.length === 0 ? (
        <p className="mt-8 text-ice-70">Os índices estão temporariamente indisponíveis.</p>
      ) : null}
    </Section>
  );
}
