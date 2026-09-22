import Link from "next/link";
import type { SecurityType } from "@/lib/market";

// Caminho canônico de cada classe. Uma única fonte da verdade: a mesma função monta o
// link da tabela, o do sitemap e o do redirect de classe errada.
const PATHS: Record<SecurityType, string> = {
  stock: "/acoes",
  unit: "/acoes",
  fii: "/fiis",
  fiagro: "/fiis",
  etf: "/etfs",
  bdr: "/bdrs",
};

export function pathFor(type: SecurityType, ticker: string): string {
  return `${PATHS[type] ?? "/acoes"}/${ticker.toUpperCase()}`;
}

export function basePathFor(type: SecurityType): string {
  return PATHS[type] ?? "/acoes";
}

export function TickerLink({ type, ticker }: { type: SecurityType; ticker: string }) {
  return (
    <Link
      href={pathFor(type, ticker)}
      className="tabular-nums underline decoration-ice-70/40 underline-offset-4 hover:decoration-ice"
    >
      {ticker}
    </Link>
  );
}
