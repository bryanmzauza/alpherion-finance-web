"use client";

import { useMemo } from "react";
import type { Quote } from "@/lib/market";
import { currency, date, toNumber } from "@/lib/format";

type Props = {
  quotes: Quote[];
  label: string;
};

// Gráfico de linha em SVG puro (site.md §5 e §9): sem biblioteca de charts.
//
// O orçamento de JS da página pública é de 170 kB gzip; qualquer biblioteca de gráfico
// come metade disso sozinha, e o que esta página precisa é uma linha com eixo de datas.
// Como é SVG servido pelo servidor, o gráfico aparece no primeiro paint.
//
// **A tabela é o fallback real**, não um enfeite de acessibilidade: com a fonte de preço
// travada (ADR-017) não há série nenhuma, e a página precisa dizer isso em vez de
// desenhar um gráfico vazio.
export function HistoryChart({ quotes, label }: Props) {
  const points = useMemo(
    () =>
      quotes
        .map((q) => ({ date: q.date, value: toNumber(q.close) }))
        .filter((p): p is { date: string; value: number } => p.value !== null),
    [quotes],
  );

  if (points.length < 2) {
    return (
      <p className="text-ice-70">
        Sem histórico disponível para exibir o gráfico. Os dados de cotação dependem da
        licença da fonte.
      </p>
    );
  }

  const values = points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const width = 720;
  const height = 240;

  const path = points
    .map((p, i) => {
      const x = (i / (points.length - 1)) * width;
      const y = height - ((p.value - min) / span) * height;
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  const first = points[0];
  const last = points[points.length - 1];

  return (
    <figure>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="h-60 w-full"
        role="img"
        aria-label={`${label}: de ${currency(first.value)} em ${date(first.date)} a ${currency(last.value)} em ${date(last.date)}`}
        preserveAspectRatio="none"
      >
        <path d={path} fill="none" stroke="var(--color-gold)" strokeWidth={2} vectorEffect="non-scaling-stroke" />
      </svg>
      <figcaption className="mt-2 flex justify-between text-table tabular-nums text-ice-70">
        <span>
          {date(first.date)} · {currency(first.value)}
        </span>
        <span>
          {date(last.date)} · {currency(last.value)}
        </span>
      </figcaption>
    </figure>
  );
}
