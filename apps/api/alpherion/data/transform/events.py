"""Monta a agenda (`market_events`) a partir das três origens.

Regra única e inegociável: **a agenda só tem fato com data e fonte**. Nada de "espera-se
que", "provável", "prévia de resultado" ou estimativa de consenso — isso é opinião de
terceiro apresentada como calendário (§8.3 e ADR-018). Um item da agenda é: alguém
anunciou algo, com data, e o link prova.

As origens:

- **Proventos** (`corporate_actions`) geram até **dois** eventos: a data-com (último dia
  para ter direito) e o pagamento. São datas diferentes e decisões diferentes para o
  investidor, e é por isso que não podem virar um item só.
- **Documentos** (`company_documents`, do IPE): título, categoria, data e link. Sem
  resumo — o produto lista e linka, quem lê é o usuário, na CVM.
- **Agenda macro** (arquivo versionado): Copom, IPCA, IGP-M, FOMC, vencimento de opções.
  Cada item traz `source_url`; item sem fonte é descartado com aviso.

Os `id` são determinísticos (origem + chave natural), então reconstruir a agenda não
duplica nada e um evento que já estava lá mantém o mesmo id.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Final

logger = logging.getLogger(__name__)

#: Arquivo da agenda macro do ano, versionado junto com o código (§4.3 do plano).
MACRO_FILE: Final = Path(__file__).resolve().parent.parent / "content" / "agenda-macro.json"

#: Rótulo de cada tipo de provento na agenda. O texto é factual e igual para todos.
PROVENTO_LABELS: Final[dict[str, str]] = {
    "dividend": "Dividendo",
    "jcp": "Juros sobre capital próprio",
    "fii_income": "Rendimento",
    "split": "Desdobramento",
    "reverse_split": "Grupamento",
    "bonus": "Bonificação",
    "subscription": "Subscrição",
}

CASH_KINDS: Final = frozenset({"dividend", "jcp", "fii_income"})


@dataclass(frozen=True, slots=True)
class EventRow:
    """Uma linha de `market_events`."""

    id: str
    kind: str
    date: date
    title: str
    source: str
    ticker: str | None = None
    cvm_code: int | None = None
    payload: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class CorporateActionInput:
    """O que a agenda precisa de um provento anunciado."""

    id: int
    ticker: str
    kind: str
    ex_date: date | None
    payment_date: date | None
    value_per_share: Decimal | None
    ratio: str | None
    source: str


@dataclass(frozen=True, slots=True)
class DocumentInput:
    protocol: str
    cvm_code: int
    ticker: str | None
    category: str
    subject: str | None
    delivered_at: date


def from_corporate_actions(actions: Iterable[CorporateActionInput]) -> Iterator[EventRow]:
    """Data-com e pagamento — dois eventos por provento, quando as duas datas existem."""
    for action in actions:
        label = PROVENTO_LABELS.get(action.kind)
        if label is None:
            logger.warning("tipo de provento fora do vocabulário: %r", action.kind)
            continue
        payload: dict[str, Any] = {"tipo": label}
        if action.value_per_share is not None:
            payload["valor_por_acao"] = str(action.value_per_share)
        if action.ratio:
            payload["proporcao"] = action.ratio

        if action.ex_date is not None:
            yield EventRow(
                id=f"ca:{action.id}:ex",
                kind="ex_date" if action.kind in CASH_KINDS else "corporate",
                date=action.ex_date,
                ticker=action.ticker,
                title=f"{action.ticker} — {label} (data-com)",
                payload=payload,
                source=action.source,
            )
        if action.payment_date is not None and action.kind in CASH_KINDS:
            yield EventRow(
                id=f"ca:{action.id}:pg",
                kind="payment",
                date=action.payment_date,
                ticker=action.ticker,
                title=f"{action.ticker} — {label} (pagamento)",
                payload=payload,
                source=action.source,
            )


def from_documents(documents: Iterable[DocumentInput]) -> Iterator[EventRow]:
    """Um evento por documento entregue. Título, categoria e data — sem resumo (§8.3)."""
    for document in documents:
        prefix = f"{document.ticker} — " if document.ticker else ""
        yield EventRow(
            id=f"doc:{document.protocol}",
            kind="document",
            date=document.delivered_at,
            ticker=document.ticker,
            cvm_code=document.cvm_code,
            title=f"{prefix}{document.category}",
            payload={"categoria": document.category, "assunto": document.subject},
            source="cvm_ipe",
        )


def from_macro(path: Path | None = None) -> Iterator[EventRow]:
    """Agenda macro do arquivo versionado. Item sem data ou sem fonte é descartado."""
    file = path or MACRO_FILE
    if not file.exists():
        logger.info("agenda macro ainda não preenchida (%s)", file.name)
        return
    try:
        payload = json.loads(file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        logger.warning("agenda macro inválida: %s", error)
        return

    for item in payload.get("eventos", []):
        if not isinstance(item, dict):
            continue
        day = _parse_date(item.get("data"))
        title = str(item.get("titulo") or "").strip()
        source_url = str(item.get("source_url") or "").strip()
        if day is None or not title or not source_url:
            # Sem fonte não vai para a agenda: a regra do produto é fato com origem.
            logger.warning("item da agenda macro descartado (sem data, título ou fonte): %r", item)
            continue
        yield EventRow(
            id=f"macro:{day:%Y%m%d}:{_slug(title)}",
            kind="macro",
            date=day,
            title=title,
            payload={"fonte": source_url, "detalhe": item.get("detalhe")},
            source="agenda",
        )


def _parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    for pattern in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text[:10], pattern).date()
        except ValueError:
            continue
    return None


def _slug(text: str) -> str:
    cleaned = "".join(c if c.isalnum() else "-" for c in text.lower())
    return "-".join(part for part in cleaned.split("-") if part)[:60]


def build(
    actions: Iterable[CorporateActionInput],
    documents: Iterable[DocumentInput],
    *,
    macro_file: Path | None = None,
) -> list[EventRow]:
    """A agenda inteira, ordenada por data. Ids determinísticos: reconstruir é idempotente."""
    events = [
        *from_corporate_actions(actions),
        *from_documents(documents),
        *from_macro(macro_file),
    ]
    events.sort(key=lambda event: (event.date, event.id))
    return events
