import type { CorporateEvent } from "@/lib/market";
import { currency, date } from "@/lib/format";
import { Table, Td, Th, Thead, Tr } from "@/components/ui/table";
import { Value } from "@/components/market/value";

// Proventos e eventos societários **anunciados pelo emissor**. Não é o que o usuário
// recebeu (isso vive na carteira, no app) e não é projeção: cada linha é um anúncio com
// data e fonte.
const KIND_LABELS: Record<string, string> = {
  dividend: "Dividendo",
  jcp: "Juros sobre capital próprio",
  fii_income: "Rendimento",
  split: "Desdobramento",
  reverse_split: "Grupamento",
  bonus: "Bonificação",
  subscription: "Subscrição",
};

export function DividendTable({ events }: { events: CorporateEvent[] }) {
  if (events.length === 0) {
    return <p className="text-ice-70">Nenhum provento anunciado no período carregado.</p>;
  }

  return (
    <Table caption="Proventos e eventos anunciados">
      <Thead>
        <Tr>
          <Th>Tipo</Th>
          <Th>Data-com</Th>
          <Th>Pagamento</Th>
          <Th className="text-right">Valor por ação</Th>
        </Tr>
      </Thead>
      <tbody>
        {events.map((event, index) => (
          <Tr key={`${event.kind}-${event.ex_date}-${index}`}>
            <Td>{KIND_LABELS[event.kind] ?? event.kind}</Td>
            <Td className="tabular-nums">{date(event.ex_date)}</Td>
            <Td className="tabular-nums">{date(event.payment_date)}</Td>
            <Td numeric className="tabular-nums">
              {event.ratio ? (
                event.ratio
              ) : (
                <Value reason={event.value_per_share ? undefined : "evento sem valor por ação"}>
                  {currency(event.value_per_share)}
                </Value>
              )}
            </Td>
          </Tr>
        ))}
      </tbody>
    </Table>
  );
}
