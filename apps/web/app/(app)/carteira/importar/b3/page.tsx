import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { ImportFlow } from "@/components/app/import-flow";
import { Card } from "@/components/ui/card";
import { Gold } from "@/components/ui/gold";
import { getPortfolio } from "@/lib/portfolio/repo";
import { requireSession } from "@/lib/session";

export const metadata: Metadata = { title: "Importar da B3" };

// /carteira/importar/b3 (plano 5.3). O aviso sobre CPF e nome vem **antes** do envio:
// a pessoa precisa saber o que acontece com o arquivo antes de mandá-lo, não depois.
export default async function ImportarB3Page() {
  const session = await requireSession("/carteira/importar/b3");
  if (!(await getPortfolio(session.user.id))) redirect("/carteira/nova");

  return (
    <div className="max-w-4xl">
      <h1 className="text-3xl md:text-4xl">
        Importar da <Gold>B3</Gold>
      </h1>
      <p className="mt-4 text-ice-70">
        Os arquivos vêm da Área do Investidor da B3 (investidor.b3.com.br), que reúne o que está em todas as suas
        corretoras. Você pode mandar um, dois ou os três, em qualquer ordem.
      </p>

      <Card className="mt-8 border-gold/40">
        <h2 className="font-display text-xl font-semibold">O que acontece com o arquivo</h2>
        <ul className="mt-4 list-disc space-y-2 pl-6 text-table text-ice-70">
          <li>
            Ele é lido em memória e descartado em seguida. Não guardamos o arquivo, só uma impressão digital (hash) para
            avisar se você mandar o mesmo de novo.
          </li>
          <li>
            <strong className="text-ice">CPF, nome, conta e corretora são ignorados</strong>: a leitura pega só as colunas
            de ativo, data, quantidade e valores. Esses dados não chegam ao banco nem a nenhum registro.
          </li>
          <li>Quantidades e valores são gravados cifrados.</li>
        </ul>
      </Card>

      <section className="mt-10">
        <h2 className="text-2xl">Passo a passo</h2>
        <ol className="mt-4 list-decimal space-y-3 pl-6 text-ice-70">
          <li>
            Entre em <span className="text-ice">investidor.b3.com.br</span> com seu CPF e senha da B3.
          </li>
          <li>
            <span className="text-ice">Posição</span>: no menu, &ldquo;Posição&rdquo; → ícone de download → Excel. Traz a
            quantidade atual de cada ativo (ações, FIIs, ETFs, BDRs, Tesouro Direto e renda fixa).
          </li>
          <li>
            <span className="text-ice">Negociação</span>: &ldquo;Extratos&rdquo; → &ldquo;Negociação&rdquo; → escolha o
            período (desde a primeira compra, se quiser o preço médio completo) → Excel.
          </li>
          <li>
            <span className="text-ice">Proventos</span>: &ldquo;Extratos&rdquo; → &ldquo;Movimentação&rdquo; → mesmo período
            → Excel. Dividendos, JCP e rendimentos pagos entram; o resto do extrato é ignorado.
          </li>
          <li>Envie os arquivos abaixo, confira a prévia e confirme.</li>
        </ol>
        <p className="mt-4 text-table text-ice-70">
          O extrato de negociação não traz corretagem nem emolumentos: as compras entram sem taxa. Para o custo exato,
          lance a taxa em <Link href="/carteira/adicionar" className="text-gold underline underline-offset-4">lançamento manual</Link>.
        </p>
      </section>

      <section className="mt-10">
        <h2 className="text-2xl">Enviar</h2>
        <div className="mt-4">
          <ImportFlow kind="b3" maxFiles={3} maxBytes={5 * 1024 * 1024} accept=".xlsx,.csv" />
        </div>
      </section>
    </div>
  );
}
