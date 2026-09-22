import Link from "next/link";
import type { SecuritySummary } from "@/lib/market";
import { compactCurrency, currency } from "@/lib/format";
import { Table, Td, Th, Thead, Tr } from "@/components/ui/table";
import { TickerLink } from "@/components/market/ticker-link";
import { Value } from "@/components/market/value";

type Props = {
  securities: SecuritySummary[];
  sectorSlug: string | null;
  sectorName: string | null;
  currentTicker: string;
};

// "Mesmo setor" (§2.1): papéis do mesmo segmento B3, com cotação e liquidez.
//
// A ordem é por **liquidez**, e o cabeçalho diz isso. Uma lista de pares ordenada por
// P/L ou por variação seria um ranking com recomendação implícita; ordenada por volume,
// é um fato sobre o que o mercado negocia.
export function SameSectorList({ securities, sectorSlug, sectorName, currentTicker }: Props) {
  const others = securities.filter((s) => s.ticker !== currentTicker).slice(0, 8);
  if (others.length === 0) return null;

  return (
    <section aria-labelledby="mesmo-setor">
      <h2 id="mesmo-setor">Mesmo setor</h2>
      <p className="mt-2 text-table text-ice-70">
        Papéis de {sectorName ?? "mesmo segmento"}, por volume financeiro do dia.
      </p>
      <Table caption="Papéis do mesmo setor, por volume" className="mt-4">
        <Thead>
          <Tr>
            <Th>Papel</Th>
            <Th>Empresa</Th>
            <Th className="text-right">Cotação</Th>
            <Th className="text-right">Volume</Th>
          </Tr>
        </Thead>
        <tbody>
          {others.map((item) => (
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
      {sectorSlug ? (
        <Link
          href={`/setores/${sectorSlug}`}
          className="mt-4 inline-block text-gold underline decoration-gold/40 underline-offset-4 hover:decoration-gold"
        >
          Ver o setor inteiro →
        </Link>
      ) : null}
    </section>
  );
}
