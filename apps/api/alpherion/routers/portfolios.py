"""Valorização da carteira (site.md §2.3). A API não conhece a pessoa: recebe posições,
devolve números, não guarda nada."""

from __future__ import annotations

import datetime as dt
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from alpherion.auth import require_scopes
from alpherion.db.session import get_session
from alpherion.market import valuation
from alpherion.market.flags import Gate
from alpherion.settings import Settings, get_settings

router = APIRouter(
    prefix="/portfolios",
    tags=["portfolios"],
    dependencies=[Depends(require_scopes("market:read"))],
)


@router.post("/valuation", response_model=valuation.Valuation)
async def value_portfolio(
    body: valuation.ValuationRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> valuation.Valuation:
    """Preço atual, valor, resultado e peso por posição (≤ 100 posições)."""
    today = dt.datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    return await valuation.value_positions(
        body, valuation.DbPriceSource(session, today), Gate(settings)
    )
