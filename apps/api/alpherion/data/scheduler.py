"""Agendamento dos jobs do worker `data` (site.md §3.4, plano §3.3).

É o `command` do serviço `data` no compose de produção: um laço que acorda a cada
minuto e dispara o que está na hora. Sem APScheduler e sem cron dentro do container —
a tabela `SCHEDULE` abaixo é a única fonte da verdade do "o que roda quando", e é ela
que o runbook cita.

**O agendamento é só um gatilho.** Quem garante que nada roda duas vezes é o lock de
`jobs/base.py`, não este laço: um restart do container no minuto exato não duplica
carga. Por isso disparar o mesmo job de novo à mão (runbook) é sempre seguro.

A ordem dentro do dia é o que importa mais que o horário exato:

    cotahist → eventos → ajuste → informes/demonstrações → indicadores → revalidação

Um indicador calculado antes do preço do dia sai com a cotação de ontem; a revalidação
antes dos indicadores publica a página velha. Os horários abaixo respeitam essa ordem
com folga, e os jobs de fonte externa ficam depois do fechamento do pregão (18h).

Alternativa prevista no plano: cron do host chamando `python -m alpherion.data.jobs.<job>`.
Os módulos continuam executáveis por conta própria — este arquivo não é pré-requisito
de nada, só a forma padrão de operar num VPS só.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final
from zoneinfo import ZoneInfo

from alpherion.data.jobs import (
    adjust_factors,
    b3_corporate_actions,
    b3_index_composition,
    b3_listing,
    bcb_series,
    coingecko_history,
    coingecko_prices,
    cotahist_daily,
    cvm_documents,
    cvm_fii_reports,
    cvm_statements,
    indicators_rebuild,
    revalidate_pages,
    tesouro_daily,
)
from alpherion.data.jobs.base import JobSkipped

logger = logging.getLogger(__name__)

#: Todo horário da tabela é de Brasília — o pregão e a publicação das fontes também.
TZ: Final = ZoneInfo("America/Sao_Paulo")

WEEKDAYS: Final = frozenset({0, 1, 2, 3, 4})  # segunda a sexta


@dataclass(frozen=True, slots=True)
class Scheduled:
    """Um job e quando ele roda."""

    name: str
    entrypoint: Callable[[], None]
    hour: int
    minute: int = 0
    #: Dias da semana (0 = segunda). Vazio = todos.
    weekdays: frozenset[int] = frozenset()
    #: Dia do mês; usado pelos jobs de carga pesada e baixa frequência.
    day_of_month: int | None = None

    def due(self, now: datetime) -> bool:
        if now.hour != self.hour or now.minute != self.minute:
            return False
        if self.weekdays and now.weekday() not in self.weekdays:
            return False
        return not (self.day_of_month is not None and now.day != self.day_of_month)


#: O que roda quando. Ordem do dia: preço → eventos → ajuste → fundamentos → derivados.
SCHEDULE: Final[tuple[Scheduled, ...]] = (
    # Manhã: cadastro e fontes que publicam cedo.
    Scheduled("b3_listing", b3_listing.run, hour=7, weekdays=WEEKDAYS),
    Scheduled("cvm_documents", cvm_documents.run, hour=7, minute=30),
    Scheduled("bcb_series", bcb_series.run, hour=8),
    Scheduled("b3_index_composition", b3_index_composition.run, hour=8, minute=30),
    # Depois do fechamento do pregão (18h).
    Scheduled("cotahist_daily", cotahist_daily.run, hour=19, minute=30, weekdays=WEEKDAYS),
    Scheduled("tesouro_daily", tesouro_daily.run, hour=20),
    Scheduled("b3_corporate_actions", b3_corporate_actions.run, hour=20, minute=30),
    Scheduled("adjust_factors", adjust_factors.run, hour=21, minute=30),
    # Fundamentos: mudam pouco, arquivos grandes.
    Scheduled("cvm_fii_reports", cvm_fii_reports.run, hour=5, day_of_month=15),
    Scheduled("cvm_statements", cvm_statements.run, hour=4, day_of_month=20),
    # Derivados, por último.
    Scheduled("indicators_rebuild", indicators_rebuild.run, hour=22),
    Scheduled("revalidate_pages", revalidate_pages.run, hour=22, minute=30),
    # Cripto (só dev até a fonte licenciada — ADR-017 trava em produção).
    *tuple(
        Scheduled("coingecko_prices", coingecko_prices.run, hour=hour) for hour in range(0, 24, 3)
    ),
    Scheduled("coingecko_history", coingecko_history.run, hour=23),
)


def run_due(now: datetime) -> list[str]:
    """Dispara o que está na hora. Devolve os nomes disparados (para o log e o teste)."""
    executados = []
    for entry in SCHEDULE:
        if not entry.due(now):
            continue
        executados.append(entry.name)
        try:
            entry.entrypoint()
        except JobSkipped as skipped:
            logger.info("%s pulado: %s", entry.name, skipped)
        except Exception:
            # Um job que falha não pode derrubar o agendador: o erro já está em
            # `etl_runs` e o alerta de frescor o pega.
            logger.exception("%s falhou; seguindo com os demais", entry.name)
    return executados


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger.info("agendador iniciado com %d entradas (%s)", len(SCHEDULE), TZ)
    ultimo_minuto: str | None = None
    while True:
        now = datetime.now(UTC).astimezone(TZ)
        minuto = now.strftime("%Y-%m-%dT%H:%M")
        if minuto != ultimo_minuto:
            ultimo_minuto = minuto
            run_due(now)
        # Acorda no começo do minuto seguinte: dormir 60 s fixos acumularia deriva.
        proximo = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
        time.sleep(max(1.0, (proximo - now).total_seconds()))


if __name__ == "__main__":  # pragma: no cover - entrada do container `data`
    main()
