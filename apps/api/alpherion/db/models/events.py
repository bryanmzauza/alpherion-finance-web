"""`market_events` — a agenda: tudo o que acontece num dia, numa tabela só.

Une três origens que nada têm em comum além da data: proventos anunciados
(`corporate_actions`), documentos entregues à CVM (`company_documents`) e a agenda macro
(arquivo versionado no repositório). É a base de `/agenda`, da tab Eventos de `/mercado`
e do calendário da carteira (v1.x).

**Tabela, não view materializada** (site.md §4.3 previa view): a agenda macro vem de um
arquivo, não do banco, e uma view não alcança arquivo. Tabela reconstruída pelo job
`market_events_rebuild` dá o mesmo resultado, com a vantagem de o rebuild ser parcial
por janela — e `REFRESH MATERIALIZED VIEW` reconstruiria a agenda inteira todo dia.

`payload` guarda o que a página mostra do evento (valor por ação, categoria do
documento, link) para que a listagem não precise de `JOIN` com três tabelas.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import Date, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from alpherion.db.base import Base
from alpherion.db.types import CreatedAt, enum_check

#: `ex_date` e `payment` vêm do mesmo provento em datas diferentes: o investidor
#: precisa saber quando comprar até (data-com) e quando o dinheiro cai (pagamento).
EVENT_KINDS = ("ex_date", "payment", "document", "macro", "corporate")


class MarketEvent(Base):
    __tablename__ = "market_events"
    __table_args__ = (
        enum_check("kind", EVENT_KINDS, name="kind_valido"),
        Index("ix_market_events_date_kind", "date", "kind"),
        Index("ix_market_events_ticker_date", "ticker", "date"),
    )

    #: Chave determinística montada da origem (`event_key`): reconstruir a agenda não
    #: duplica linha nem muda o id de um evento que já estava lá.
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    kind: Mapped[str] = mapped_column(String(12))
    date: Mapped[date] = mapped_column(Date)
    ticker: Mapped[str | None] = mapped_column(String(20))
    cvm_code: Mapped[int | None] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    source: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[CreatedAt]
