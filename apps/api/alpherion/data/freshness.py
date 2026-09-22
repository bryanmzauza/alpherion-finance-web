"""Frescor dos dados: o pipeline rodou hoje? (site.md §3.6, plano §3.6)

O modo de falha mais perigoso de um pipeline não é o erro — é o **silêncio**. Um job que
para de rodar não quebra nada visível: a página continua no ar, com o número de ontem,
depois o de semana passada, e ninguém percebe até um leitor conferir na fonte. Por isso
o alerta olha para o que **deveria ter acontecido**, não para o que falhou.

As três regras (§3.6 do plano):

1. `cotahist_daily` não rodou com sucesso até as 21h de um dia útil.
2. `cvm_documents` falhou dois dias seguidos.
3. `b3_index_composition` falhou dois dias seguidos.

Dois dias, e não um: fonte externa cai, e acordar alguém por uma indisponibilidade de
uma tarde é o caminho mais curto para o alerta ser ignorado quando importar.

As regras são puras e testáveis aqui; quem lê o banco é o endpoint (`/v1/internal/...`,
para o Uptime Kuma) e o job que manda no Telegram. Os dois usam exatamente estas regras.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

#: Hora (Brasília) a partir da qual a cotação do dia já deveria estar carregada.
COTAHIST_DEADLINE_HOUR: Final = 21

#: Quantas falhas seguidas antes de alertar num job de fonte externa instável.
FAILURE_STREAK: Final = 2


class Level(StrEnum):
    OK = "ok"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class Run:
    """Uma execução de job, como `etl_runs` guarda."""

    job: str
    status: str
    started_at: dt.datetime
    period: dt.date | None = None


@dataclass(frozen=True, slots=True)
class Finding:
    job: str
    message: str


@dataclass(frozen=True, slots=True)
class Report:
    level: Level
    findings: list[Finding]
    checked_at: dt.datetime

    @property
    def ok(self) -> bool:
        return self.level is Level.OK

    def as_text(self) -> str:
        """Mensagem do Telegram: direta, com o nome do job e o que fazer."""
        if self.ok:
            return "Pipeline do Alpherion: tudo carregado."
        linhas = "\n".join(f"• {f.job}: {f.message}" for f in self.findings)
        return (
            "⚠️ Frescor dos dados do Alpherion\n"
            f"{linhas}\n\n"
            "Runbook: docs/runbooks/reprocessar-job.md"
        )


def is_business_day(day: dt.date) -> bool:
    """Sábado e domingo não têm pregão. Feriado da B3 não entra: o job pula sozinho
    (sem arquivo, `skipped`) e o alerta o trata como "não era para rodar"."""
    return day.weekday() < 5


def evaluate(runs: list[Run], *, now: dt.datetime) -> Report:
    """Aplica as três regras sobre as execuções recentes."""
    findings: list[Finding] = []

    finding = _check_cotahist(runs, now=now)
    if finding:
        findings.append(finding)

    for job in ("cvm_documents", "b3_index_composition"):
        streak = _check_streak(runs, job=job, now=now)
        if streak:
            findings.append(streak)

    return Report(
        level=Level.OK if not findings else Level.WARNING,
        findings=findings,
        checked_at=now,
    )


def _check_cotahist(runs: list[Run], *, now: dt.datetime) -> Finding | None:
    """Cotação do pregão de hoje, depois das 21h."""
    today = now.date()
    if not is_business_day(today) or now.hour < COTAHIST_DEADLINE_HOUR:
        return None

    de_hoje = [r for r in runs if r.job == "cotahist_daily" and r.started_at.date() == today]
    if any(r.status == "success" for r in de_hoje):
        return None
    if any(r.status == "skipped" for r in de_hoje):
        # Feriado ou arquivo ainda não publicado: o job disse que não havia o que fazer.
        return None
    return Finding(
        job="cotahist_daily",
        message=(
            f"sem carga bem-sucedida até as {COTAHIST_DEADLINE_HOUR}h de "
            f"{today:%d/%m/%Y} — a cotação do dia não entrou"
        ),
    )


def _check_streak(runs: list[Run], *, job: str, now: dt.datetime) -> Finding | None:
    """Falhas em dias distintos seguidos — não duas tentativas do mesmo dia."""
    falhas = sorted(
        {r.started_at.date() for r in runs if r.job == job and r.status == "failed"},
        reverse=True,
    )
    sucessos = {r.started_at.date() for r in runs if r.job == job and r.status == "success"}
    recentes = [day for day in falhas if day >= now.date() - dt.timedelta(days=FAILURE_STREAK)]
    # Um sucesso no meio zera a contagem: o problema se resolveu sozinho.
    seguidas = [day for day in recentes if day not in sucessos]

    if len(seguidas) < FAILURE_STREAK:
        return None
    return Finding(
        job=job,
        message=f"falhou em {len(seguidas)} dias seguidos (último: {seguidas[0]:%d/%m/%Y})",
    )
