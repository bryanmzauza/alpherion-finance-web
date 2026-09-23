import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { ManualTransactionForm } from "@/components/app/manual-transaction-form";
import { Gold } from "@/components/ui/gold";
import { getPortfolio } from "@/lib/portfolio/repo";
import { requireSession } from "@/lib/session";

export const metadata: Metadata = { title: "Lançar movimentação" };

export default async function AdicionarPage() {
  const session = await requireSession("/carteira/adicionar");
  if (!(await getPortfolio(session.user.id))) redirect("/carteira/nova");
  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="max-w-2xl">
      <h1 className="text-3xl md:text-4xl">
        Lançar <Gold>movimentação</Gold>
      </h1>
      <p className="mt-4 text-ice-70">
        Uma compra ou venda por vez. As taxas entram no custo da compra (preço médio pelo método da Receita).
      </p>
      <div className="mt-8">
        <ManualTransactionForm today={today} />
      </div>
    </div>
  );
}
