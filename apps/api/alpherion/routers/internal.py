"""Endpoints de operação (site.md §3.6). Não fazem parte do produto.

`GET /v1/internal/freshness` é o que o Uptime Kuma consulta: devolve 200 quando o
pipeline rodou como deveria e 503 quando não — porque um monitor entende código HTTP,
não JSON. O corpo diz **qual** job falhou, para o alerta já chegar com a informação que
resolve.

Por que um endpoint e não só o job do Telegram: o alerta do Telegram depende do worker
estar vivo. Se o container `data` morrer, é justamente o alerta que para de chegar. O
monitor externo bate na API, que é outro processo.
"""

from __future__ import annotations

import datetime as dt
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from alpherion.auth import require_scopes
from alpherion.data.freshness import Level, Run, evaluate
from alpherion.db.models import EtlRun
from alpherion.db.session import get_session

router = APIRouter(
    prefix="/internal",
    tags=["internal"],
    dependencies=[Depends(require_scopes("market:read"))],
    include_in_schema=False,
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]

#: Janela consultada: o suficiente para a regra de dois dias seguidos, com folga.
WINDOW_DAYS = 5


class FreshnessFinding(BaseModel):
    job: str
    message: str


class FreshnessResponse(BaseModel):
    status: Literal["ok", "warning"]
    findings: list[FreshnessFinding]
    checked_at: dt.datetime


@router.get("/freshness", response_model=FreshnessResponse)
async def freshness(session: SessionDep, response: Response) -> FreshnessResponse:
    """Frescor do pipeline. 503 quando algum job não rodou como deveria."""
    now = dt.datetime.now(dt.UTC)
    rows = (
        await session.execute(
            select(EtlRun.job, EtlRun.status, EtlRun.started_at, EtlRun.period)
            .where(EtlRun.started_at >= now - dt.timedelta(days=WINDOW_DAYS))
            .order_by(EtlRun.started_at.desc())
        )
    ).all()

    report = evaluate(
        [Run(job=row[0], status=row[1], started_at=row[2], period=row[3]) for row in rows],
        now=now,
    )
    if report.level is Level.WARNING:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return FreshnessResponse(
        status=report.level.value,
        findings=[FreshnessFinding(job=f.job, message=f.message) for f in report.findings],
        checked_at=report.checked_at,
    )
