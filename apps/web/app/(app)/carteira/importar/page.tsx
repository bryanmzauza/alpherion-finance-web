import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { ImportFlow } from "@/components/app/import-flow";
import { Gold } from "@/components/ui/gold";
import { getPortfolio } from "@/lib/portfolio/repo";
import { requireSession } from "@/lib/session";

export const metadata: Metadata = { title: "Importar planilha" };

// /carteira/importar (plano 5.3): CSV genérico no formato de `public/csv-modelo.csv`.
export default async function ImportarCsvPage() {
  const session = await requireSession("/carteira/importar");
  if (!(await getPortfolio(session.user.id))) redirect("/carteira/nova");

  return (
    <div className="max-w-4xl">
      <h1 className="text-3xl md:text-4xl">
        Importar <Gold>planilha</Gold>
      </h1>
      <p className="mt-4 text-ice-70">
        Um CSV com uma movimentação por linha. Baixe o{" "}
        <a href="/csv-modelo.csv" download className="text-gold underline underline-offset-4">
          modelo
        </a>
        , preencha e envie. Veio da B3? Use a{" "}
        <Link href="/carteira/importar/b3" className="text-gold underline underline-offset-4">
          importação da B3
        </Link>
        .
      </p>

      <section className="mt-8">
        <h2 className="text-2xl">Colunas</h2>
        <dl className="mt-4 grid gap-x-6 gap-y-2 text-table sm:grid-cols-[10rem_1fr]">
          <dt className="text-ice">data</dt>
          <dd className="text-ice-70">dd/mm/aaaa ou aaaa-mm-dd</dd>
          <dt className="text-ice">tipo</dt>
          <dd className="text-ice-70">compra ou venda</dd>
          <dt className="text-ice">ativo</dt>
          <dd className="text-ice-70">ticker (PETR4), nome do título (Tesouro IPCA+ 2035) ou símbolo da cripto (BTC)</dd>
          <dt className="text-ice">quantidade</dt>
          <dd className="text-ice-70">com vírgula ou ponto decimal</dd>
          <dt className="text-ice">preco</dt>
          <dd className="text-ice-70">preço unitário em reais</dd>
          <dt className="text-ice">taxas</dt>
          <dd className="text-ice-70">opcional; corretagem e emolumentos da operação</dd>
          <dt className="text-ice">classe</dt>
          <dd className="text-ice-70">opcional: acao, fii, etf, bdr, tesouro ou cripto</dd>
        </dl>
        <p className="mt-4 text-table text-ice-70">Até 1.000 linhas e 2 MB. O arquivo é lido em memória e descartado.</p>
      </section>

      <section className="mt-10">
        <h2 className="text-2xl">Enviar</h2>
        <div className="mt-4">
          <ImportFlow kind="csv" maxFiles={1} maxBytes={2 * 1024 * 1024} accept=".csv,text/csv" />
        </div>
      </section>
    </div>
  );
}
