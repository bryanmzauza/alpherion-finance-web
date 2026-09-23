import Link from "next/link";
import type { SecuritySummary } from "@/lib/market";
import { compactCurrency, currency, multiple, percent } from "@/lib/format";
import { sortPhrase, sortQuery, type Sort, type SortField } from "@/lib/market-sort";
import { Table, Td, Th, Thead, Tr } from "@/components/ui/table";
import { Change } from "@/components/market/change";
import { TickerLink } from "@/components/market/ticker-link";
import { Value } from "@/components/market/value";
import { cn } from "@/lib/cn";

// Tabela de papéis ordenável por URL (plano 4.4 e 4.5): o cabeçalho de cada coluna é um
// link `?sort=&dir=`, a ordem é feita **na API** (lista fechada de campos) e a coluna que
// ordena está sempre visível — ordenar por um número que a tabela esconde tiraria do
// leitor o critério da ordem.

export type ColumnKey = "price" | "change" | "volume" | "pe" | "pvp" | "dy_12m" | "roe" | "market_cap";

type Column = {
  label: string;
  sort?: SortField;
  /** Direção do primeiro clique. */
  firstDir?: "asc" | "desc";
  render: (row: SecuritySummary) => React.ReactNode;
};

const reason = (row: SecuritySummary, key: string) => row.missing_reasons?.[key];

const COLUMNS: Record<ColumnKey, Column> = {
  price: {
    label: "Cotação",
    render: (row) => <Value reason={reason(row, "price")}>{currency(row.price)}</Value>,
  },
  change: {
    label: "Variação",
    sort: "change",
    render: (row) => <Change value={row.change_percent_day} reason={reason(row, "change_percent_day")} />,
  },
  volume: {
    label: "Volume do dia",
    sort: "volume",
    render: (row) => <Value reason={reason(row, "volume")}>{compactCurrency(row.volume)}</Value>,
  },
  pe: {
    label: "P/L",
    sort: "pe",
    firstDir: "asc",
    render: (row) => <Value reason={reason(row, "pe")}>{multiple(row.pe)}</Value>,
  },
  pvp: {
    label: "P/VP",
    sort: "pvp",
    firstDir: "asc",
    render: (row) => <Value reason={reason(row, "pvp")}>{multiple(row.pvp)}</Value>,
  },
  dy_12m: {
    label: "DY 12 m",
    sort: "dy_12m",
    render: (row) => <Value reason={reason(row, "dy_12m")}>{percent(row.dy_12m)}</Value>,
  },
  roe: {
    label: "ROE",
    sort: "roe",
    render: (row) => <Value reason={reason(row, "roe")}>{percent(row.roe)}</Value>,
  },
  market_cap: {
    label: "Valor de mercado",
    sort: "market_cap",
    render: (row) => <Value reason={reason(row, "market_cap")}>{compactCurrency(row.market_cap)}</Value>,
  },
};

type Props = {
  rows: SecuritySummary[];
  columns: ColumnKey[];
  sort: Sort;
  /** Caminho da página, para montar os links de ordenação. */
  basePath: string;
  caption: string;
};

export function SortableSecurityTable({ rows, columns, sort, basePath, caption }: Props) {
  if (rows.length === 0) {
    return <p className="text-ice-70">Nenhum papel carregado nesta lista.</p>;
  }

  return (
    <Table caption={`${caption}, ${sortPhrase(sort)}`}>
      <Thead>
        <Tr>
          <Th aria-sort={ariaSort(sort, "ticker")}>
            <SortLink field="ticker" firstDir="asc" sort={sort} basePath={basePath}>
              Papel
            </SortLink>
          </Th>
          <Th className="hidden md:table-cell">Empresa</Th>
          {columns.map((key) => {
            const column = COLUMNS[key];
            return (
              <Th
                key={key}
                className="text-right whitespace-nowrap"
                aria-sort={column.sort ? ariaSort(sort, column.sort) : undefined}
              >
                {column.sort ? (
                  <SortLink field={column.sort} firstDir={column.firstDir ?? "desc"} sort={sort} basePath={basePath}>
                    {column.label}
                  </SortLink>
                ) : (
                  column.label
                )}
              </Th>
            );
          })}
        </Tr>
      </Thead>
      <tbody>
        {rows.map((row) => (
          <Tr key={row.ticker}>
            <Td>
              <TickerLink type={row.type} ticker={row.ticker} />
            </Td>
            <Td className="hidden max-w-64 truncate md:table-cell">{row.trade_name ?? row.company_name}</Td>
            {columns.map((key) => (
              <Td key={key} numeric className="tabular-nums whitespace-nowrap">
                {COLUMNS[key].render(row)}
              </Td>
            ))}
          </Tr>
        ))}
      </tbody>
    </Table>
  );
}

function ariaSort(sort: Sort, field: SortField): "ascending" | "descending" | undefined {
  if (sort.field !== field) return undefined;
  return sort.dir === "asc" ? "ascending" : "descending";
}

function SortLink({
  field,
  firstDir,
  sort,
  basePath,
  children,
}: {
  field: SortField;
  firstDir: "asc" | "desc";
  sort: Sort;
  basePath: string;
  children: React.ReactNode;
}) {
  const active = sort.field === field;
  const next: Sort = active ? { field, dir: sort.dir === "asc" ? "desc" : "asc" } : { field, dir: firstDir };
  // `sortQuery` omite o padrão: voltar a ele tira a query, e a versão indexável não tem.
  const href = `${basePath}${sortQuery(next)}`;
  return (
    <Link
      href={href}
      scroll={false}
      className={cn("inline-flex items-center gap-1 hover:text-ice", active && "text-ice")}
    >
      {children}
      <span aria-hidden="true" className="text-xs">
        {active ? (sort.dir === "asc" ? "▲" : "▼") : ""}
      </span>
    </Link>
  );
}

export function Pagination({
  page,
  pages,
  basePath,
  sort,
}: {
  page: number;
  pages: number;
  basePath: string;
  sort: Sort;
}) {
  if (pages <= 1) return null;
  const link = (target: number) =>
    `${basePath}${sortQuery(sort, target > 1 ? { page: String(target) } : {})}`;
  return (
    <nav aria-label="Páginas da lista" className="mt-6 flex items-center gap-4 text-table">
      {page > 1 ? (
        <Link href={link(page - 1)} className="text-gold underline underline-offset-4">
          ← Anterior
        </Link>
      ) : null}
      <span className="text-ice-70 tabular-nums">
        Página {page} de {pages}
      </span>
      {page < pages ? (
        <Link href={link(page + 1)} className="text-gold underline underline-offset-4">
          Próxima →
        </Link>
      ) : null}
    </nav>
  );
}
