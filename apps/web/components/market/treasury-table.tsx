import type { TreasuryBond } from "@/lib/market";
import { currency, date, decimal } from "@/lib/format";
import { Table, Td, Th, Thead, Tr } from "@/components/ui/table";
import { SourceBadge } from "@/components/market/source-badge";
import { Value } from "@/components/market/value";

// Títulos do Tesouro Direto, agrupados por indexador.
//
// Fonte ODbL (Tesouro Transparente): é a única tabela de preço do site que não depende
// da licença da B3 (ADR-017). A taxa de compra é a que interessa a quem vai comprar; a
// de venda aparece ao lado porque a diferença entre as duas é informação — e nenhuma
// das duas vem acompanhada de "é uma boa hora".
const INDEX_LABELS: Record<string, string> = {
  selic: "Tesouro Selic",
  ipca: "Tesouro IPCA+",
  prefixado: "Tesouro Prefixado",
  renda_mais: "Tesouro Renda+",
  educa_mais: "Tesouro Educa+",
};

export function TreasuryTable({ bonds }: { bonds: TreasuryBond[] }) {
  if (bonds.length === 0) {
    return <p className="text-ice-70">Nenhum título carregado.</p>;
  }

  const groups = new Map<string, TreasuryBond[]>();
  for (const bond of bonds) {
    const list = groups.get(bond.index_type) ?? [];
    list.push(bond);
    groups.set(bond.index_type, list);
  }

  return (
    <div className="space-y-10">
      {[...groups.entries()].map(([indexType, list]) => (
        <section key={indexType}>
          <h2>{INDEX_LABELS[indexType] ?? indexType}</h2>
          <Table caption={`Títulos ${INDEX_LABELS[indexType] ?? indexType}`} className="mt-4">
            <Thead>
              <Tr>
                <Th>Título</Th>
                <Th>Vencimento</Th>
                <Th className="text-right">Taxa de compra</Th>
                <Th className="text-right">Preço unitário</Th>
              </Tr>
            </Thead>
            <tbody>
              {list.map((bond) => (
                <Tr key={bond.slug}>
                  <Td>
                    {bond.name}
                    {bond.coupon ? (
                      <span className="ml-2 text-table text-ice-70">juros semestrais</span>
                    ) : null}
                  </Td>
                  <Td className="tabular-nums">{date(bond.maturity)}</Td>
                  <Td numeric className="tabular-nums">
                    <Value reason={bond.missing_reasons.buy_rate}>
                      {bond.buy_rate ? `${decimal(bond.buy_rate)}%` : "—"}
                    </Value>
                  </Td>
                  <Td numeric className="tabular-nums">
                    <Value reason={bond.missing_reasons.buy_rate}>{currency(bond.buy_price)}</Value>
                  </Td>
                </Tr>
              ))}
            </tbody>
          </Table>
          {list[0] ? <SourceBadge source={list[0].source} className="mt-3" /> : null}
        </section>
      ))}
    </div>
  );
}
