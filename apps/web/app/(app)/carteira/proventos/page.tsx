import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Value } from "@/components/market/value";
import { Card } from "@/components/ui/card";
import { Gold } from "@/components/ui/gold";
import { Table, Td, Th, Thead, Tr } from "@/components/ui/table";
import { Tooltip } from "@/components/ui/tooltip";
import { DASH, currency, date, percent } from "@/lib/format";
import { summarizeIncome } from "@/lib/portfolio/income";
import { INCOME_LABEL } from "@/lib/portfolio/labels";
import { getPortfolio, listIncome, positionsFor } from "@/lib/portfolio/repo";
import { requireSession } from "@/lib/session";

export const metadata: Metadata = { title: "Proventos" };

// /carteira/proventos (plano 5.3): o que a carteira recebeu — por ano, por ativo e linha
// a linha. O yield on cost é apresentado como fato sobre o passado, não como expectativa.
export default async function ProventosPage() {
  const session = await requireSession("/carteira/proventos");
  const portfolio = await getPortfolio(session.user.id);
  if (!portfolio) redirect("/carteira/nova");

  const [rows, positions] = await Promise.all([
    listIncome(session.user.id, portfolio.id),
    positionsFor(session.user.id, portfolio.id),
  ]);
  const costs = new Map(positions.map((p) => [p.assetId, p.cost === null ? null : Number(p.cost)]));
  const summary = summarizeIncome(rows, costs, new Date());

  return (
    <>
      <h1 className="text-3xl md:text-4xl">
        <Gold>Proventos</Gold> recebidos
      </h1>
      <p className="mt-4 max-w-2xl text-ice-70">
        Valores líquidos, como caíram na conta. Vêm da importação da B3 (extrato de movimentação ou relatório de
        proventos).
      </p>

      {rows.length === 0 ? (
        <p className="mt-8 text-ice-70">Nenhum provento registrado ainda.</p>
      ) : (
        <>
          <div className="mt-8 grid gap-4 sm:grid-cols-2">
            <Card className="p-5">
              <p className="text-table text-ice-70">Últimos 12 meses</p>
              <p className="mt-2 text-2xl tabular-nums">{currency(summary.total12m)}</p>
            </Card>
            <Card className="p-5">
              <p className="text-table text-ice-70">Desde o primeiro registro</p>
              <p className="mt-2 text-2xl tabular-nums">{currency(summary.total)}</p>
            </Card>
          </div>

          <div className="mt-10 grid gap-8 lg:grid-cols-2">
            <section>
              <h2 className="text-2xl">Por ativo</h2>
              <div className="mt-4">
                <Table caption="Proventos por ativo">
                  <Thead>
                    <Tr>
                      <Th>Ativo</Th>
                      <Th className="text-right">12 meses</Th>
                      <Th className="text-right">Total</Th>
                      <Th className="text-right">
                        <Tooltip content="Proventos líquidos dos últimos 12 meses divididos pelo custo atual da posição (quantidade × preço médio). Descreve o que já foi recebido; não é estimativa do que virá.">
                          Yield on cost
                        </Tooltip>
                      </Th>
                    </Tr>
                  </Thead>
                  <tbody className="tabular-nums">
                    {summary.byAsset.map((a) => (
                      <Tr key={a.assetId}>
                        <Td className="font-medium text-ice">{a.symbol}</Td>
                        <Td numeric>{currency(a.net12m)}</Td>
                        <Td numeric>{currency(a.netTotal)}</Td>
                        <Td numeric>
                          <Value reason="sem custo conhecido da posição atual">
                            {a.yieldOnCost === null ? DASH : percent(a.yieldOnCost)}
                          </Value>
                        </Td>
                      </Tr>
                    ))}
                  </tbody>
                </Table>
              </div>
            </section>
            <section>
              <h2 className="text-2xl">Por ano</h2>
              <div className="mt-4">
                <Table caption="Proventos por ano">
                  <Thead>
                    <Tr>
                      <Th>Ano</Th>
                      <Th className="text-right">Líquido</Th>
                    </Tr>
                  </Thead>
                  <tbody className="tabular-nums">
                    {summary.byYear.map((y) => (
                      <Tr key={y.year}>
                        <Td>{y.year}</Td>
                        <Td numeric>{currency(y.net)}</Td>
                      </Tr>
                    ))}
                  </tbody>
                </Table>
              </div>
            </section>
          </div>

          <section className="mt-10">
            <h2 className="text-2xl">Linha a linha</h2>
            <div className="mt-4">
              <Table caption="Proventos recebidos">
                <Thead>
                  <Tr>
                    <Th>Pagamento</Th>
                    <Th>Ativo</Th>
                    <Th>Tipo</Th>
                    <Th className="text-right">Líquido</Th>
                  </Tr>
                </Thead>
                <tbody className="tabular-nums">
                  {rows.map((r) => (
                    <Tr key={r.id}>
                      <Td>{date(r.date)}</Td>
                      <Td className="font-medium text-ice">{r.symbol}</Td>
                      <Td>{INCOME_LABEL[r.kind]}</Td>
                      <Td numeric>{currency(r.net)}</Td>
                    </Tr>
                  ))}
                </tbody>
              </Table>
            </div>
          </section>
        </>
      )}
    </>
  );
}
