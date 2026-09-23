import { pathFor } from "@/components/market/ticker-link";
import type { AssetHit, AssetSearchGroup } from "@/lib/market";

// Apresentação da busca global (site.md §2.1): rótulo de cada grupo e o caminho de cada
// resultado. Só tipos e funções puras — o componente do header importa daqui e não
// pode arrastar `lib/env` para o navegador.

export const GROUP_LABELS: Record<AssetSearchGroup["asset_class"], string> = {
  stock: "Ações",
  fii: "FIIs",
  etf: "ETFs",
  bdr: "BDRs",
  index: "Índices",
  treasury: "Tesouro Direto",
  crypto: "Cripto",
};

/**
 * Caminho de um resultado. Título do Tesouro e criptoativo ainda não têm página
 * própria: o link cai na linha da tabela (`/tesouro#titulo-…`), que tem o `id`.
 */
export function hitHref(hit: AssetHit): string {
  switch (hit.type) {
    case "index":
      return `/indices/${hit.code}`;
    case "treasury":
      return `/tesouro#${treasuryAnchor(hit.code)}`;
    case "crypto":
      return `/cripto#${cryptoAnchor(hit.code)}`;
    default:
      return pathFor(hit.type, hit.code);
  }
}

export const treasuryAnchor = (slug: string) => `titulo-${slug}`;
export const cryptoAnchor = (id: string) => `cripto-${id}`;

/** Tamanho mínimo da busca — o mesmo `min_length` da API. */
export const MIN_QUERY = 2;
export const MAX_QUERY = 60;
