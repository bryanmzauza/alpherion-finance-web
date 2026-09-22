"""Criptoativos (CoinGecko).

ADR-017: o plano Demo não permite uso comercial — em produção isto fica atrás de
`MARKET_CRYPTO_ENABLED` até haver fonte licenciada. A estrutura não muda com a troca
de fonte: `id` é o identificador do provedor.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from alpherion.db.base import Base
from alpherion.db.types import Money, Price, Quantity, Ratio, Slug, UpdatedAt


class CryptoAsset(Base):
    """`id` é o slug do provedor (ex.: `bitcoin`) e a URL de `/cripto/[id]`."""

    __tablename__ = "crypto_assets"

    id: Mapped[Slug] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(120))
    #: Stablecoin entra no engine com fator próprio (não é "cripto" para risco).
    is_stablecoin: Mapped[bool] = mapped_column(server_default="false")
    market_cap_rank: Mapped[int | None]
    updated_at: Mapped[UpdatedAt]


class CryptoDaily(Base):
    """Fechamento diário em BRL e USD — base do histórico e do engine."""

    __tablename__ = "crypto_daily"
    __table_args__ = (Index("ix_crypto_daily_date", "date"),)

    id: Mapped[str] = mapped_column(
        String(80), ForeignKey("crypto_assets.id", ondelete="CASCADE"), primary_key=True
    )
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    price_brl: Mapped[Price | None]
    price_usd: Mapped[Price | None]
    market_cap_brl: Mapped[Money | None]
    volume_brl: Mapped[Money | None]
    updated_at: Mapped[UpdatedAt]


class CryptoMetric(Base):
    """Snapshot horário: o que a página mostra "agora" (24h, 7d, ATH, dominância)."""

    __tablename__ = "crypto_metrics"
    __table_args__ = (Index("ix_crypto_metrics_captured_at", "captured_at"),)

    id: Mapped[str] = mapped_column(
        String(80), ForeignKey("crypto_assets.id", ondelete="CASCADE"), primary_key=True
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    price_brl: Mapped[Price | None]
    price_usd: Mapped[Price | None]
    change_24h: Mapped[Ratio | None]
    change_7d: Mapped[Ratio | None]
    market_cap_brl: Mapped[Money | None]
    volume_24h_brl: Mapped[Money | None]
    circulating_supply: Mapped[Quantity | None]
    max_supply: Mapped[Quantity | None]
    ath_brl: Mapped[Price | None]
    ath_date: Mapped[date | None] = mapped_column(Date)
    #: Dominância do BTC no mercado total (só preenchida para o bitcoin).
    btc_dominance: Mapped[Ratio | None]
