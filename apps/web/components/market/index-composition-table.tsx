import type { IndexComposition } from "@/lib/market";
import { compactCurrency, date, percent } from "@/lib/format";
import { Table, Td, Th, Thead, Tr } from "@/components/ui/table";
import { SourceBadge } from "@/components/market/source-badge";
import { Value } from "@/components/market/value";

// Carteira teórica de um índice.
//
// **A data vem no título, não numa nota de rodapé.** A B3 rebalanceia a cada
// quadrimestre e publica prévias; sem a data, o leitor acha que está vendo a composição
// de hoje quando pode estar vendo a de quatro meses atrás. É por isso que a API devolve
// `reference_date` como parte do dado, e não como metadado opcional.
export function IndexCompositionTable({ composition }: { composition: IndexComposition }) {
  return (
    <section aria-labelledby="composicao">
      <h2 id="composicao">Carteira teórica de {date(composition.reference_date)}</h2>
      <p className="mt-2 text-table text-ice-70">
        {composition.members.length} papéis, por participação no índice.
      </p>
      <Table caption="Carteira teórica do índice, por participação" className="mt-6">
        <Thead>
          <Tr>
            <Th>Papel</Th>
            <Th>Empresa</Th>
            <Th className="text-right">Participação</Th>
            <Th className="text-right">Quantidade teórica</Th>
          </Tr>
        </Thead>
        <tbody>
          {composition.members.map((member) => (
            <Tr key={member.ticker}>
              <Td className="tabular-nums">{member.ticker}</Td>
              <Td>{member.company_name ?? "—"}</Td>
              <Td numeric className="tabular-nums">
                <Value>{percent(member.weight)}</Value>
              </Td>
              <Td numeric className="tabular-nums">
                <Value>{compactCurrency(member.theoretical_qty)}</Value>
              </Td>
            </Tr>
          ))}
        </tbody>
      </Table>
      <SourceBadge source={composition.source} className="mt-4" />
    </section>
  );
}
