"""Alerta de frescor no Telegram (plano §3.6).

Roda depois da janela de carga do dia. Não recalcula nada: aplica as regras de
`data/freshness.py` — as mesmas do endpoint que o Uptime Kuma consulta — e manda a
mensagem quando há o que dizer.

**Silêncio é o resultado normal.** Um alerta que chega todo dia dizendo "tudo bem" deixa
de ser lido em uma semana, e aí o dia em que ele diz outra coisa passa em branco.

Sem `TELEGRAM_BOT_TOKEN`/`TELEGRAM_ALERT_CHAT_ID` configurados, o job termina como
`skipped` com o motivo: em desenvolvimento não há para onde mandar, e isso não é falha.
"""

from __future__ import annotations

import datetime as dt
import logging
import os

import httpx
from sqlalchemy import select

from alpherion.data.freshness import Level, Run, evaluate
from alpherion.data.jobs import base
from alpherion.db.models import EtlRun

logger = logging.getLogger(__name__)

JOB = "freshness_alert"
WINDOW_DAYS = 5
TELEGRAM_URL = "https://api.telegram.org/bot{token}/sendMessage"


def run() -> None:
    with base.run(JOB, period=dt.date.today(), use_lock=False) as ctx:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_ALERT_CHAT_ID")
        now = dt.datetime.now(dt.UTC)

        rows = ctx.session.execute(
            select(EtlRun.job, EtlRun.status, EtlRun.started_at, EtlRun.period).where(
                EtlRun.started_at >= now - dt.timedelta(days=WINDOW_DAYS)
            )
        ).all()
        report = evaluate(
            [Run(job=r[0], status=r[1], started_at=r[2], period=r[3]) for r in rows], now=now
        )
        ctx.notes["findings"] = [f.job for f in report.findings]

        if report.level is Level.OK:
            logger.info("frescor: tudo carregado")
            return
        if not token or not chat_id:
            raise base.JobSkipped(
                f"{len(report.findings)} alerta(s), mas o Telegram não está configurado"
            )

        response = httpx.post(
            TELEGRAM_URL.format(token=token),
            data={"chat_id": chat_id, "text": report.as_text()},
            timeout=15.0,
        )
        response.raise_for_status()
        ctx.wrote(len(report.findings))


if __name__ == "__main__":  # pragma: no cover - entrada de linha de comando
    base.main(run)
