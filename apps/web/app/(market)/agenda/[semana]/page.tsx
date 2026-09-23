import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Section } from "@/components/site/section";
import { AgendaWeek, currentWeek } from "@/components/agenda/agenda-week";
import {
  INDEX_WINDOW_DAYS,
  addDays,
  parseWeekSlug,
  shiftWeek,
  todayIso,
  weekDays,
  weekPath,
  weekSlug,
} from "@/lib/agenda";

type Params = { semana: string };

// `/agenda/2026-39` — uma semana da agenda (plano 4.3). ISR sob demanda: a semana
// atual e a próxima saem no build; as outras, na primeira visita.
export const revalidate = 1800;

export function generateStaticParams(): Params[] {
  const week = currentWeek();
  return [week, shiftWeek(week, 1)].map((w) => ({ semana: weekSlug(w) }));
}

const br = (iso: string) => iso.split("-").reverse().join("/");

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const week = parseWeekSlug((await params).semana);
  if (!week) return {};
  const days = weekDays(week);
  // Semana de mais de 12 meses atrás sai do índice: agenda velha não é notícia, e
  // centenas de semanas passadas competiriam com a semana corrente na busca.
  const old = days[6] < addDays(todayIso(), -INDEX_WINDOW_DAYS);
  return {
    title: `Agenda da semana ${week.week} de ${week.year} — proventos, fatos relevantes e macro`,
    description: `Proventos, fatos relevantes e agenda macro de ${br(days[0])} a ${br(days[6])}, com a fonte de cada item.`,
    alternates: { canonical: weekPath(week) },
    ...(old ? { robots: { index: false, follow: true } } : {}),
  };
}

export default async function AgendaWeekPage({ params }: { params: Promise<Params> }) {
  const week = parseWeekSlug((await params).semana);
  if (!week) notFound();
  return (
    <Section wide className="pt-16 md:pt-20">
      <AgendaWeek week={week} />
    </Section>
  );
}
