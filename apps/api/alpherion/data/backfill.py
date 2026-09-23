"""Carga inicial do schema `market` (plano §3.3).

Dois perfis:

- **`--sample`**: o suficiente para desenvolver e para gravar vídeo — 20 ações, 10 FIIs,
  5 ETFs, 5 BDRs, 3 índices, o Tesouro inteiro (é pequeno), as 20 maiores cripto, 3 anos
  de cotação e 90 dias de IPE. Roda em minutos e deixa um banco de poucas centenas de MB.
- **`--full`**: o que roda uma vez em produção antes da tag `v0.2.0`. Leva horas, baixa
  dezenas de GB e é reexecutável por etapa — cada job é idempotente e registra `etl_runs`.

**A ordem aqui não é estética.** Cadastro antes de tudo (sem `securities` não há a que
prender cotação, evento ou indicador); preço e eventos antes do ajuste; ajuste antes dos
indicadores; indicadores antes de revalidar a página. Rodar fora de ordem não corrompe
nada — os jobs são idempotentes —, só produz uma passagem com dado incompleto.

Interrompeu no meio? Rode de novo: o que já entrou é sobrescrito com o mesmo valor.
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Final

from alpherion.data.jobs import (
    adjust_factors,
    b3_corporate_actions,
    b3_index_composition,
    b3_listing,
    bcb_series,
    coingecko_history,
    coingecko_prices,
    cotahist_daily,
    cvm_companies,
    cvm_company_facts,
    cvm_documents,
    cvm_fii_reports,
    cvm_statements,
    indicators_rebuild,
    market_events_rebuild,
    tesouro_daily,
)
from alpherion.data.jobs.base import JobSkipped

logger = logging.getLogger(__name__)

#: Amostra de desenvolvimento. Papéis líquidos e conhecidos, para que qualquer tela
#: tenha dado de verdade — inclusive as de ETF e BDR, que costumam ficar de fora.
SAMPLE_STOCKS: Final = (
    "PETR4", "PETR3", "VALE3", "ITUB4", "BBDC4", "ABEV3", "BBAS3", "B3SA3", "WEGE3", "ITSA4",
    "MGLU3", "LREN3", "RENT3", "SUZB3", "JBSS3", "RADL3", "EQTL3", "RAIL3", "CSAN3", "GGBR4",
)  # fmt: skip
SAMPLE_FIIS: Final = (
    "MXRF11", "HGLG11", "KNRI11", "XPML11", "VISC11",
    "BTLG11", "HGRU11", "KNCR11", "IRDM11", "VGIP11",
)  # fmt: skip
SAMPLE_ETFS: Final = ("BOVA11", "SMAL11", "IVVB11", "DIVO11", "XFIX11")
SAMPLE_BDRS: Final = ("AAPL34", "MSFT34", "AMZO34", "GOGL34", "TSLA34")
SAMPLE_INDICES: Final = ("ibovespa", "ifix", "idiv")

SAMPLE_YEARS: Final = 3
SAMPLE_CRYPTO: Final = 20
SAMPLE_IPE_DAYS: Final = 90

#: Produção: a DFP a partir daqui cobre o histórico que os indicadores usam.
FULL_FIRST_STATEMENT_YEAR: Final = 2010
#: COTAHIST completo começa em 1986, mas o produto mostra no máximo "máx" de 10 anos;
#: o backfill completo carrega 20, que cobre CAGR e gráficos longos com folga.
FULL_QUOTE_YEARS: Final = 20


@dataclass(frozen=True, slots=True)
class Profile:
    """Quanto carregar. `tickers` vazio = tudo o que a fonte trouxer."""

    name: str
    quote_years: int
    statement_years: int
    ipe_days: int
    crypto_top: int
    tickers: tuple[str, ...] = ()
    indices: tuple[str, ...] = ()
    #: Cripto entra nos dois perfis, mas em produção o job para na trava do ADR-017
    #: (fonte sem termos verificados) e a etapa aparece como pulada, com o motivo.
    crypto: bool = True


SAMPLE: Final = Profile(
    name="sample",
    quote_years=SAMPLE_YEARS,
    statement_years=SAMPLE_YEARS,
    ipe_days=SAMPLE_IPE_DAYS,
    crypto_top=SAMPLE_CRYPTO,
    tickers=(*SAMPLE_STOCKS, *SAMPLE_FIIS, *SAMPLE_ETFS, *SAMPLE_BDRS),
    indices=SAMPLE_INDICES,
)

FULL: Final = Profile(
    name="full",
    quote_years=FULL_QUOTE_YEARS,
    statement_years=date.today().year - FULL_FIRST_STATEMENT_YEAR,
    ipe_days=365,
    crypto_top=100,
)


@dataclass
class Step:
    """Uma etapa do backfill, com o nome que aparece no log e no runbook."""

    name: str
    action: Callable[[], None]
    notes: str = ""


@dataclass
class Report:
    """O que rodou, o que foi pulado e o que falhou — impresso no fim."""

    done: list[str] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failed


def plan(profile: Profile) -> list[Step]:
    """As etapas, na ordem em que precisam rodar."""
    today = date.today()
    years = [today.year - offset for offset in range(profile.quote_years)]
    statement_years = [today.year - 1 - offset for offset in range(profile.statement_years)]
    tickers = list(profile.tickers) or None

    steps: list[Step] = [
        # 1. Cadastro: sem ele não há a que prender nada.
        Step("b3_listing", b3_listing.run, "ações, units, ETFs, BDRs e FIIs"),
        Step("cvm_companies", cvm_companies.run, "razão social, CNPJ e código CVM"),
        # 2. Fundamentos.
        *[
            Step(f"cvm_statements:{year}", _bind(cvm_statements.run, year=year))
            for year in statement_years
        ],
        Step("cvm_company_facts", cvm_company_facts.run, "capital social (FRE)"),
        Step("cvm_fii_reports", cvm_fii_reports.run),
        Step(
            "cvm_documents",
            _bind(cvm_documents.run, since=today - timedelta(days=profile.ipe_days)),
            f"IPE dos últimos {profile.ipe_days} dias",
        ),
        # 3. Fontes liberadas de preço.
        Step("tesouro_daily", _bind(tesouro_daily.run, full=True), "série completa do Tesouro"),
        Step("bcb_series", _bind(bcb_series.run, full=True), "séries do SGS desde o início"),
        # 4. Preço e eventos da B3 (ADR-017: em produção, só com licença).
        *[
            Step(
                f"cotahist:{year}",
                _bind(cotahist_daily.run_year, year=year, only=tickers),
                "ano inteiro" if tickers is None else f"{len(tickers)} papéis",
            )
            for year in years
        ],
        Step("b3_corporate_actions", _bind(b3_corporate_actions.run, tickers=tickers)),
        Step(
            "b3_index_composition",
            _bind(
                b3_index_composition.run,
                slugs=list(profile.indices) or None,
                years=profile.quote_years,
            ),
        ),
    ]

    if profile.crypto:
        steps += [
            Step("coingecko_prices", _bind(coingecko_prices.run, top=profile.crypto_top)),
            Step("coingecko_history", _bind(coingecko_history.run, days=365)),
        ]

    # 5. Derivados, sempre por último e nesta ordem.
    steps += [
        Step("adjust_factors", _bind(adjust_factors.run, tickers=tickers)),
        Step("indicators_rebuild", _bind(indicators_rebuild.run, tickers=tickers)),
        Step("market_events_rebuild", market_events_rebuild.run),
    ]
    return steps


def _bind(action: Callable[..., None], **kwargs: object) -> Callable[[], None]:
    def call() -> None:
        action(**kwargs)

    return call


def run(profile: Profile, *, only: list[str] | None = None, dry_run: bool = False) -> Report:
    """Roda o backfill. `only` limita às etapas cujo nome comece pelo que for passado."""
    report = Report()
    for step in plan(profile):
        if only and not any(step.name.startswith(prefix) for prefix in only):
            continue
        if dry_run:
            logger.info("[dry-run] %s %s", step.name, f"({step.notes})" if step.notes else "")
            report.done.append(step.name)
            continue

        logger.info("==> %s %s", step.name, f"({step.notes})" if step.notes else "")
        try:
            step.action()
        except JobSkipped as skipped:
            report.skipped.append((step.name, str(skipped)))
        except Exception as failure:  # o backfill segue: cada etapa é independente
            logger.exception("%s falhou", step.name)
            report.failed.append((step.name, f"{type(failure).__name__}: {failure}"))
        else:
            report.done.append(step.name)
    _print(report)
    return report


def _print(report: Report) -> None:
    logger.info("concluídas: %d", len(report.done))
    for name, reason in report.skipped:
        logger.info("pulada: %s — %s", name, reason)
    for name, reason in report.failed:
        logger.error("FALHOU: %s — %s", name, reason)
    if report.failed:
        logger.error(
            "reexecute só o que falhou: python -m alpherion.data.backfill --etapa %s",
            " --etapa ".join(name for name, _ in report.failed),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Carga inicial do schema market.")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--sample", action="store_true", help="amostra para desenvolvimento")
    grupo.add_argument("--full", action="store_true", help="carga completa (produção, horas)")
    parser.add_argument("--etapa", action="append", default=None, help="só estas etapas")
    parser.add_argument("--dry-run", action="store_true", help="lista as etapas e sai")
    args = parser.parse_args()

    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")
    report = run(
        SAMPLE if args.sample else FULL,
        only=args.etapa,
        dry_run=args.dry_run,
    )
    if not report.ok:
        raise SystemExit(1)


if __name__ == "__main__":  # pragma: no cover - entrada de linha de comando
    main()
