// Resumo dos proventos recebidos (plano 5.3). Fica no `web` pelo mesmo motivo da posição
// (`lib/positions.ts`): os valores estão cifrados no schema `app` e só são decifrados
// aqui. É soma e divisão sobre o que a pessoa recebeu — fato, não projeção.

export type IncomeRow = { assetId: string; symbol: string; date: string; net: string };

export type IncomeSummary = {
  byYear: { year: string; net: number }[];
  byAsset: { assetId: string; symbol: string; net12m: number; netTotal: number; yieldOnCost: number | null }[];
  total: number;
  total12m: number;
};

/**
 * `yieldOnCost` = proventos líquidos dos últimos 12 meses ÷ custo atual da posição
 * (quantidade × preço médio). `null` quando não há custo conhecido.
 */
export function summarizeIncome(rows: IncomeRow[], costByAsset: Map<string, number | null>, today: Date): IncomeSummary {
  const cutoff = new Date(today);
  cutoff.setUTCFullYear(cutoff.getUTCFullYear() - 1);
  const since = cutoff.toISOString().slice(0, 10);

  const years = new Map<string, number>();
  const assets = new Map<string, { symbol: string; net12m: number; netTotal: number }>();
  let total = 0;
  let total12m = 0;

  for (const row of rows) {
    const net = Number(row.net);
    if (!Number.isFinite(net)) continue;
    const year = row.date.slice(0, 4);
    years.set(year, (years.get(year) ?? 0) + net);
    const entry = assets.get(row.assetId) ?? { symbol: row.symbol, net12m: 0, netTotal: 0 };
    entry.netTotal += net;
    total += net;
    if (row.date > since) {
      entry.net12m += net;
      total12m += net;
    }
    assets.set(row.assetId, entry);
  }

  return {
    byYear: [...years.entries()].sort(([a], [b]) => (a < b ? 1 : -1)).map(([year, net]) => ({ year, net })),
    byAsset: [...assets.entries()]
      .map(([assetId, e]) => {
        const cost = costByAsset.get(assetId) ?? null;
        return { assetId, ...e, yieldOnCost: cost && cost > 0 ? e.net12m / cost : null };
      })
      .sort((a, b) => b.netTotal - a.netTotal),
    total,
    total12m,
  };
}
