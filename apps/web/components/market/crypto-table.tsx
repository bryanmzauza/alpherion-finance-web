import type { CryptoItem } from "@/lib/market";
import { compactCurrency, currency, direction, signedPercent } from "@/lib/format";
import { Table, Td, Th, Thead, Tr } from "@/components/ui/table";
import { SourceBadge } from "@/components/market/source-badge";
import { Value } from "@/components/market/value";
import { cn } from "@/lib/cn";

// Criptoativos por valor de mercado.
//
// A ordem é por valor de mercado e o título diz isso — é o critério mais neutro que
// existe para cripto (ordenar por variação seria destacar o que subiu hoje, que é a
// definição de isca). Sem a fonte licenciada (ADR-017), a API devolve preço `null` com
// o motivo e a tabela mostra "—": o ativo continua listado, o preço é que não sai.
const TREND = { up: "text-ok", down: "text-risk-text", flat: "text-ice-70" } as const;

export function CryptoTable({ assets }: { assets: CryptoItem[] }) {
  if (assets.length === 0) {
    return <p className="text-ice-70">Nenhum criptoativo carregado.</p>;
  }

  return (
    <>
      <Table caption="Criptoativos, por valor de mercado">
        <Thead>
          <Tr>
            <Th className="text-right">#</Th>
            <Th>Ativo</Th>
            <Th className="text-right">Cotação</Th>
            <Th className="text-right">24 h</Th>
            <Th className="text-right">Valor de mercado</Th>
          </Tr>
        </Thead>
        <tbody>
          {assets.map((asset) => (
            <Tr key={asset.id}>
              <Td numeric className="tabular-nums text-ice-70">
                {asset.rank ?? "—"}
              </Td>
              <Td>
                <span className="tabular-nums">{asset.symbol}</span>{" "}
                <span className="text-ice-70">{asset.name}</span>
              </Td>
              <Td numeric className="tabular-nums">
                <Value reason={asset.missing_reasons.price}>{currency(asset.price)}</Value>
              </Td>
              <Td numeric className={cn("tabular-nums", TREND[direction(asset.change_24h)])}>
                <Value reason={asset.missing_reasons.change_24h}>
                  {signedPercent(asset.change_24h)}
                </Value>
              </Td>
              <Td numeric className="tabular-nums">
                <Value reason={asset.missing_reasons.market_cap}>
                  {compactCurrency(asset.market_cap)}
                </Value>
              </Td>
            </Tr>
          ))}
        </tbody>
      </Table>
      {assets[0] ? <SourceBadge source={assets[0].source} className="mt-3" /> : null}
    </>
  );
}
