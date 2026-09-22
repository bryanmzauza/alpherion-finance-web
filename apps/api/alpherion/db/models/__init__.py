"""Modelos do schema `market` (site.md §4.3).

Dono: o worker `data` escreve (Alembic roda com DATA_DATABASE_URL); a API só lê.
Importar tudo aqui é o que faz o autogenerate do Alembic enxergar as tabelas.

Convenções (§4 do site.md):
- dinheiro e preço: `Numeric` (nunca float — erro de arredondamento vira número errado na tela);
- quantidade de ativo: `Numeric(28, 10)` (cripto tem 8+ casas);
- datas de mercado: `Date` (o dado é diário); carimbos de tempo: `timestamptz`;
- toda tabela alimentada por job tem a fonte registrada em `data_sources`.
"""

from __future__ import annotations

from alpherion.db.models.company import (
    CompanyDocument,
    CompanyFact,
    CorporateAction,
    FinancialStatement,
    Sector,
    Security,
)
from alpherion.db.models.crypto import CryptoAsset, CryptoDaily, CryptoMetric
from alpherion.db.models.etl import DataSource, EtlRun
from alpherion.db.models.events import MarketEvent
from alpherion.db.models.fii import FiiReport
from alpherion.db.models.index import IndexComposition, IndexDaily, MarketIndex
from alpherion.db.models.indicators import IndicatorDaily
from alpherion.db.models.macro import MacroSeries
from alpherion.db.models.quotes import DailyQuote
from alpherion.db.models.treasury import TreasuryBond, TreasuryDaily

__all__ = [
    "CompanyDocument",
    "CompanyFact",
    "CorporateAction",
    "CryptoAsset",
    "CryptoDaily",
    "CryptoMetric",
    "DailyQuote",
    "DataSource",
    "EtlRun",
    "FiiReport",
    "FinancialStatement",
    "IndexComposition",
    "IndexDaily",
    "IndicatorDaily",
    "MacroSeries",
    "MarketEvent",
    "MarketIndex",
    "Sector",
    "Security",
    "TreasuryBond",
    "TreasuryDaily",
]
