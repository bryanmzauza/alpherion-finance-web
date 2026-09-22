"""Cadastro dos papéis listados na B3: ações, units, ETFs, BDRs e FIIs.

É o que dá ao `securities` o que a CVM não tem — **ticker**, setor/subsetor/segmento da
classificação B3, segmento de listagem (Novo Mercado, Nível 2…), razão de BDR e índice
replicado por ETF. Sem isso não existe `/acoes/PETR4` nem `/setores/[slug]`.

Endpoints não documentados (`b3_api`): mudam sem aviso. O fallback está no job — cadastro
pelo FRE/CVM, que tem razão social, CNPJ e código CVM, mas não tem ticker; enquanto a B3
não volta, o cadastro existente continua valendo e nada é apagado (§3.2 do plano).

O tipo do papel sai do **final do ticker**, que é a convenção da própria B3 e não muda:
3/4/5/6/7/8 ação, 11 unit ou ETF ou FII (desempatado pelo segmento), 31–35 BDR, 39/33
BDR não patrocinado. Quando a classificação não fecha, o papel fica `other` em vez de
entrar numa classe errada — uma página de ação com um FII dentro é pior que uma classe
a menos.

ADR-017: só o cadastro vem daqui; preço é COTAHIST e depende da licença.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass, replace
from typing import Any, Final

import httpx

from alpherion.data.sources.b3_api import LISTED_BASE, fetch_pages, field

logger = logging.getLogger(__name__)

COMPANIES_PATH: Final = "listedCompaniesProxy/CompanyCall/GetInitialCompanies"
FUNDS_PATH: Final = "fundsProxy/fundsCall/GetListedFundsSIG"
BDRS_PATH: Final = "listedCompaniesProxy/CompanyCall/GetInitialCompanies"

#: `typeFund` dos endpoints de fundos da B3.
FUND_TYPES: Final[dict[str, int]] = {"fii": 7, "etf": 20, "fiagro": 34}

#: Sufixo numérico do ticker → tipo do papel (`securities.type`).
TICKER_SUFFIXES: Final[dict[str, str]] = {
    "3": "stock",
    "4": "stock",
    "5": "stock",
    "6": "stock",
    "7": "stock",
    "8": "stock",
    "31": "bdr",
    "32": "bdr",
    "33": "bdr",
    "34": "bdr",
    "35": "bdr",
    "39": "bdr",
}

TICKER_RE: Final = re.compile(r"^[A-Z]{4}\d{1,2}[A-Z]?$")


@dataclass(frozen=True, slots=True)
class ListedSecurity:
    """Um papel listado, pronto para `securities`."""

    ticker: str
    type: str
    company_name: str
    trade_name: str | None = None
    cnpj: str | None = None
    cvm_code: int | None = None
    isin: str | None = None
    sector: str | None = None
    subsector: str | None = None
    segment: str | None = None
    sector_slug: str | None = None
    listing_segment: str | None = None
    #: ETF: slug do índice replicado. BDR: quantos BDRs equivalem a uma ação lá fora.
    etf_index_slug: str | None = None
    bdr_ratio: str | None = None


def slugify(*parts: str | None) -> str | None:
    """`Petróleo, Gás e Biocombustíveis` → `petroleo-gas-e-biocombustiveis`."""
    text = " ".join(part for part in parts if part)
    if not text.strip():
        return None
    normalized = unicodedata.normalize("NFD", text)
    ascii_only = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_only.lower()).strip("-")
    return slug[:80] or None


def type_of(ticker: str, *, hint: str | None = None) -> str:
    """Tipo do papel pelo sufixo do ticker; `hint` resolve o 11, que é ambíguo.

    11 é unit (SANB11), ETF (BOVA11) e FII (MXRF11) ao mesmo tempo — só a origem do
    registro desempata. Sem dica, fica `other`: melhor uma classe a menos do que um FII
    listado como ação.
    """
    code = ticker.strip().upper()
    if not TICKER_RE.match(code):
        return "other"
    digits = "".join(c for c in code[4:] if c.isdigit())
    if digits == "11":
        return hint if hint in {"unit", "etf", "fii", "fiagro"} else "other"
    if len(digits) == 2 and digits in TICKER_SUFFIXES:
        return TICKER_SUFFIXES[digits]
    return TICKER_SUFFIXES.get(digits[:1], "other") if digits else "other"


def _digits(value: Any) -> str | None:
    if value is None:
        return None
    only = "".join(c for c in str(value) if c.isdigit())
    return only or None


def _int(value: Any) -> int | None:
    digits = _digits(value)
    return int(digits) if digits else None


def parse_company(record: dict[str, Any]) -> Iterator[ListedSecurity]:
    """Uma companhia pode ter vários tickers (`PETR3`, `PETR4`) no mesmo registro."""
    name = field(record, "companyName", "company_name", "nomeEmpresa")
    codes = field(record, "codes", "code", "issuingCompany")
    if not name or not codes:
        return
    tickers = codes if isinstance(codes, list) else [codes]

    sector = field(record, "sectorName", "setorAtividade", "industryClassification")
    subsector = field(record, "subSectorName", "subsector")
    segment = field(record, "segmentName", "segment")
    for raw_ticker in tickers:
        ticker = str(raw_ticker).strip().upper()
        # Vindo do endpoint de companhias, um ticker terminado em 11 é unit — ETF e FII
        # têm endpoint próprio.
        kind = type_of(ticker, hint="unit")
        yield ListedSecurity(
            ticker=ticker,
            type=kind,
            company_name=str(name).strip()[:200],
            trade_name=(str(field(record, "tradingName") or "").strip() or None),
            cnpj=_digits(field(record, "cnpj", "cnpjCompany")),
            cvm_code=_int(field(record, "codeCVM", "cvmCode")),
            isin=(str(field(record, "isin") or "").strip() or None),
            sector=sector,
            subsector=subsector,
            segment=segment,
            sector_slug=slugify(sector, subsector, segment),
            listing_segment=field(record, "market", "listingSegment", "segmentoListagem"),
        )


def parse_fund(record: dict[str, Any], *, kind: str) -> ListedSecurity | None:
    """Registro dos endpoints de fundos (FII, ETF, fiagro)."""
    ticker = field(record, "acronym", "acronymFund", "ticker", "fundTicker")
    name = field(record, "companyName", "fundName", "tradingName", "nameFund")
    if not ticker or not name:
        return None
    code = str(ticker).strip().upper()
    # Os endpoints de fundo devolvem o código sem o dígito (`MXRF`), e é o `11` que
    # identifica a cota negociada.
    if code.isalpha():
        code = f"{code}11"
    segment = field(record, "segment", "typeFund", "classificacao")
    return ListedSecurity(
        ticker=code,
        type=type_of(code, hint=kind),
        company_name=str(name).strip()[:200],
        cnpj=_digits(field(record, "cnpj", "documentNumber")),
        segment=segment,
        sector_slug=slugify(kind, segment),
        etf_index_slug=slugify(field(record, "indexName", "benchmark")) if kind == "etf" else None,
    )


def parse_bdr(record: dict[str, Any]) -> ListedSecurity | None:
    security = next(parse_company(record), None)
    if security is None:
        return None
    ratio = field(record, "bdrRatio", "ratio", "proporcao")
    return replace(
        security,
        type="bdr",
        bdr_ratio=str(ratio).strip()[:20] if ratio else None,
    )


def fetch_companies(*, http: httpx.Client | None = None) -> list[ListedSecurity]:
    """Ações e units listadas."""
    records = fetch_pages(LISTED_BASE, COMPANIES_PATH, {"language": "pt-br"}, http=http)
    securities = [s for record in records for s in parse_company(record)]
    logger.info("B3 listagem: %d papéis de %d companhias", len(securities), len(records))
    return securities


def fetch_funds(kind: str, *, http: httpx.Client | None = None) -> list[ListedSecurity]:
    """FIIs, ETFs ou fiagros listados."""
    if kind not in FUND_TYPES:
        raise ValueError(f"tipo de fundo desconhecido: {kind!r}")
    records = fetch_pages(
        LISTED_BASE,
        FUNDS_PATH,
        {"language": "pt-br", "typeFund": FUND_TYPES[kind]},
        http=http,
    )
    funds = [fund for record in records if (fund := parse_fund(record, kind=kind)) is not None]
    logger.info("B3 listagem (%s): %d fundos", kind, len(funds))
    return funds


def fetch_bdrs(*, http: httpx.Client | None = None) -> list[ListedSecurity]:
    records = fetch_pages(
        LISTED_BASE, BDRS_PATH, {"language": "pt-br", "typeBDR": "PATROCINADO"}, http=http
    )
    bdrs = [bdr for record in records if (bdr := parse_bdr(record)) is not None]
    logger.info("B3 listagem: %d BDRs", len(bdrs))
    return bdrs
