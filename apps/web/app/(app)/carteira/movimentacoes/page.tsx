import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { buttonVariants } from "@/components/ui/button";
import { Gold } from "@/components/ui/gold";
import { Table, Td, Th, Thead, Tr } from "@/components/ui/table";
import { currency, date } from "@/lib/format";
import { quantity } from "@/lib/portfolio/labels";
import { getPortfolio, listTransactions } from "@/lib/portfolio/repo";
import { requireSession } from "@/lib/session";

export const metadata: Metadata = { title: "Movimentações" };

const SOURCE_LABEL = { manual: "Manual", csv: "CSV", b3_import: "B3", b3_api: "B3" } as const;

type Props = { searchParams: Promise<{ apagada?: string; erro?: string }> };

// /carteira/movimentacoes (plano 5.3): toda compra e venda, a mais recente primeiro,
// com a origem de cada uma. Apagar é um formulário POST por linha (funciona sem JS).
export default async function MovimentacoesPage({ searchParams }: Props) {
  const session = await requireSession("/carteira/movimentacoes");
  const portfolio = await getPortfolio(session.user.id);
  if (!portfolio) redirect("/carteira/nova");
  const { apagada, erro } = await searchParams;
  const rows = await listTransactions(session.user.id, portfolio.id);

  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1 className="text-3xl md:text-4xl">
          <Gold>Movimentações</Gold>
        </h1>
        <Link href="/carteira/adicionar" className={buttonVariants({ variant: "secondary" })}>
          Lançar movimentação
        </Link>
      </div>
      {apagada ? (
        <p role="status" className="mt-6 text-table text-ok">
          Movimentação apagada.
        </p>
      ) : null}
      {erro ? (
        <p role="alert" className="mt-6 text-table text-risk-text">
          Não encontramos essa movimentação.
        </p>
      ) : null}

      {rows.length === 0 ? (
        <p className="mt-8 text-ice-70">Nenhuma movimentação ainda.</p>
      ) : (
        <div className="mt-8">
          <Table caption="Movimentações da carteira">
            <Thead>
              <Tr>
                <Th>Data</Th>
                <Th>Ativo</Th>
                <Th>Tipo</Th>
                <Th className="text-right">Quantidade</Th>
                <Th className="text-right">Preço</Th>
                <Th className="text-right">Taxas</Th>
                <Th className="text-right">Total</Th>
                <Th>Origem</Th>
                <Th>
                  <span className="sr-only">Ações</span>
                </Th>
              </Tr>
            </Thead>
            <tbody className="tabular-nums">
              {rows.map((t) => {
                const total = Number(t.quantity) * Number(t.price) + (t.side === "buy" ? 1 : -1) * Number(t.fees || 0);
                return (
                  <Tr key={t.id}>
                    <Td>{date(t.date)}</Td>
                    <Td>
                      <span className="font-medium text-ice">{t.symbol}</span>
                      <span className="block max-w-56 truncate text-xs text-ice-70">{t.name}</span>
                    </Td>
                    <Td>{t.side === "buy" ? "Compra" : "Venda"}</Td>
                    <Td numeric>{quantity(t.quantity)}</Td>
                    <Td numeric>{currency(t.price)}</Td>
                    <Td numeric>{currency(t.fees)}</Td>
                    <Td numeric>{currency(total)}</Td>
                    <Td className="text-ice-70">{SOURCE_LABEL[t.source]}</Td>
                    <Td>
                      <form action="/api/portfolio/transactions/delete" method="post">
                        <input type="hidden" name="id" value={t.id} />
                        <button
                          type="submit"
                          className="text-table text-ice-70 underline-offset-4 hover:text-risk-text hover:underline"
                          aria-label={`Apagar ${t.side === "buy" ? "compra" : "venda"} de ${t.symbol} em ${date(t.date)}`}
                        >
                          Apagar
                        </button>
                      </form>
                    </Td>
                  </Tr>
                );
              })}
            </tbody>
          </Table>
        </div>
      )}
    </>
  );
}
