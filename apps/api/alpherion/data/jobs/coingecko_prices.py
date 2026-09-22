"""Cotação e métricas de criptoativos (horário).

**Só desenvolvimento** até haver fonte licenciada: `data_sources` tem a CoinGecko sem
`terms_checked_at`, então em produção o job termina como `skipped` com o motivo
(ADR-017), e `/cripto` mostra "—" com a explicação.

Dois destinos por execução: `crypto_assets` (cadastro) e `crypto_metrics` (o snapshot
"agora" que a página mostra). O fechamento diário é do `coingecko_history`.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime

from alpherion.data.jobs import base
from alpherion.data.sources import coingecko
from alpherion.db.models import CryptoAsset, CryptoMetric
from alpherion.db.upsert import upsert

logger = logging.getLogger(__name__)

JOB = "coingecko_prices"
SOURCE = "coingecko"
#: Quantos ativos acompanhamos. Mais que isso vira ruído numa página de carteira.
DEFAULT_TOP = 100


def run(*, top: int = DEFAULT_TOP) -> None:
    with base.run(JOB, period=date.today(), source=SOURCE) as ctx:
        assets = coingecko.fetch_markets(per_page=top)
        captured_at = datetime.now(UTC)

        ctx.wrote(
            upsert(
                ctx.session,
                CryptoAsset,
                [
                    {
                        "id": asset.asset_id,
                        "symbol": asset.symbol,
                        "name": asset.name,
                        "market_cap_rank": rank,
                    }
                    for rank, asset in enumerate(assets, start=1)
                ],
                # `is_stablecoin` é classificação nossa (o engine trata stablecoin com
                # fator próprio) e não pode ser apagada por uma carga de preço.
                update=["symbol", "name", "market_cap_rank"],
            )
        )
        ctx.wrote(
            upsert(
                ctx.session,
                CryptoMetric,
                [
                    {
                        "id": asset.asset_id,
                        "captured_at": captured_at,
                        "price_brl": asset.price,
                        "change_24h": asset.change_24h,
                        "market_cap_brl": asset.market_cap,
                        "volume_24h_brl": asset.volume_24h,
                        "circulating_supply": asset.circulating_supply,
                    }
                    for asset in assets
                ],
            )
        )


if __name__ == "__main__":  # pragma: no cover - entrada de linha de comando
    base.main(run)
