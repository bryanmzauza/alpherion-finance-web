import type { Metadata } from "next";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Gold } from "@/components/ui/gold";
import { Input } from "@/components/ui/input";
import { getPortfolio } from "@/lib/portfolio/repo";
import { requireSession } from "@/lib/session";

export const metadata: Metadata = { title: "Nova carteira" };

type Props = { searchParams: Promise<{ passo?: string; erro?: string }> };

// /carteira/nova (plano 5.3), em dois passos: dar nome à carteira e escolher como os
// ativos entram. Uma carteira por pessoa no v1 — quem já tem cai direto no passo 2.
export default async function NovaCarteiraPage({ searchParams }: Props) {
  const session = await requireSession("/carteira/nova");
  const { erro } = await searchParams;
  const portfolio = await getPortfolio(session.user.id);

  if (!portfolio) {
    return (
      <div className="max-w-xl">
        <p className="text-table text-ice-70">Passo 1 de 2</p>
        <h1 className="mt-2 text-3xl md:text-4xl">
          Sua <Gold>carteira</Gold>
        </h1>
        <p className="mt-4 text-ice-70">
          Dê um nome para a carteira. Ele só aparece para você e pode ser qualquer coisa: &ldquo;Aposentadoria&rdquo;,
          &ldquo;Principal&rdquo;, o seu nome.
        </p>
        {erro ? (
          <p role="alert" className="mt-6 text-table text-risk-text">
            O nome precisa ter de 1 a 60 caracteres.
          </p>
        ) : null}
        <form action="/api/portfolio" method="post" className="mt-8 space-y-5">
          <div>
            <label htmlFor="nome" className="mb-2 block text-table text-ice-70">
              Nome da carteira
            </label>
            <Input id="nome" name="nome" required maxLength={60} defaultValue="Principal" />
          </div>
          <Button type="submit">Continuar</Button>
        </form>
      </div>
    );
  }

  const options = [
    {
      href: "/carteira/importar/b3",
      title: "Importar da B3",
      text: "Os arquivos da Área do Investidor: posição, negociações e proventos. O caminho mais completo.",
    },
    {
      href: "/carteira/importar",
      title: "Importar planilha (CSV)",
      text: "Uma planilha sua, no formato do modelo: data, tipo, ativo, quantidade e preço.",
    },
    {
      href: "/carteira/adicionar",
      title: "Lançar à mão",
      text: "Uma compra ou venda de cada vez. Bom para poucos ativos ou para completar a importação.",
    },
  ];

  return (
    <div>
      <p className="text-table text-ice-70">Passo 2 de 2</p>
      <h1 className="mt-2 text-3xl md:text-4xl">
        Como os ativos <Gold>entram</Gold>
      </h1>
      <p className="mt-4 max-w-2xl text-ice-70">
        Dá para combinar os três. Reenviar o mesmo arquivo não duplica nada.
      </p>
      <div className="mt-8 grid gap-4 md:grid-cols-3">
        {options.map((option) => (
          <Link key={option.href} href={option.href} className="group">
            <Card className="h-full transition-colors group-hover:border-gold">
              <h2 className="font-display text-xl font-semibold">{option.title}</h2>
              <p className="mt-3 text-table text-ice-70">{option.text}</p>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
