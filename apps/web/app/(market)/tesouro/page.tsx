import type { Metadata } from "next";
import { Section } from "@/components/site/section";
import { TreasuryTable } from "@/components/market/treasury-table";
import { Gold } from "@/components/ui/gold";
import { getTreasury, optional } from "@/lib/market";

export const metadata: Metadata = {
  title: "Tesouro Direto — taxas e preços de hoje",
  description:
    "Títulos do Tesouro Direto com taxa e preço unitário do dia, direto do Tesouro Transparente. Cada número com fonte e data.",
  alternates: { canonical: "/tesouro" },
};

export const revalidate = 3600;

export default async function TreasuryPage() {
  const bonds = (await optional(getTreasury())) ?? [];

  return (
    <Section wide className="pt-16 md:pt-20">
      <h1>
        Tesouro <Gold>Direto</Gold>
      </h1>
      <p className="mt-4 max-w-2xl text-ice-70">
        Taxa e preço unitário de cada título, como o Tesouro Transparente publica. Nenhuma
        indicação de compra ou venda: os números estão aqui para serem conferidos na fonte.
      </p>
      <div className="mt-10">
        <TreasuryTable bonds={bonds} />
      </div>
    </Section>
  );
}
