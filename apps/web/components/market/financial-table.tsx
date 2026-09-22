import type { Financials } from "@/lib/market";
import { compactCurrency } from "@/lib/format";
import { Table, Td, Th, Thead, Tr } from "@/components/ui/table";
import { SourceBadge } from "@/components/market/source-badge";
import { Value } from "@/components/market/value";

// Demonstrações no formato da CVM — conta, descrição e valor. Só as contas de primeiro
// e segundo nível: a DFP inteira tem centenas de linhas e a página do ativo não é um
// visualizador de XBRL. Quem quer o detalhe tem o link da CVM nos comunicados.
const STATEMENT_LABELS: Record<string, string> = {
  dre: "Demonstração do resultado",
  bp_ativo: "Balanço — ativo",
  bp_passivo: "Balanço — passivo",
  dfc: "Fluxo de caixa",
};

const MAX_LEVEL = 2;

export function FinancialTable({ financials }: { financials: Financials }) {
  return (
    <section aria-labelledby="demonstracoes">
      <h2 id="demonstracoes">Demonstrações</h2>
      <p className="mt-2 text-table text-ice-70">
        {financials.consolidated ? "Consolidado" : "Individual"} · exercício encerrado em{" "}
        {financials.period_end.split("-").reverse().join("/")}
      </p>

      <div className="mt-6 space-y-8">
        {Object.entries(financials.statements).map(([statement, lines]) => (
          <div key={statement}>
            <h3 className="text-table font-medium uppercase tracking-wide text-ice-70">
              {STATEMENT_LABELS[statement] ?? statement}
            </h3>
            <Table caption={STATEMENT_LABELS[statement] ?? statement} className="mt-3">
              <Thead>
                <Tr>
                  <Th>Conta</Th>
                  <Th className="text-right">Valor</Th>
                </Tr>
              </Thead>
              <tbody>
                {lines.filter(topLevel).map((line) => (
                  <Tr key={line.account_code}>
                    <Td>
                      <span className="text-ice-70 tabular-nums">{line.account_code}</span>{" "}
                      {line.account_name}
                    </Td>
                    <Td numeric className="tabular-nums">
                      <Value reason={line.value === null ? "conta sem valor na DFP" : undefined}>
                        {compactCurrency(line.value)}
                      </Value>
                    </Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          </div>
        ))}
      </div>
      <SourceBadge source={financials.source} className="mt-6" />
    </section>
  );
}

function topLevel(line: { account_code: string }): boolean {
  return line.account_code.split(".").length <= MAX_LEVEL;
}
