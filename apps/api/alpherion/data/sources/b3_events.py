"""Eventos corporativos anunciados pelo emissor: proventos, desdobramentos, bonificações.

Alimenta `corporate_actions`, a aba Eventos da página do ativo, a `/agenda` e o fator de
ajuste do histórico (`transform/adjust.py`). É o que permite dizer "data-com em 12/11,
pagamento em 30/11, R$ 0,35 por ação" — fato com data e fonte, sem nenhuma projeção.

**Não é o que o usuário recebeu.** Isso vive em `app.income_events`, no schema do web.
Aqui é o anúncio público do emissor.

Fallback (site.md §3.5): quando o endpoint da B3 muda ou sai do ar, os proventos
aparecem também nos documentos da CVM (aviso aos acionistas, no IPE) e o job registra a
falha em `etl_runs` para o alerta de frescor. Evento que já está no banco não é apagado
por uma resposta vazia.

Fonte: `GetListedSupplementCompany`, **uma chamada por emissor** (`PETR`), que traz os
proventos em dinheiro, os eventos em ações (desdobramento, grupamento, bonificação) e as
subscrições de todos os papéis do emissor — cada item com o **ISIN** do papel, que é
como PETR3 e PETR4 se separam. Serve para companhia e para fundo (MXRF). O endpoint
anterior (`GetListedCashDividends`) pedia o *nome de pregão* e recebia o código do
emissor: voltava vazio para todo papel.

ADR-017: valor de provento é dado do emissor divulgado pela B3; a publicação segue a
mesma regra de licença dos outros dados da B3.
"""

from __future__ import annotations

import logging
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Final

import httpx

from alpherion.data.sources.b3_api import LISTED_BASE, fetch_json, field
from alpherion.data.sources.b3_api import build_url as _build_url

logger = logging.getLogger(__name__)

SUPPLEMENT_PATH: Final = "listedCompaniesProxy/CompanyCall/GetListedSupplementCompany"

#: Listas da resposta do emissor que viram `corporate_actions`.
EVENT_LISTS: Final = ("cashDividends", "stockDividends", "subscriptions")

#: Nome do evento na B3 (sem acento, minúsculo) → `corporate_actions.kind`.
KINDS: Final[dict[str, str]] = {
    "dividendo": "dividend",
    "dividendos": "dividend",
    "juros sobre capital proprio": "jcp",
    "jrs cap proprio": "jcp",
    "jcp": "jcp",
    "rendimento": "fii_income",
    "rendimentos": "fii_income",
    "amortizacao": "fii_income",
    "desdobramento": "split",
    "grupamento": "reverse_split",
    "bonificacao": "bonus",
    "bonificacao em acoes": "bonus",
    "subscricao": "subscription",
}

SOURCE: Final = "b3"


@dataclass(frozen=True, slots=True)
class CorporateEvent:
    """Um evento anunciado, pronto para `corporate_actions`."""

    ticker: str
    kind: str
    ex_date: date | None
    record_date: date | None
    payment_date: date | None
    value_per_share: Decimal | None
    ratio: str | None
    source: str = SOURCE


def _strip(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


def kind_of(label: Any) -> str | None:
    """Rótulo da B3 → tipo do evento. Rótulo novo vira `None` com aviso, não um chute."""
    if not label:
        return None
    key = _strip(str(label)).strip().lower()
    kind = KINDS.get(key)
    if kind is None:
        logger.warning("tipo de evento desconhecido na B3: %r", label)
    return kind


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    text = str(value).strip().replace(".", "").replace(",", ".")
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _date(value: Any) -> date | None:
    text = str(value or "").strip()
    for pattern in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:10], pattern).date()
        except ValueError:
            continue
    return None


def parse_event(record: dict[str, Any], *, ticker: str) -> CorporateEvent | None:
    """Um registro de provento ou evento. Sem tipo ou sem data, não vira evento."""
    kind = kind_of(field(record, "label", "typeStock", "corporateAction", "tipo"))
    if kind is None:
        return None
    ex_date = _date(field(record, "lastDatePrior", "dateApproval", "dataEx"))
    payment_date = _date(field(record, "paymentDate", "dataPagamento"))
    if ex_date is None and payment_date is None:
        return None  # evento sem data não entra na agenda nem no ajuste
    return CorporateEvent(
        ticker=ticker.strip().upper(),
        kind=kind,
        ex_date=ex_date,
        record_date=_date(field(record, "recordDate", "dataCom")),
        payment_date=payment_date,
        value_per_share=_decimal(field(record, "valueCash", "rate", "valor")),
        ratio=_ratio(record, kind),
    )


def _ratio(record: dict[str, Any], kind: str) -> str | None:
    """Proporção do evento, no formato que `transform/adjust.py` espera ("antigas:novas").

    A B3 publica um `factor` cujo sentido muda com o tipo (conferido com a Magalu:
    desdobramento de 2020 com fator 300 foi 1:4; grupamento de 2024 com fator 0,1 foi
    10:1):

    - desdobramento: percentual de ações **novas** — 300 → cada ação vira 4 → `1:4`;
    - grupamento: quantas ações cada uma **vira** — 0,1 → `1:0.1` (10 viram 1);
    - bonificação: percentual — 5 → `5%`.

    O que não dá para ler vira `None`, e o ajuste ignora o evento em vez de errar a série.
    """
    if kind not in {"split", "reverse_split", "bonus"}:
        return None
    raw = field(record, "factor", "ratio", "proporcao", "percentage")
    if raw is None:
        return None
    text = str(raw).strip()
    if ":" in text or text.endswith("%"):
        return text[:20]
    value = _decimal(text)
    if value is None or value <= 0:
        return None
    if kind == "bonus":
        return f"{value.normalize()}%"
    if kind == "reverse_split":
        return f"1:{value.normalize()}"
    return f"1:{(1 + value / Decimal(100)).normalize()}"


def parse_supplement(payload: Any, isin_to_ticker: dict[str, str]) -> list[CorporateEvent]:
    """Resposta do emissor → eventos, cada um no ticker dono do ISIN.

    ISIN que não está no nosso cadastro (papel deslistado, direito de subscrição) é
    ignorado: evento sem página não tem onde aparecer.
    """
    companies = payload if isinstance(payload, list) else [payload]
    events: list[CorporateEvent] = []
    for company in companies:
        if not isinstance(company, dict):
            continue
        for key in EVENT_LISTS:
            for record in company.get(key) or []:
                if not isinstance(record, dict):
                    continue
                isin = str(field(record, "isinCode", "assetIssued") or "").strip().upper()
                ticker = isin_to_ticker.get(isin)
                if ticker is None:
                    continue
                event = parse_event(record, ticker=ticker)
                if event is not None:
                    events.append(event)
    return events


def fetch_issuer_events(
    issuer: str,
    isin_to_ticker: dict[str, str],
    *,
    http: httpx.Client | None = None,
) -> list[CorporateEvent]:
    """Proventos e eventos anunciados de todos os papéis de um emissor (`PETR`)."""
    url = _build_url(
        LISTED_BASE,
        SUPPLEMENT_PATH,
        {"issuingCompany": issuer.strip().upper(), "language": "pt-br"},
    )
    events = parse_supplement(fetch_json(url, http=http), isin_to_ticker)
    logger.info("B3 eventos de %s: %d anúncios", issuer, len(events))
    return events
