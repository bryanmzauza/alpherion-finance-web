// Ativo → fatores de risco (site.md §4.2), a base da leitura de exposição do raio-x
// (Etapa 6). Os pesos explícitos são os do `FATORES` de `ferramentas/raio-x-carteira.py`
// (o mesmo número do vídeo 02); os demais ativos recebem o padrão da classe, que a
// Etapa 6 pode refinar com o setor B3 vindo da API. Nenhum peso aqui é recomendação: é
// a hipótese de a que cada ativo responde, e o texto da análise a apresenta como tal.

import type { assetClass } from "@/drizzle/schema";

type AssetClass = (typeof assetClass.enumValues)[number];

/** Pesos explícitos do `raio-x-carteira.py`. */
const EXPLICIT: Record<string, Record<string, number>> = {
  BTC: { Cripto: 1 },
  ETH: { Cripto: 1 },
  SOL: { Cripto: 1 },
  USDC: { Dólar: 1 },
  PETR4: { "Commodity/petróleo": 0.6, Dólar: 0.2, "Bolsa BR": 0.2 },
  VALE3: { "Commodity/minério": 0.6, Dólar: 0.2, "Bolsa BR": 0.2 },
  ITUB4: { "Bolsa BR": 0.6, "Juros BR": 0.4 },
  WEGE3: { "Bolsa BR": 0.6, Dólar: 0.2, "Juros BR": 0.2 },
  MXRF11: { "Juros BR": 0.8, "Bolsa BR": 0.2 },
  HGLG11: { "Juros BR": 0.8, "Bolsa BR": 0.2 },
};

/** Padrão por classe, no mesmo espírito dos pesos explícitos. */
const BY_CLASS: Record<AssetClass, Record<string, number> | null> = {
  crypto: { Cripto: 1 },
  stablecoin: { Dólar: 1 },
  stock_br: { "Bolsa BR": 1 },
  etf_br: { "Bolsa BR": 1 },
  fii: { "Juros BR": 0.8, "Bolsa BR": 0.2 },
  bdr: { "Bolsa exterior": 0.8, Dólar: 0.2 },
  treasury: { "Juros BR": 1 },
  fixed_income: { "Juros BR": 1 },
  other: null,
};

export function defaultFactorMap(symbol: string, cls: AssetClass): Record<string, number> | null {
  return EXPLICIT[symbol.toUpperCase()] ?? BY_CLASS[cls];
}
