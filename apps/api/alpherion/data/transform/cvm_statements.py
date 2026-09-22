"""Demonstrações financeiras da CVM (DFP anual e ITR trimestral) no formato longo.

O pacote de um ano traz um CSV por demonstração e por escopo — `..._BPA_con_2025.csv`,
`..._DRE_ind_2025.csv` e assim por diante. Todos têm o mesmo cabeçalho, uma linha por
conta do plano padronizado:

    CNPJ_CIA;DT_REFER;VERSAO;DENOM_CIA;CD_CVM;GRUPO_DFP;MOEDA;ESCALA_MOEDA;
    ORDEM_EXERC;DT_INI_EXERC;DT_FIM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA;ST_CONTA_FIXA

Quatro regras que o formato impõe e que decidem se o indicador sai certo:

- **`ESCALA_MOEDA`**. O valor vem em `MIL` na maioria das companhias e em `UNIDADE` em
  algumas. Normalizamos para reais na leitura; sem isso o P/L de uma empresa sai mil
  vezes errado e o de outra, certo — o pior tipo de bug de dado.
- **`ORDEM_EXERC`**. Cada arquivo traz o exercício corrente (`ÚLTIMO`) e o comparativo
  do anterior (`PENÚLTIMO`). Só o corrente é carregado: o anterior já veio, completo,
  no pacote do seu próprio ano, e com a versão da época.
- **`VERSAO`**. A companhia republica a demonstração; a CVM mantém as duas no arquivo.
  A leitura fica sempre com a maior versão por (companhia, período, demonstração,
  escopo) — `latest_versions()`.
- **Consolidado × individual**. Vêm em arquivos diferentes (`_con_`/`_ind_`) e não se
  misturam: a página mostra o consolidado quando existe, e o individual quando a
  companhia não consolida.

Formato longo, igual ao da fonte (site.md §4.3): guardar a conta como a CVM publica é o
que permite recalcular qualquer indicador depois sem refazer a carga.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Final

from alpherion.data.transform.csv_fields import Row, read_rows, strip_accents

logger = logging.getLogger(__name__)

#: Trecho do nome do arquivo → `financial_statements.statement`.
#: `DVA` (valor adicionado) fica de fora: não alimenta nenhum indicador do v1.
STATEMENT_BY_FILE: Final[dict[str, str]] = {
    "_bpa_": "bp_ativo",
    "_bpp_": "bp_passivo",
    "_dre_": "dre",
    "_dfc_mi_": "dfc",
    "_dfc_md_": "dfc",
    "_dra_": "dra",
    "_dmpl_": "dmpl",
}

#: `ESCALA_MOEDA` → multiplicador para chegar a reais.
SCALES: Final[dict[str, int]] = {"UNIDADE": 1, "MIL": 1_000, "MILHAO": 1_000_000}

CURRENT_PERIOD: Final = "ULTIMO"
ANNUAL: Final = "annual"
QUARTERLY: Final = "quarterly"

#: Chave de dedupe por versão: identifica "a mesma conta do mesmo período".
_Key = tuple[int, date, str, str, bool, str]


@dataclass(frozen=True, slots=True)
class StatementRow:
    """Uma conta de uma demonstração, já em reais e pronta para `financial_statements`."""

    cvm_code: int
    period_end: date
    period_type: str
    statement: str
    consolidated: bool
    account_code: str
    account_name: str
    value: Decimal | None
    version: int
    #: Início do exercício — só nas demonstrações de fluxo (DRE, DFC). `None` no balanço.
    period_start: date | None

    @property
    def key(self) -> _Key:
        return (
            self.cvm_code,
            self.period_end,
            self.period_type,
            self.statement,
            self.consolidated,
            self.account_code,
        )

    @property
    def months(self) -> int | None:
        """Duração aproximada do exercício, em meses — separa o trimestre do acumulado."""
        if self.period_start is None:
            return None
        days = (self.period_end - self.period_start).days + 1
        return round(days / 30.44)


def statement_of(filename: str) -> str | None:
    """`dfp_cia_aberta_DRE_con_2025.csv` → `dre`. Arquivo que não interessa vira `None`."""
    name = filename.lower()
    for marker, statement in STATEMENT_BY_FILE.items():
        if marker in name:
            return statement
    return None


def is_consolidated(filename: str) -> bool | None:
    name = filename.lower()
    if "_con_" in name:
        return True
    if "_ind_" in name:
        return False
    return None


def _scale(raw: str | None) -> int:
    if raw is None:
        return 1
    key = strip_accents(raw).strip().upper()
    if key not in SCALES:
        logger.warning("escala de moeda desconhecida: %r (tratada como unidade)", raw)
        return 1
    return SCALES.get(key, 1)


def parse_row(
    row: Row,
    *,
    statement: str,
    consolidated: bool,
    period_type: str,
) -> StatementRow | None:
    """Converte uma linha do CSV. Linha incompleta ou de exercício anterior vira `None`."""
    order = strip_accents(row.get("ordem_exerc") or "").strip().upper()
    if order and order != CURRENT_PERIOD:
        return None

    currency = (row.get("moeda") or "REAL").strip().upper()
    if strip_accents(currency) != "REAL":
        logger.warning("linha em moeda %r ignorada (só carregamos reais)", currency)
        return None

    cvm_code = row.integer("cd_cvm", "codigo_cvm")
    period_end = row.date("dt_fim_exerc", "dt_refer", "data_referencia")
    account_code = row.get("cd_conta", "codigo_conta")
    if cvm_code is None or period_end is None or account_code is None:
        return None

    value = row.decimal("vl_conta", "valor_conta")
    scale = _scale(row.get("escala_moeda"))
    return StatementRow(
        cvm_code=cvm_code,
        period_end=period_end,
        period_type=period_type,
        statement=statement,
        consolidated=consolidated,
        account_code=account_code[:20],
        account_name=(row.text("ds_conta", "descricao_conta", limit=300) or account_code),
        value=value * scale if value is not None else None,
        version=row.integer("versao") or 1,
        period_start=row.date("dt_ini_exerc"),
    )


def parse_file(path: Path, *, period_type: str) -> Iterator[StatementRow]:
    """Lê um CSV do pacote. A demonstração e o escopo vêm do **nome do arquivo**.

    É a própria CVM que codifica os dois no nome; `GRUPO_DFP` traz a mesma informação
    por extenso e em formato livre, o que o torna pior como chave.
    """
    statement = statement_of(path.name)
    consolidated = is_consolidated(path.name)
    if statement is None or consolidated is None:
        logger.debug("ignorado %s (não é demonstração que carregamos)", path.name)
        return
    for row in read_rows(path):
        parsed = parse_row(
            row, statement=statement, consolidated=consolidated, period_type=period_type
        )
        if parsed is not None:
            yield parsed


def latest_versions(rows: Iterable[StatementRow]) -> list[StatementRow]:
    """Uma linha por conta: a de maior `version` (republicação vence a original)."""
    best: dict[_Key, StatementRow] = {}
    for row in rows:
        current = best.get(row.key)
        if current is None or row.version > current.version:
            best[row.key] = row
    return list(best.values())


def full_year_only(rows: Iterable[StatementRow]) -> Iterator[StatementRow]:
    """Descarta o acumulado parcial: na DFP interessa o exercício de 12 meses.

    Balanço não tem início de exercício (`months is None`) e passa direto — é uma foto
    da data, não um fluxo.
    """
    for row in rows:
        months = row.months
        if months is None or 11 <= months <= 13:
            yield row
