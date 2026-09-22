import type { PriceHeaderData, SecurityProfile } from "@/lib/market";
import { compactCurrency, currency, date, direction, signedPercent } from "@/lib/format";
import { SourceBadge } from "@/components/market/source-badge";
import { Value } from "@/components/market/value";
import { cn } from "@/lib/cn";

type Props = {
  profile: SecurityProfile;
  price: PriceHeaderData;
};

const TREND = {
  up: "text-ok",
  down: "text-risk-text",
  flat: "text-ice-70",
} as const;

// Cabeçalho da página do ativo. Cotação, variação, extremos de 52 semanas e volume —
// tudo fato, nada de "potencial" ou "alvo".
//
// Sem a licença da B3 (ADR-017), a API devolve preço `null` com o motivo; aqui isso vira
// "—" com tooltip, e o cabeçalho continua de pé com o nome, a classe e o setor. A página
// não pode parecer quebrada por causa de uma licença pendente.
export function PriceHeader({ profile, price }: Props) {
  const trend = direction(price.change_percent_day);

  return (
    <header className="border-b border-navy-3 pb-8">
      <p className="text-table uppercase tracking-wide text-ice-70">{labelOf(profile.type)}</p>
      <h1 className="mt-2 flex flex-wrap items-baseline gap-3">
        <span className="tabular-nums">{profile.ticker}</span>
        <span className="text-h2 font-normal text-ice-70">{profile.trade_name ?? profile.company_name}</span>
      </h1>

      <div className="mt-6 flex flex-wrap items-baseline gap-x-6 gap-y-2">
        <span className="text-h1 font-display tabular-nums">
          <Value reason={price.missing_reasons.price}>{currency(price.price)}</Value>
        </span>
        <span className={cn("text-h2 tabular-nums", TREND[trend])}>
          <Value reason={price.missing_reasons.change_percent_day}>
            {signedPercent(price.change_percent_day)}
          </Value>
        </span>
        {price.quote_date ? (
          <span className="text-table text-ice-70">fechamento de {date(price.quote_date)}</span>
        ) : null}
      </div>

      <dl className="mt-6 grid grid-cols-2 gap-x-8 gap-y-3 text-table sm:grid-cols-3">
        <Fact label="Mínima 52 semanas" reason={price.missing_reasons.low_52w}>
          {currency(price.low_52w)}
        </Fact>
        <Fact label="Máxima 52 semanas" reason={price.missing_reasons.high_52w}>
          {currency(price.high_52w)}
        </Fact>
        <Fact label="Volume do dia" reason={price.missing_reasons.volume}>
          {compactCurrency(price.volume)}
        </Fact>
      </dl>

      <SourceBadge source={price.source} className="mt-6" />
    </header>
  );
}

function Fact({
  label,
  reason,
  children,
}: {
  label: string;
  reason?: string;
  children: string;
}) {
  return (
    <div>
      <dt className="text-ice-70">{label}</dt>
      <dd className="tabular-nums">
        <Value reason={reason}>{children}</Value>
      </dd>
    </div>
  );
}

const LABELS: Record<string, string> = {
  stock: "Ação",
  unit: "Unit",
  fii: "Fundo imobiliário",
  fiagro: "Fiagro",
  etf: "ETF",
  bdr: "BDR",
};

function labelOf(type: string): string {
  return LABELS[type] ?? "Ativo";
}
