import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { Value } from "@/components/market/value";
import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Gold } from "@/components/ui/gold";
import { Table, Td, Th, Thead, Tr } from "@/components/ui/table";
import { cn } from "@/lib/cn";
import { DASH, currency, date, direction, percent, signedPercent } from "@/lib/format";
import { CLASS_LABEL, quantity } from "@/lib/portfolio/labels";
import { getPortfolio, positionsFor } from "@/lib/portfolio/repo";
import { MAX_VALUED, valuePositions, type ValuedPosition } from "@/lib/portfolio/valuation";
import { requireSession } from "@/lib/session";

export const metadata: Metadata = { title: "Carteira" };

const TREND = { up: "text-ok", down: "text-risk-text", flat: "text-ice-70" } as const;

// /carteira (plano 5.3): posição de cada ativo — quantidade, preço médio (método da
// Receita), preço atual, valor, resultado e peso. Tudo **fato**: nenhuma coluna diz o
// que fazer com o ativo. Preço sempre com a fonte e a data; sem preço, "—" com o motivo.
export default async function CarteiraPage() {
  const session = await requireSession("/carteira");
  const portfolio = await getPortfolio(session.user.id);
  if (!portfolio) redirect("/carteira/nova");

  // Ordem alfabética: neutra, sem sugerir que um ativo "vem antes" de outro por mérito.
  const label = (p: { marketRef: string; symbol: string; name: string }) => (p.marketRef === "ticker" ? p.symbol : p.name);
  const positions = (await positionsFor(session.user.id, portfolio.id)).sort((a, b) =>
    label(a).localeCompare(label(b), "pt-BR"),
  );
  if (positions.length === 0) return <Empty name={portfolio.name} />;

  const { valuation, error, truncated } = await valuePositions(positions);
  const valued = new Map<string, ValuedPosition>(
    (valuation?.positions ?? []).map((v) => [`${v.market_ref}:${v.symbol}`, v]),
  );
  const warnings = positions.flatMap((p) => p.warnings.map((w) => `${p.symbol}: ${w}`));

  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-table text-ice-70">{portfolio.name}</p>
          <h1 className="mt-1 text-3xl md:text-4xl">
            Sua <Gold>carteira</Gold>
          </h1>
        </div>
        <div className="flex gap-3">
          <Link href="/carteira/adicionar" className={buttonVariants({ variant: "secondary" })}>
            Lançar movimentação
          </Link>
          <Link href="/carteira/importar/b3" className={buttonVariants({ variant: "secondary" })}>
            Importar
          </Link>
        </div>
      </div>

      <div className="mt-8 grid gap-4 sm:grid-cols-3">
        <Summary label="Valor atual" value={valuation ? currency(valuation.total_value) : DASH} reason={error ?? undefined} />
        <Summary label="Custo (preço médio)" value={currency(valuation?.total_cost)} reason="sem custo conhecido nas posições com valor" />
        <Summary
          label="Resultado"
          value={currency(valuation?.total_result)}
          reason="sem custo conhecido nas posições com valor"
          tone={direction(valuation?.total_result)}
        />
      </div>
      {valuation?.partial ? (
        <p className="mt-3 text-table text-ice-70">
          Os totais somam só as posições com preço e custo conhecidos; as demais aparecem com &ldquo;—&rdquo; e o motivo.
        </p>
      ) : null}
      {truncated ? (
        <p className="mt-3 text-table text-warn">
          A carteira tem mais de {MAX_VALUED} posições; os valores consideram as primeiras {MAX_VALUED}.
        </p>
      ) : null}

      <div className="mt-8">
        <Table caption="Posições da carteira">
          <Thead>
            <Tr>
              <Th>Ativo</Th>
              <Th className="text-right">Quantidade</Th>
              <Th className="text-right">Preço médio</Th>
              <Th className="text-right">Preço atual</Th>
              <Th className="text-right">Valor</Th>
              <Th className="text-right">Resultado</Th>
              <Th className="text-right">Peso</Th>
            </Tr>
          </Thead>
          <tbody className="tabular-nums">
            {positions.map((p) => {
              const v = valued.get(`${p.marketRef}:${p.symbol}`);
              const reasons = v?.missing_reasons ?? {};
              const priceReason = reasons.price ?? error ?? undefined;
              return (
                <Tr key={p.assetId}>
                  <Td>
                    <span className="font-medium text-ice">{label(p)}</span>
                    <span className="ml-2 text-xs text-ice-70">{CLASS_LABEL[p.assetClass]}</span>
                    {p.marketRef === "ticker" ? <span className="block truncate text-xs text-ice-70">{p.name}</span> : null}
                  </Td>
                  <Td numeric>{p.quantity === null ? <Value reason="posição informada por valor">{DASH}</Value> : quantity(p.quantity)}</Td>
                  <Td numeric>
                    <Value reason={reasons.cost ?? "sem histórico de compras para calcular"}>{currency(p.avgPrice)}</Value>
                  </Td>
                  <Td numeric>
                    <Value reason={priceReason}>{currency(v?.price)}</Value>
                    {v?.price && v.source ? (
                      <span className="block text-xs text-ice-70">
                        {v.source} · {date(v.price_date)}
                      </span>
                    ) : null}
                  </Td>
                  <Td numeric>
                    <Value reason={reasons.value ?? priceReason}>{currency(v?.value)}</Value>
                  </Td>
                  <Td numeric className={TREND[direction(v?.result)]}>
                    <Value reason={v?.value ? "sem preço médio" : priceReason}>{currency(v?.result)}</Value>
                    {v?.result_percent ? <span className="block text-xs">{signedPercent(v.result_percent)}</span> : null}
                  </Td>
                  <Td numeric>
                    <Value reason={priceReason}>{percent(v?.weight)}</Value>
                  </Td>
                </Tr>
              );
            })}
          </tbody>
        </Table>
      </div>

      {warnings.length > 0 ? (
        <Card className="mt-8">
          <h2 className="font-display text-xl font-semibold">Avisos do histórico</h2>
          <ul className="mt-4 list-disc space-y-1 pl-6 text-table text-ice-70">
            {warnings.slice(0, 20).map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </Card>
      ) : null}

      <p className="mt-8 max-w-3xl text-table text-ice-70">
        Preço médio pelo método da Receita Federal: compras entram com as taxas; vendas baixam a quantidade sem mudar o
        preço médio. Quando a posição vem do arquivo da B3, a quantidade é a do arquivo.
      </p>
    </>
  );
}

function Summary({
  label,
  value,
  reason,
  tone = "flat",
}: {
  label: string;
  value: string;
  reason?: string;
  tone?: "up" | "down" | "flat";
}) {
  return (
    <Card className="p-5">
      <p className="text-table text-ice-70">{label}</p>
      <p className={cn("mt-2 text-2xl tabular-nums", tone !== "flat" && TREND[tone])}>
        <Value reason={reason}>{value}</Value>
      </p>
    </Card>
  );
}

function Empty({ name }: { name: string }) {
  return (
    <div className="max-w-2xl">
      <p className="text-table text-ice-70">{name}</p>
      <h1 className="mt-1 text-3xl md:text-4xl">
        Carteira <Gold>vazia</Gold>
      </h1>
      <p className="mt-4 text-ice-70">
        Importe os arquivos da Área do Investidor da B3, uma planilha CSV ou lance as movimentações à mão.
      </p>
      <div className="mt-8 flex flex-wrap gap-3">
        <Link href="/carteira/importar/b3" className={buttonVariants()}>
          Importar da B3
        </Link>
        <Link href="/carteira/importar" className={buttonVariants({ variant: "secondary" })}>
          Importar CSV
        </Link>
        <Link href="/carteira/adicionar" className={buttonVariants({ variant: "secondary" })}>
          Lançar à mão
        </Link>
      </div>
    </div>
  );
}
