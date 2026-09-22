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

CASH_DIVIDENDS_PATH: Final = "listedCompaniesProxy/CompanyCall/GetListedCashDividends"
SUPPLEMENT_PATH: Final = "listedCompaniesProxy/CompanyCall/GetListedSupplementCompany"

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
    """Proporção do evento, no formato que `transform/adjust.py` espera.

    A B3 publica desdobramento como fator ("200" para 1:2, em porcentagem de ações
    novas) em uns endpoints e como texto noutros. Só devolvemos o que dá para ler; o
    que não dá vira `None`, e o ajuste ignora o evento em vez de errar a série.
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
    # Percentual de ações novas por ação antiga: 200% = cada ação vira 3.
    return f"{value}%" if kind == "bonus" else f"1:{1 + value / Decimal(100)}"


def fetch_events(
    ticker: str,
    *,
    issuing_company: str | None = None,
    http: httpx.Client | None = None,
) -> list[CorporateEvent]:
    """Proventos e eventos anunciados de um papel.

    `issuing_company` é o código de quatro letras que a B3 usa (`PETR` para PETR4);
    quando não vem, é derivado do ticker.
    """
    code = (issuing_company or ticker[:4]).strip().upper()
    url = _build_url(
        LISTED_BASE,
        CASH_DIVIDENDS_PATH,
        {"language": "pt-br", "pageNumber": 1, "pageSize": 200, "tradingName": code},
    )
    payload = fetch_json(url, http=http)
    records = payload.get("results", []) if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        return []
    events = [
        event
        for record in records
        if isinstance(record, dict) and (event := parse_event(record, ticker=ticker)) is not None
    ]
    logger.info("B3 eventos de %s: %d anúncios", ticker, len(events))
    return events
