"""Cadastro de ativos listados, eventos corporativos, demonstrações e documentos CVM."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from alpherion.db.base import Base
from alpherion.db.types import (
    CORPORATE_ACTION_KINDS,
    MARKETS,
    PERIOD_TYPES,
    SECURITY_TYPES,
    STATEMENT_TYPES,
    CreatedAt,
    Money,
    Price,
    Quantity,
    Ratio,
    Slug,
    Ticker,
    UpdatedAt,
    enum_check,
)


class Security(Base):
    """Todo papel negociado na B3: ação, unit, BDR, ETF, FII, fiagro.

    Origem: listagem da B3 + cadastro da CVM. `cvm_code` é o elo com as demonstrações
    (uma empresa tem N tickers: PETR3 e PETR4 dividem o mesmo `cvm_code`).
    """

    __tablename__ = "securities"
    __table_args__ = (
        enum_check("type", SECURITY_TYPES, name="type_valido"),
        enum_check("market", MARKETS, name="market_valido"),
        Index("ix_securities_cvm_code", "cvm_code"),
        Index("ix_securities_sector_slug", "sector_slug"),
        Index("ix_securities_type_status", "type", "status"),
        # Busca por nome no autocomplete (`/v1/assets/search`): sem acento, sem caixa.
        # `market.immutable_unaccent` (criada na migration) existe porque `unaccent()` é
        # STABLE, e o Postgres só aceita função IMMUTABLE em índice.
        Index(
            "ix_securities_company_name_trgm",
            text("market.immutable_unaccent(lower(company_name)) public.gin_trgm_ops"),
            postgresql_using="gin",
        ),
    )

    ticker: Mapped[Ticker] = mapped_column(primary_key=True)
    isin: Mapped[str | None] = mapped_column(String(12))
    cnpj: Mapped[str | None] = mapped_column(String(14))
    cvm_code: Mapped[int | None] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(10))
    market: Mapped[str] = mapped_column(String(2), server_default="br")

    company_name: Mapped[str] = mapped_column(String(200))
    trade_name: Mapped[str | None] = mapped_column(String(200))

    sector: Mapped[str | None] = mapped_column(String(120))
    subsector: Mapped[str | None] = mapped_column(String(120))
    segment: Mapped[str | None] = mapped_column(String(120))
    #: Slug do segmento B3, chave de `/setores/[slug]`.
    sector_slug: Mapped[str | None] = mapped_column(String(80))
    #: Novo Mercado, Nível 2, Nível 1, Bovespa Mais, tradicional.
    listing_segment: Mapped[str | None] = mapped_column(String(60))

    status: Mapped[str] = mapped_column(String(20), server_default="active")
    ri_url: Mapped[str | None] = mapped_column(Text)

    #: ETF: índice replicado (`indices.slug`), quando houver.
    etf_index_slug: Mapped[str | None] = mapped_column(String(80))
    #: BDR: quantos BDRs equivalem a uma ação da empresa no exterior.
    bdr_ratio: Mapped[str | None] = mapped_column(String(20))

    updated_at: Mapped[UpdatedAt]


class CorporateAction(Base):
    """Provento ou evento **anunciado pelo emissor** — não é o que o usuário recebeu.

    O que o usuário recebeu vive em `app.income_events` (schema do web). Aqui é o fato
    público: data-com, pagamento, valor por ação.
    """

    __tablename__ = "corporate_actions"
    __table_args__ = (
        enum_check("kind", CORPORATE_ACTION_KINDS, name="kind_valido"),
        Index("ix_corporate_actions_ticker_ex_date", "ticker", "ex_date"),
        Index("ix_corporate_actions_payment_date", "payment_date"),
        # Dedupe entre fontes (B3 e CVM anunciam o mesmo provento).
        Index(
            "uq_corporate_actions_evento",
            "ticker",
            "kind",
            "ex_date",
            "value_per_share",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticker: Mapped[Ticker] = mapped_column(ForeignKey("securities.ticker", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(20))
    #: Último dia para ter direito (o papel passa a negociar "ex" no dia seguinte).
    ex_date: Mapped[date | None] = mapped_column(Date)
    record_date: Mapped[date | None] = mapped_column(Date)
    payment_date: Mapped[date | None] = mapped_column(Date)
    value_per_share: Mapped[Price | None]
    #: Desdobramento/grupamento/bonificação: proporção ("1:2", "10%").
    ratio: Mapped[str | None] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[CreatedAt]


class FinancialStatement(Base):
    """DRE, balanço e DFC no formato longo da CVM (uma linha por conta).

    Guardar no formato da fonte é proposital: qualquer indicador é recalculável, e uma
    republicação (`version`) não exige refazer o modelo.
    """

    __tablename__ = "financial_statements"
    __table_args__ = (
        enum_check("statement", STATEMENT_TYPES, name="statement_valido"),
        enum_check("period_type", PERIOD_TYPES, name="period_type_valido"),
        Index("ix_financial_statements_lookup", "cvm_code", "statement", "period_end"),
    )

    cvm_code: Mapped[int] = mapped_column(Integer, primary_key=True)
    period_end: Mapped[date] = mapped_column(Date, primary_key=True)
    period_type: Mapped[str] = mapped_column(String(10), primary_key=True)
    statement: Mapped[str] = mapped_column(String(12), primary_key=True)
    consolidated: Mapped[bool] = mapped_column(primary_key=True)
    account_code: Mapped[str] = mapped_column(String(20), primary_key=True)

    account_name: Mapped[str] = mapped_column(String(300))
    value: Mapped[Money | None]
    #: Ordem da republicação na CVM; a leitura usa sempre a maior por período.
    version: Mapped[int] = mapped_column(Integer, server_default="1")
    updated_at: Mapped[UpdatedAt]


class CompanyFact(Base):
    """Fatos cadastrais da empresa que não estão nas demonstrações (FRE/FCA).

    Ações em circulação é o que transforma lucro em LPA e preço em valor de mercado.
    """

    __tablename__ = "company_facts"

    cvm_code: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference_date: Mapped[date] = mapped_column(Date, primary_key=True)
    shares_outstanding: Mapped[Quantity | None]
    free_float: Mapped[Ratio | None]
    capital_social: Mapped[Money | None]
    updated_at: Mapped[UpdatedAt]


class CompanyDocument(Base):
    """Documento entregue à CVM (dataset IPE): fato relevante, comunicado, aviso, ata.

    Guardamos **metadados e o link** para o documento na CVM — nunca o conteúdo: resumir
    fato relevante seria interpretação (site.md §8.3).
    """

    __tablename__ = "company_documents"
    __table_args__ = (
        Index("ix_company_documents_cvm_code_delivered", "cvm_code", "delivered_at"),
        Index("ix_company_documents_ticker_delivered", "ticker", "delivered_at"),
        Index("ix_company_documents_delivered_at", "delivered_at"),
    )

    #: Protocolo da CVM: identificador natural, garante idempotência da carga.
    protocol: Mapped[str] = mapped_column(String(40), primary_key=True)
    cvm_code: Mapped[int] = mapped_column(Integer)
    #: Ticker principal da empresa, para a página do ativo (pode faltar).
    ticker: Mapped[str | None] = mapped_column(String(20))
    category: Mapped[str] = mapped_column(String(120))
    type: Mapped[str | None] = mapped_column(String(120))
    subject: Mapped[str | None] = mapped_column(Text)
    delivered_at: Mapped[date] = mapped_column(Date)
    reference_date: Mapped[date | None] = mapped_column(Date)
    url: Mapped[str] = mapped_column(Text)
    created_at: Mapped[CreatedAt]


class Sector(Base):
    """Setor → subsetor → segmento da classificação B3, e os segmentos de FII.

    Tabela derivada (montada por job a partir de `securities`), mas materializada porque
    `/setores` é página indexável e precisa de nome estável e `lastmod`.
    """

    __tablename__ = "sectors"

    slug: Mapped[Slug] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(20))  # b3_segment | fii_segment
    sector: Mapped[str | None] = mapped_column(String(120))
    subsector: Mapped[str | None] = mapped_column(String(120))
    securities_count: Mapped[int] = mapped_column(Integer, server_default="0")
    updated_at: Mapped[UpdatedAt]
