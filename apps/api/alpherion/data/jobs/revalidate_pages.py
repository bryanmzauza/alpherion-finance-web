"""Avisa o Next que as páginas mudaram (ISR sob demanda).

Último job do dia. As páginas de mercado são estáticas com revalidação (§3.6 do
site.md): sem este aviso, o visitante veria o dado de ontem até a revalidação por tempo
expirar. O `web` expõe `POST /api/revalidate` protegido por token.

É o único job que fala com o `web` — e ainda assim não atravessa a fronteira de
privacidade: manda **caminhos**, nunca dado. Quem lê o banco continua sendo só o `web`,
pela API.

Falhar aqui não invalida a carga do dia: o dado está no banco e a revalidação por tempo
acontece de qualquer jeito. Por isso a falha é registrada e não re-levantada.
"""

from __future__ import annotations

import logging
from datetime import date

import httpx
from sqlalchemy import select

from alpherion.data.jobs import base
from alpherion.db.models import Security
from alpherion.settings import get_settings

logger = logging.getLogger(__name__)

JOB = "revalidate_pages"

#: Páginas que mudam todo dia, independentemente de qual papel foi carregado.
ALWAYS = ("/", "/mercado", "/agenda", "/acoes", "/fiis", "/etfs", "/bdrs", "/indices", "/tesouro")

#: O Next revalida por caminho; mandar milhares de uma vez estoura o tempo da requisição.
BATCH = 200

PATH_BY_TYPE = {
    "stock": "/acoes",
    "unit": "/acoes",
    "fii": "/fiis",
    "fiagro": "/fiis",
    "etf": "/etfs",
    "bdr": "/bdrs",
}


def run(*, paths: list[str] | None = None) -> None:
    settings = get_settings()
    with base.run(JOB, period=date.today()) as ctx:
        if not settings.web_revalidate_url or not settings.web_revalidate_token:
            raise base.JobSkipped("WEB_REVALIDATE_URL/TOKEN não configurados")

        alvos = paths or [*ALWAYS, *_asset_paths(ctx)]
        enviados, falhas = 0, 0
        with httpx.Client(timeout=30.0) as http:
            for start in range(0, len(alvos), BATCH):
                batch = alvos[start : start + BATCH]
                try:
                    response = http.post(
                        settings.web_revalidate_url,
                        json={"paths": batch},
                        headers={"Authorization": f"Bearer {settings.web_revalidate_token}"},
                    )
                    response.raise_for_status()
                except httpx.HTTPError as error:
                    falhas += len(batch)
                    logger.warning("revalidação de %d caminhos falhou: %s", len(batch), error)
                    continue
                enviados += len(batch)

        ctx.wrote(enviados)
        ctx.notes["caminhos_com_falha"] = falhas


def _asset_paths(ctx: base.JobContext) -> list[str]:
    rows = ctx.session.execute(
        select(Security.ticker, Security.type).where(Security.status == "active")
    )
    return [f"{PATH_BY_TYPE[kind]}/{ticker}" for ticker, kind in rows if kind in PATH_BY_TYPE]


if __name__ == "__main__":  # pragma: no cover - entrada de linha de comando
    base.main(run)
