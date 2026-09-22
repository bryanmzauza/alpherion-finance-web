"""Download do COTAHIST da B3 (série histórica de cotações).

A B3 publica três recortes do mesmo arquivo: diário (`COTAHIST_D<ddmmaaaa>.ZIP`),
mensal e **anual** (`COTAHIST_A<aaaa>.ZIP`). O job diário usa o do dia; o backfill usa
o anual, que é a mesma estrutura com o ano inteiro.

O parsing fica em `transform/cotahist_parser.py`; aqui só o download e a escolha da URL.

ADR-017: baixar e processar não é distribuir — publicar é. O que sai para o público
depende de `MARKET_B3_PRICES_ENABLED` e da licença registrada em `docs/fontes-de-dados.md`.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Final

import httpx

from alpherion.data.sources.http import download, extract_single
from alpherion.data.transform.cotahist_parser import Quote, parse_lines

logger = logging.getLogger(__name__)

BASE_URL: Final = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist"

#: O arquivo anual passa de 200 MB descomprimido; o diário fica na casa de poucos MB.
MAX_DOWNLOAD_BYTES: Final = 120 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES: Final = 900 * 1024 * 1024

#: O arquivo é latin-1 (é anterior ao UTF-8 e nunca mudou).
ENCODING: Final = "latin-1"


def daily_url(day: date) -> str:
    return f"{BASE_URL}/COTAHIST_D{day:%d%m%Y}.ZIP"


def yearly_url(year: int) -> str:
    return f"{BASE_URL}/COTAHIST_A{year}.ZIP"


@contextmanager
def _downloaded(url: str, http: httpx.Client | None) -> Iterator[Path]:
    """Baixa e extrai em diretório temporário, apagado ao sair.

    Não guardamos o arquivo bruto: o que interessa vai para o banco, e manter cópia de
    dado de terceiro no disco só aumenta a superfície (§7.5 e ADR-017).
    """
    with TemporaryDirectory(prefix="alpherion-cotahist-") as tmp:
        tmp_path = Path(tmp)
        zip_path = download(url, tmp_path / "cotahist.zip", max_bytes=MAX_DOWNLOAD_BYTES, http=http)
        yield extract_single(zip_path, tmp_path, max_bytes=MAX_UNCOMPRESSED_BYTES)


def fetch_day(day: date, *, http: httpx.Client | None = None) -> Iterator[Quote]:
    """Cotações de um pregão. Consome o gerador **dentro** do `with`."""
    yield from _fetch(daily_url(day), http)


def fetch_year(year: int, *, http: httpx.Client | None = None) -> Iterator[Quote]:
    """Cotações de um ano inteiro (backfill)."""
    yield from _fetch(yearly_url(year), http)


def _fetch(url: str, http: httpx.Client | None) -> Iterator[Quote]:
    with _downloaded(url, http) as txt_path, txt_path.open(encoding=ENCODING) as file:
        count = 0
        for quote in parse_lines(file):
            count += 1
            yield quote
        logger.info("%s: %d cotações à vista", url, count)
