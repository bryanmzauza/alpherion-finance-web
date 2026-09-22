import type { Metadata } from "next";
import { Section } from "@/components/site/section";
import { CryptoTable } from "@/components/market/crypto-table";
import { Gold } from "@/components/ui/gold";
import { getCrypto, optional } from "@/lib/market";

export const metadata: Metadata = {
  title: "Criptoativos — cotação em reais",
  description:
    "Criptoativos por valor de mercado, com cotação em reais, variação de 24 horas e volume. Cada número com fonte e data.",
  alternates: { canonical: "/cripto" },
};

export const revalidate = 300;

export default async function CryptoPage() {
  const assets = (await optional(getCrypto())) ?? [];

  return (
    <Section wide className="pt-16 md:pt-20">
      <h1>
        Cripto em <Gold>reais</Gold>
      </h1>
      <p className="mt-4 max-w-2xl text-ice-70">
        Ordenados por valor de mercado. Criptoativos são de alto risco e esta página não indica
        nenhum deles — é fato com fonte, como o resto do site.
      </p>
      <div className="mt-10">
        <CryptoTable assets={assets} />
      </div>
    </Section>
  );
}
