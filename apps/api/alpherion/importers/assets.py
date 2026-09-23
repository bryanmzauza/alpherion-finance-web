"""Do que o arquivo diz ("PETR4", "Tesouro IPCA+ 2035", "BTC") ao ativo do cadastro.

Os parsers não tocam no banco: devolvem uma `AssetHint`. Depois do parse, a rota junta
todas as dicas, consulta o schema `market` **uma vez** (`Catalog`) e resolve. Assim os
parsers são funções puras, testáveis com fixture, e a consulta não cresce por linha.

O `symbol` do `AssetRef` é a chave de mercado do ativo — ticker, id do CoinGecko ou slug
do título —, que é o que o `web` manda de volta para a valorização.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Final, Literal, Protocol

from alpherion.importers.models import AssetClass, AssetRef
from alpherion.importers.tabular import norm

HintKind = Literal["ticker", "treasury", "fixed_income", "crypto"]


@dataclass(frozen=True, slots=True)
class AssetHint:
    kind: HintKind
    code: str
    name: str | None = None
    maturity: date | None = None
    #: Classe sugerida pelo contexto (aba "BDR" da posição, coluna "classe" do CSV).
    class_hint: AssetClass | None = None


@dataclass(frozen=True, slots=True)
class SecurityInfo:
    ticker: str
    type: str
    name: str


@dataclass(frozen=True, slots=True)
class TreasuryInfo:
    slug: str
    name: str
    maturity: date


@dataclass(frozen=True, slots=True)
class CryptoInfo:
    id: str
    symbol: str
    name: str
    is_stablecoin: bool


class Catalog(Protocol):
    """O pedaço do schema `market` de que a resolução precisa."""

    async def securities(self, tickers: set[str]) -> Mapping[str, SecurityInfo]: ...
    async def treasury(self) -> list[TreasuryInfo]: ...
    async def crypto(self, symbols: set[str]) -> Mapping[str, CryptoInfo]: ...


@dataclass
class MemoryCatalog:
    """Catálogo em memória (testes e dublês)."""

    securities_: dict[str, SecurityInfo] = field(default_factory=dict)
    treasury_: list[TreasuryInfo] = field(default_factory=list)
    crypto_: dict[str, CryptoInfo] = field(default_factory=dict)

    async def securities(self, tickers: set[str]) -> Mapping[str, SecurityInfo]:
        return {t: s for t, s in self.securities_.items() if t in tickers}

    async def treasury(self) -> list[TreasuryInfo]:
        return self.treasury_

    async def crypto(self, symbols: set[str]) -> Mapping[str, CryptoInfo]:
        return {s: c for s, c in self.crypto_.items() if s in symbols}


SECURITY_CLASS: Final[dict[str, AssetClass]] = {
    "stock": "stock_br",
    "unit": "stock_br",
    "fii": "fii",
    "fiagro": "fii",
    "etf": "etf_br",
    "bdr": "bdr",
}

#: Nomes antigos (e o jeito que algumas corretoras ainda escrevem) → nome atual compacto.
TREASURY_ALIASES: Final = {
    "ltn": "tesouroprefixado",
    "ntnf": "tesouroprefixadocomjurossemestrais",
    "lft": "tesouroselic",
    "ntnbprincipal": "tesouroipca",
    "ntnb": "tesouroipcacomjurossemestrais",
    "ntnc": "tesouroigpmcomjurossemestrais",
    "tesouroigpcomjurossemestrais": "tesouroigpmcomjurossemestrais",
    "tesourorenda": "tesourorendaaposentadoriaextra",
    "tesourorendamaisaposentadoriaextra": "tesourorendaaposentadoriaextra",
    "tesourorendamais": "tesourorendaaposentadoriaextra",
    "tesourorendaplus": "tesourorendaaposentadoriaextra",
    "tesouroeducamais": "tesouroeduca",
}


def _compact(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", norm(text))


def _treasury_key(name: str) -> str:
    """Nome do título → chave compacta ("Tesouro IPCA+" → "tesouroipca"), com apelidos."""
    key = re.sub(r"[^a-z0-9]", "", norm(name))
    return TREASURY_ALIASES.get(key, key)


def _split_treasury(text: str) -> tuple[str, int | None]:
    """Separa o ano do vencimento: `Tesouro IPCA+ 2035` → (`Tesouro IPCA+`, 2035)."""
    match = re.search(r"(19|20)\d{2}\b", text)
    if not match:
        return text.strip(), None
    return (text[: match.start()] + text[match.end() :]).strip(" -"), int(match.group(0))


def ticker_class_guess(ticker: str) -> AssetClass | None:
    """Palpite pelo sufixo, para ticker fora do cadastro (11 é ambíguo: FII, ETF ou unit)."""
    suffix = re.sub(r"^[A-Z0-9]{4}", "", ticker)
    if suffix in {"3", "4", "5", "6", "7", "8"}:
        return "stock_br"
    if suffix in {"31", "32", "33", "34", "35", "39"}:
        return "bdr"
    return None


@dataclass
class Resolver:
    """Resolve dicas em lote. `warnings` junta um aviso por ativo desconhecido."""

    securities: Mapping[str, SecurityInfo]
    treasury: list[TreasuryInfo]
    crypto: Mapping[str, CryptoInfo]
    warnings: dict[str, str] = field(default_factory=dict)

    @classmethod
    async def load(cls, catalog: Catalog, hints: Iterable[AssetHint]) -> Resolver:
        hints = list(hints)
        tickers = {h.code for h in hints if h.kind == "ticker"}
        symbols = {h.code.upper() for h in hints if h.kind == "crypto"}
        needs_treasury = any(h.kind == "treasury" for h in hints)
        return cls(
            securities=await catalog.securities(tickers) if tickers else {},
            treasury=await catalog.treasury() if needs_treasury else [],
            crypto=await catalog.crypto(symbols) if symbols else {},
        )

    def resolve(self, hint: AssetHint) -> AssetRef:
        if hint.kind == "ticker":
            return self._ticker(hint)
        if hint.kind == "treasury":
            return self._treasury(hint)
        if hint.kind == "crypto":
            return self._crypto(hint)
        name = (hint.name or hint.code).strip()[:200]
        return AssetRef(
            symbol=(hint.code or name).strip().upper()[:60],
            name=name,
            asset_class="fixed_income",
            market_ref="none",
        )

    def _ticker(self, hint: AssetHint) -> AssetRef:
        info = self.securities.get(hint.code)
        if info is not None:
            return AssetRef(
                symbol=info.ticker,
                name=info.name,
                asset_class=SECURITY_CLASS.get(info.type, hint.class_hint or "other"),
                market_ref="ticker",
            )
        asset_class = hint.class_hint or ticker_class_guess(hint.code) or "other"
        self.warnings[hint.code] = (
            f"{hint.code} não está no cadastro de mercado; confira a classe ({asset_class}) "
            "antes de confirmar"
        )
        return AssetRef(
            symbol=hint.code,
            name=(hint.name or hint.code)[:200],
            asset_class=asset_class,
            market_ref="ticker",
            known=False,
        )

    def _treasury(self, hint: AssetHint) -> AssetRef:
        base, year = _split_treasury(hint.code)
        key = _treasury_key(base)
        matches = [
            bond
            for bond in self.treasury
            if _treasury_key(bond.name) == key
            and (
                bond.maturity == hint.maturity
                if hint.maturity
                else year is not None and bond.maturity.year == year
            )
        ]
        if len(matches) == 1:
            bond = matches[0]
            return AssetRef(
                symbol=bond.slug,
                name=f"{bond.name} {bond.maturity.year}",
                asset_class="treasury",
                market_ref="treasury_slug",
            )
        label = hint.code.strip()
        self.warnings[label] = f"título {label} não foi encontrado no cadastro do Tesouro"
        return AssetRef(
            symbol=_compact(label).upper()[:60] or "TESOURO",
            name=label[:200],
            asset_class="treasury",
            market_ref="none",
            known=False,
        )

    def _crypto(self, hint: AssetHint) -> AssetRef:
        symbol = hint.code.upper()
        info = self.crypto.get(symbol)
        if info is not None:
            return AssetRef(
                symbol=info.id,
                name=info.name,
                asset_class="stablecoin" if info.is_stablecoin else "crypto",
                market_ref="coingecko_id",
            )
        self.warnings[symbol] = f"{symbol} não está no cadastro de cripto"
        return AssetRef(
            symbol=symbol,
            name=hint.name or symbol,
            asset_class="crypto",
            market_ref="none",
            known=False,
        )
