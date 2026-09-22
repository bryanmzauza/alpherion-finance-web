"""Garantias estruturais do schema `market` — rodam sem banco (só metadata)."""

from __future__ import annotations

import pytest
from sqlalchemy import Table

from alpherion.db import models
from alpherion.db.base import SCHEMA, Base
from alpherion.db.models.indicators import PRICE_BASED
from alpherion.db.partitions import FIRST_YEAR, partition_name

TABLES: dict[str, Table] = Base.metadata.tables


def test_todas_as_tabelas_no_schema_market() -> None:
    """Nenhuma tabela da API pode cair no schema `app` (do web) nem no `public`."""
    assert TABLES, "nenhuma tabela registrada — o import de models quebrou?"
    for name, table in TABLES.items():
        assert table.schema == SCHEMA, f"{name} está fora do schema {SCHEMA}"


def test_tabelas_do_site_md_existem() -> None:
    """As tabelas previstas em site.md §4.3 e no ADR-018 (portal)."""
    esperadas = {
        # §4.3
        "securities",
        "daily_quotes",
        "corporate_actions",
        "financial_statements",
        "company_facts",
        "indicators_daily",
        "fii_reports",
        "treasury_bonds",
        "treasury_daily",
        "macro_series",
        "crypto_assets",
        "crypto_daily",
        "crypto_metrics",
        "etl_runs",
        "data_sources",
        # ADR-018 (portal de mercado)
        "indices",
        "index_daily",
        "index_compositions",
        "company_documents",
        "sectors",
    }
    presentes = {t.name for t in TABLES.values()}
    assert presentes >= esperadas, f"faltam: {sorted(esperadas - presentes)}"


def test_daily_quotes_particionada_por_ano() -> None:
    """Sem `PARTITION BY`, a tabela vira um monólito de ~40 anos de pregão."""
    quotes = TABLES[f"{SCHEMA}.daily_quotes"]
    assert quotes.dialect_options["postgresql"]["partition_by"] == "RANGE (date)"
    # A chave de partição tem de estar na PK (exigência do Postgres).
    assert {c.name for c in quotes.primary_key.columns} == {"ticker", "date"}


def test_nenhuma_coluna_de_dinheiro_usa_float() -> None:
    """Preço e valor em float acumulam erro de arredondamento e viram número errado na tela."""
    suspeitas = ("price", "close", "open", "high", "low", "value", "volume", "nav", "cap")
    # Contagens e posições têm nome parecido, mas são inteiros de verdade.
    excecoes = {"market_cap_rank", "securities_count", "shareholders", "trades"}
    for table in TABLES.values():
        for column in table.columns:
            if column.name in excecoes or not any(s in column.name for s in suspeitas):
                continue
            tipo = column.type.__class__.__name__
            assert tipo in {"Numeric", "String", "Text", "Date", "DateTime"}, (
                f"{table.name}.{column.name} usa {tipo}; dinheiro é Numeric"
            )


def test_indicadores_de_preco_existem_na_tabela() -> None:
    """`PRICE_BASED` alimenta a flag do ADR-017: se um nome sumir, a flag para de cobrir."""
    colunas = {c.name for c in TABLES[f"{SCHEMA}.indicators_daily"].columns}
    assert colunas >= PRICE_BASED, f"não são colunas: {sorted(PRICE_BASED - colunas)}"


def test_data_sources_registra_verificacao_de_termos() -> None:
    """ADR-017: job em produção só roda para fonte com `terms_checked_at` preenchido."""
    colunas = {c.name for c in TABLES[f"{SCHEMA}.data_sources"].columns}
    assert colunas >= {"terms_checked_at", "attribution", "license_note"}


@pytest.mark.parametrize(
    ("year", "esperado"), [(1986, "daily_quotes_1986"), (2026, "daily_quotes_2026")]
)
def test_nome_da_particao(year: int, esperado: str) -> None:
    assert partition_name("daily_quotes", year) == esperado


def test_primeiro_ano_do_cotahist() -> None:
    """A série histórica da B3 começa em 1986 — o backfill cria as partições daí."""
    assert FIRST_YEAR == 1986


def test_modelos_exportados() -> None:
    """`models.__all__` é o que o Alembic enxerga: um modelo fora dele não vira migration."""
    for nome in models.__all__:
        assert hasattr(models, nome), f"{nome} está em __all__ mas não foi importado"
