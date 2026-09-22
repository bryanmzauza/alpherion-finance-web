import type { SecuritySummary } from "@/lib/market";
import { compactCurrency, currency } from "@/lib/format";
import { Table, Td, Th, Thead, Tr } from "@/components/ui/table";
import { TickerLink } from "@/components/market/ticker-link";
import { Value } from "@/components/market/value";

// Lista de papéis de uma classe. A ordem vem da API e o **título da página diz qual é**
// (§4.5): "por volume financeiro do dia", não "os melhores".
export function SecurityTable({ securities }: { securities: SecuritySummary[] }) {
  if (securities.length === 0) {
    return <p className="text-ice-70">Nenhum papel carregado nesta classe.</p>;
  }

  return (
    <Table caption="Papéis listados, por volume financeiro do dia">
      <Thead>
        <Tr>
          <Th>Papel</Th>
          <Th>Empresa</Th>
          <Th className="text-right">Cotação</Th>
          <Th className="text-right">Volume do dia</Th>
        </Tr>
      </Thead>
      <tbody>
        {securities.map((item) => (
          <Tr key={item.ticker}>
            <Td>
              <TickerLink type={item.type} ticker={item.ticker} />
            </Td>
            <Td>{item.trade_name ?? item.company_name}</Td>
            <Td numeric className="tabular-nums">
              <Value>{currency(item.price)}</Value>
            </Td>
            <Td numeric className="tabular-nums">
              <Value>{compactCurrency(item.volume)}</Value>
            </Td>
          </Tr>
        ))}
      </tbody>
    </Table>
  );
}
