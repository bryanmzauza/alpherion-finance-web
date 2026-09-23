import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Section } from "@/components/site/section";
import { AgendaMonth } from "@/components/agenda/agenda-month";
import { monthOf, monthPath, monthSlug, parseMonthSlug, todayIso } from "@/lib/agenda";

type Params = { mes: string };

// `/agenda/mes/2026-10` — a vista mensal (plano 4.3). O mês não é indexado: os itens
// estão nas semanas, e duas URLs com o mesmo conteúdo dividiriam o sinal de busca.
export const revalidate = 3600;

export function generateStaticParams(): Params[] {
  return [{ mes: monthSlug(monthOf(todayIso())) }];
}

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const month = parseMonthSlug((await params).mes);
  if (!month) return {};
  return {
    title: `Agenda do mês ${monthSlug(month).split("-").reverse().join("/")}`,
    alternates: { canonical: monthPath(month) },
    robots: { index: false, follow: true },
  };
}

export default async function AgendaMonthPage({ params }: { params: Promise<Params> }) {
  const month = parseMonthSlug((await params).mes);
  if (!month) notFound();
  return (
    <Section wide className="pt-16 md:pt-20">
      <AgendaMonth month={month} />
    </Section>
  );
}
