import type { Metadata } from "next";
import { Section } from "@/components/site/section";
import { AgendaWeek, currentWeek } from "@/components/agenda/agenda-week";

// `/agenda` — a semana corrente (site.md §2.1, plano 4.3). ISR: o `revalidate_pages`
// renova depois da carga do dia; o tempo abaixo é só a rede de segurança (e o que vira
// a semana na segunda-feira).
export const revalidate = 1800;

export const metadata: Metadata = {
  title: "Agenda do mercado — proventos, fatos relevantes e macro da semana",
  description:
    "Datas-com e pagamentos de proventos, fatos relevantes entregues à CVM e a agenda macro (Copom, IPCA, IGP-M, FOMC, vencimentos) da semana, com a fonte de cada item.",
  alternates: { canonical: "/agenda" },
};

export default function AgendaPage() {
  return (
    <Section wide className="pt-16 md:pt-20">
      <AgendaWeek week={currentWeek()} />
    </Section>
  );
}
