"""Cliente dos endpoints JSON do site de listagem da B3.

Estes endpoints **não são documentados** (site.md §3.5): são os mesmos que as páginas
públicas da B3 chamam, e podem mudar sem aviso. Três consequências que este módulo
carrega para que os jobs não precisem saber delas:

1. **Parâmetro em base64.** A B3 põe o JSON dos parâmetros no *caminho* da URL,
   codificado em base64 — `.../GetInitialCompanies/eyJsYW5ndWFnZSI6...`. `encode()` faz
   isso num lugar só, e o job escreve um dicionário normal.
2. **Formato instável.** A resposta muda de maiúscula e de nome de campo entre
   endpoints. A leitura é por apelido, como nos CSVs da CVM, e campo que sumir vira
   `None` — nunca exceção que derruba a carga do dia.
3. **Fallback obrigatório.** Quando o endpoint muda ou sai do ar, `B3UnavailableError` sobe
   e o job decide: cadastro cai para o FRE/CVM, carteira de índice mantém a última
   conhecida e a página expõe a data (§3.2 do plano). Nunca inventamos dado.

ADR-017: baixar e processar não é distribuir. O que sai para o público depende de
`MARKET_B3_PRICES_ENABLED` e da licença registrada em `docs/fontes-de-dados.md`.
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any, Final

import httpx

from alpherion.data.sources.http import DEFAULT_TIMEOUT, USER_AGENT, SourceError, check_host

logger = logging.getLogger(__name__)

LISTED_BASE: Final = "https://sistemaswebb3-listados.b3.com.br"

#: A B3 pagina tudo; 120 é o maior tamanho que os endpoints aceitam sem erro.
PAGE_SIZE: Final = 120
MAX_PAGES: Final = 200


class B3UnavailableError(SourceError):
    """A B3 não respondeu ou mudou o formato — o job precisa usar o fallback."""


def encode(params: dict[str, Any]) -> str:
    """Parâmetros → segmento base64 do caminho, como a B3 espera."""
    raw = json.dumps(params, separators=(",", ":"), ensure_ascii=False)
    return base64.b64encode(raw.encode()).decode()


def build_url(base: str, path: str, params: dict[str, Any]) -> str:
    return f"{base}/{path.strip('/')}/{encode(params)}"


def fetch_json(url: str, *, http: httpx.Client | None = None) -> Any:
    """GET que devolve JSON ou levanta `B3UnavailableError`.

    Resposta em HTML (página de erro, bloqueio por WAF) é falha explícita: deixá-la
    virar "lista vazia" apagaria a carteira de um índice inteiro no banco.
    """
    check_host(url)

    def _get(session: httpx.Client) -> httpx.Response:
        return session.get(url, headers={"Accept": "application/json"})

    if http is not None:
        response = _get(http)
    else:
        with httpx.Client(timeout=DEFAULT_TIMEOUT, headers={"User-Agent": USER_AGENT}) as session:
            response = _get(session)

    if response.status_code != httpx.codes.OK:
        raise B3UnavailableError(f"{url}: HTTP {response.status_code}")
    try:
        payload = response.json()
        # Alguns endpoints (`GetListedSupplementCompany`, `GetIndustryClassification`)
        # devolvem o JSON **codificado duas vezes**: uma string cujo conteúdo é o JSON.
        # Lido como veio, vira um `str` e todo evento some sem erro nenhum.
        if isinstance(payload, str) and payload.lstrip().startswith(("[", "{")):
            payload = json.loads(payload)
        return payload
    except ValueError as error:
        raise B3UnavailableError(f"{url}: resposta não é JSON (endpoint mudou?)") from error


def fetch_pages(
    base: str,
    path: str,
    params: dict[str, Any],
    *,
    http: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """Percorre a paginação da B3 e devolve todos os registros.

    O corte é pelo total que a própria resposta declara (`page.totalPages`), com um teto
    duro: endpoint que passe a devolver sempre a mesma página não vira laço infinito.
    """
    records: list[dict[str, Any]] = []
    page_number = 1
    while page_number <= MAX_PAGES:
        payload = fetch_json(
            build_url(base, path, {**params, "pageNumber": page_number, "pageSize": PAGE_SIZE}),
            http=http,
        )
        results, total_pages = _unwrap(payload)
        records.extend(results)
        if page_number >= total_pages:
            break
        page_number += 1
    else:
        logger.warning("%s: parou no teto de %d páginas", path, MAX_PAGES)
    return records


def _unwrap(payload: Any) -> tuple[list[dict[str, Any]], int]:
    """Separa registros e total de páginas das várias formas que a B3 usa."""
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)], 1
    if not isinstance(payload, dict):
        raise B3UnavailableError(f"formato inesperado: {type(payload).__name__}")

    results = payload.get("results") or payload.get("Results") or []
    if not isinstance(results, list):
        raise B3UnavailableError("campo 'results' não é lista")

    page = payload.get("page") or payload.get("Page") or {}
    total_pages = page.get("totalPages") if isinstance(page, dict) else None
    return (
        [item for item in results if isinstance(item, dict)],
        int(total_pages)
        if isinstance(total_pages, int | str) and str(total_pages).isdigit()
        else 1,
    )


def field(record: dict[str, Any], *names: str) -> Any:
    """Valor do primeiro campo presente, ignorando caixa (a B3 varia entre endpoints)."""
    lowered = {key.lower(): value for key, value in record.items()}
    for name in names:
        value = lowered.get(name.lower())
        if value not in (None, "", "-"):
            return value
    return None
