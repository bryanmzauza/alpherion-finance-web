"""`Catalog` sobre o schema `market` (uma consulta por tipo de ativo, não por linha)."""

from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from alpherion.db.models import CryptoAsset, Security, TreasuryBond
from alpherion.importers.assets import CryptoInfo, SecurityInfo, TreasuryInfo


class DbCatalog:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def securities(self, tickers: set[str]) -> Mapping[str, SecurityInfo]:
        rows = await self.session.execute(
            select(
                Security.ticker, Security.type, Security.trade_name, Security.company_name
            ).where(Security.ticker.in_(tickers))
        )
        return {
            ticker: SecurityInfo(ticker=ticker, type=kind, name=trade or company)
            for ticker, kind, trade, company in rows
        }

    async def treasury(self) -> list[TreasuryInfo]:
        rows = await self.session.execute(
            select(TreasuryBond.slug, TreasuryBond.name, TreasuryBond.maturity)
        )
        return [TreasuryInfo(slug=s, name=n, maturity=m) for s, n, m in rows]

    async def crypto(self, symbols: set[str]) -> Mapping[str, CryptoInfo]:
        rows = await self.session.execute(
            select(CryptoAsset.id, CryptoAsset.symbol, CryptoAsset.name, CryptoAsset.is_stablecoin)
            .where(CryptoAsset.symbol.in_(symbols))
            # Símbolo repetido entre moedas (acontece): fica a de maior capitalização.
            .order_by(CryptoAsset.market_cap_rank.asc().nulls_last())
        )
        found: dict[str, CryptoInfo] = {}
        for coin_id, symbol, name, stable in rows:
            found.setdefault(
                symbol.upper(),
                CryptoInfo(id=coin_id, symbol=symbol.upper(), name=name, is_stablecoin=stable),
            )
        return found
