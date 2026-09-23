import type { MoversList as MoversListData } from "@/lib/market";
import { compactCurrency, currency } from "@/lib/format";
import { Table, Td, Th, Thead, Tr } from "@/components/ui/table";
import { Change } from "@/components/market/change";
import { SourceBadge } from "@/components/market/source-badge";
import { TickerLink } from "@/components/market/ticker-link";
import { Value } from "@/components/market/value";

// Uma lista do dia de `/mercado` (plano 4.2): **a métrica vai no título** e o piso de
// liquidez vai logo abaixo. "Maiores altas" sem o critério é ranking editorial; com o
// critério ("variação do fechamento, entre papéis com mais de R$ 1 mi negociados") é
// fato ordenado por um número (ADR-018).

const METRIC_PHRASE = {
  change: "variação do fechamento sobre o pregão anterior",
  volume: "volume financeiro do dia",
} as const;

type Props = {
  title: string;
  list: MoversListData;
  id: string;
};

export function MoversList({ title, list, id }: Props) {
  const metric = METRIC_PHRASE[list.metric];
  const order = list.direction === "desc" ? "do maior para o menor" : "do menor para o maior";

  return (
    <section aria-labelledby={id}>
      <h3 id={id} className="font-display text-xl font-semibold">
        {title}
      </h3>
      <p className="mt-1 text-table text-ice-70">
        Por {metric}, {order}
        {list.min_volume ? `, entre papéis com mais de ${compactCurrency(list.min_volume)} negociados` : ""}.
      </p>

      <div className="mt-4">
        {list.items.length === 0 ? (
          <p className="text-table text-ice-70">
            <Value reason={list.missing_reasons.items}>—</Value>{" "}
            {list.missing_reasons.items ?? "Sem papéis que passem pelo piso de liquidez hoje."}
          </p>
        ) : (
          <Table caption={`${title}: ${metric}`}>
            <Thead>
              <Tr>
                <Th>Papel</Th>
                <Th className="hidden sm:table-cell xl:hidden">Empresa</Th>
                <Th className="text-right">Cotação</Th>
                <Th className="text-right">Variação</Th>
                <Th className="text-right">Volume</Th>
              </Tr>
            </Thead>
            <tbody>
              {list.items.map((item) => (
                <Tr key={item.ticker}>
                  {/* Nas três listas lado a lado (xl) não cabe o nome: fica no `title`. */}
                  <Td title={item.company_name}>
                    <TickerLink type={item.type ?? "stock"} ticker={item.ticker} />
                  </Td>
                  <Td className="hidden max-w-48 truncate sm:table-cell xl:hidden">{item.company_name}</Td>
                  <Td numeric className="tabular-nums">
                    <Value reason={item.missing_reasons?.price}>{currency(item.price)}</Value>
                  </Td>
                  <Td numeric>
                    <Change value={item.change_percent} reason={item.missing_reasons?.change_percent} />
                  </Td>
                  <Td numeric className="tabular-nums whitespace-nowrap">
                    <Value reason={item.missing_reasons?.volume}>{compactCurrency(item.volume)}</Value>
                  </Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        )}
      </div>
      <SourceBadge source={list.source} className="mt-3" />
    </section>
  );
}

