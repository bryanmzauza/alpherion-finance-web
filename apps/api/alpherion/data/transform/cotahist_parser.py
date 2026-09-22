"""Parser do COTAHIST da B3 (arquivo posicional de 245 bytes por registro).

Layout oficial: "LAYOUT DO ARQUIVO – COTAÇÕES HISTÓRICAS", revisão 01 de 13/04/2017
(`SeriesHistoricas_Layout.pdf`). Três tipos de registro: `00` header, `01` cotação,
`99` trailer.

Decisões que o formato impõe:

- **Posições são 1-based no documento** e viram fatias 0-based aqui uma única vez, na
  tabela `FIELDS`. Nenhum número mágico espalhado pelo parser.
- **Preços vêm sem vírgula**, com 2 casas implícitas (`(11)V99`): `0000000004120` é
  R$ 41,20. Convertemos com `Decimal`, nunca `float` — o arquivo tem 40 anos de pregão
  e erro de arredondamento aqui vira número errado na página.
- **`FATCOT` (fator de cotação)** é 1 ou 1000: papéis cotados por lote de mil (comum
  antes de 2000) têm preço mil vezes maior. Normalizamos para preço unitário; sem isso
  o histórico longo de um papel antigo dá um salto artificial.
- **Filtramos para o mercado à vista** (`TPMERC` 010 e 020) e para os `CODBDI` de papel
  negociável. Opção, termo e futuro ficam de fora do v1: não é o que as páginas mostram,
  e entram como ruído no cálculo de liquidez.

ADR-017: este parser roda em desenvolvimento e no pipeline; publicar o resultado depende
da licença da B3 (`MARKET_B3_PRICES_ENABLED`).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Final

logger = logging.getLogger(__name__)

RECORD_SIZE: Final = 245
HEADER: Final = "00"
QUOTE: Final = "01"
TRAILER: Final = "99"

#: (posição inicial, posição final) do documento, 1-based e inclusivas.
FIELDS: Final[dict[str, tuple[int, int]]] = {
    "tipreg": (1, 2),
    "data": (3, 10),
    "codbdi": (11, 12),
    "codneg": (13, 24),
    "tpmerc": (25, 27),
    "nomres": (28, 39),
    "especi": (40, 49),
    "prazot": (50, 52),
    "modref": (53, 56),
    "preabe": (57, 69),
    "premax": (70, 82),
    "premin": (83, 95),
    "premed": (96, 108),
    "preult": (109, 121),
    "preofc": (122, 134),
    "preofv": (135, 147),
    "totneg": (148, 152),
    "quatot": (153, 170),
    "voltot": (171, 188),
    "preexe": (189, 201),
    "indopc": (202, 202),
    "datven": (203, 210),
    "fatcot": (211, 217),
    "ptoexe": (218, 230),
    "codisi": (231, 242),
    "dismes": (243, 245),
}

#: Mercado à vista e fracionário. O fracionário é o mesmo papel, em lote menor.
SPOT_MARKETS: Final = frozenset({"010", "020"})

#: CODBDI de papel que queremos: lote padrão, FII e ETF/fiagro entram como lote padrão.
#: 12 = fundos imobiliários; 14 = certificados de investimento (fiagro, alguns ETFs).
TRADEABLE_BDI: Final = frozenset({"02", "12", "14"})

#: Especificações que não são papel negociável para a nossa finalidade.
SKIP_ESPECI_PREFIXES: Final = ("DIR", "BNS", "RCT", "REC")


class CotahistError(ValueError):
    """Arquivo fora do layout — nunca silenciar: significa que a B3 mudou o formato."""


@dataclass(frozen=True, slots=True)
class Quote:
    """Uma linha de cotação já normalizada (preço unitário, em reais)."""

    ticker: str
    date: date
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    average: Decimal | None
    close: Decimal
    #: Quantidade de títulos negociados.
    quantity: int
    #: Volume financeiro em R$ — é o que mede liquidez.
    volume: Decimal
    trades: int
    isin: str | None
    especi: str
    codbdi: str
    tpmerc: str


def _slice(line: str, field: str) -> str:
    start, end = FIELDS[field]
    return line[start - 1 : end]


def _price(raw: str) -> Decimal | None:
    """`(11)V99` → Decimal com 2 casas. Zero vira None: no COTAHIST é ausência."""
    digits = raw.strip()
    if not digits or not digits.isdigit():
        return None
    value = Decimal(digits) / 100
    return value or None


def _int(raw: str) -> int:
    digits = raw.strip()
    return int(digits) if digits.isdigit() else 0


def _date(raw: str) -> date:
    return datetime.strptime(raw.strip(), "%Y%m%d").date()


def parse_line(line: str) -> Quote | None:
    """Converte um registro `01` em `Quote`; devolve None para o que não interessa.

    Retorna None (sem erro) quando o registro é header/trailer, de outro mercado
    (opção, termo, futuro) ou de um papel que não publicamos (direito, recibo, bônus).
    """
    if len(line) < RECORD_SIZE:
        raise CotahistError(f"registro com {len(line)} bytes; o layout exige {RECORD_SIZE}")

    tipreg = _slice(line, "tipreg")
    if tipreg in (HEADER, TRAILER):
        return None
    if tipreg != QUOTE:
        raise CotahistError(f"tipo de registro desconhecido: {tipreg!r}")

    tpmerc = _slice(line, "tpmerc").strip()
    codbdi = _slice(line, "codbdi").strip()
    if tpmerc not in SPOT_MARKETS or codbdi not in TRADEABLE_BDI:
        return None

    especi = _slice(line, "especi").strip()
    if especi.startswith(SKIP_ESPECI_PREFIXES):
        return None

    close = _price(_slice(line, "preult"))
    if close is None:
        # Sem preço de fechamento não há linha: o papel não negociou.
        return None

    # Fator de cotação: 1000 = preço por lote de mil ações (papéis antigos).
    fatcot = _int(_slice(line, "fatcot")) or 1

    def unit(value: Decimal | None) -> Decimal | None:
        return None if value is None else value / fatcot

    isin = _slice(line, "codisi").strip()

    unit_close = unit(close)
    if unit_close is None:  # pragma: no cover - close não é None neste ponto
        return None

    return Quote(
        ticker=_slice(line, "codneg").strip(),
        date=_date(_slice(line, "data")),
        open=unit(_price(_slice(line, "preabe"))),
        high=unit(_price(_slice(line, "premax"))),
        low=unit(_price(_slice(line, "premin"))),
        average=unit(_price(_slice(line, "premed"))),
        close=unit_close,
        quantity=_int(_slice(line, "quatot")),
        # VOLTOT é (16)V99: o volume financeiro já vem em reais, sem fator de cotação.
        volume=_price(_slice(line, "voltot")) or Decimal(0),
        trades=_int(_slice(line, "totneg")),
        isin=isin or None,
        especi=especi,
        codbdi=codbdi,
        tpmerc=tpmerc,
    )


def parse_lines(lines: Iterable[str]) -> Iterator[Quote]:
    """Percorre o arquivo inteiro, pulando o que não é cotação à vista.

    Gerador de propósito: o COTAHIST de um ano tem centenas de milhares de linhas e o
    arquivo completo passa de 1 GB — nada disso cabe em memória de uma vez.
    """
    for number, raw in enumerate(lines, start=1):
        line = raw.rstrip("\r\n")
        if not line.strip():
            continue
        try:
            quote = parse_line(line)
        except CotahistError:
            logger.exception("COTAHIST: linha %d fora do layout", number)
            raise
        if quote is not None:
            yield quote
