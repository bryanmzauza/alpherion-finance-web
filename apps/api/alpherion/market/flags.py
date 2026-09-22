"""A trava de licença do ADR-017, aplicada na saída da API.

Enquanto a licença da B3 não estiver registrada, **nenhum preço sai desta API** — e o
mesmo vale para cripto enquanto a fonte for o plano Demo do CoinGecko. A trava fica
aqui, num lugar só, e não espalhada pelos endpoints: uma rota nova herda o
comportamento certo sem que ninguém precise lembrar dele.

O que a trava faz não é esconder o campo: é devolvê-lo `null` **com o motivo**, que a
página mostra como "—" com explicação no tooltip. Sumir com o campo faria a página
parecer quebrada; devolver zero seria mentira; devolver `null` mudo faria o leitor achar
que o dado não existe. Dizer "cotação indisponível (fonte de preço não licenciada)" é a
única saída honesta — e é a mesma frase que o `indicators.py` já usa internamente.

O pipeline continua carregando tudo: processar não é distribuir (ADR-017). O que esta
camada controla é a **distribuição**.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel

from alpherion.settings import Settings

#: Motivos, na mesma redação que o `transform/indicators.py` grava em `missing_reasons`.
PRICE_REASON: Final = "cotação indisponível (fonte de preço não licenciada)"
CRYPTO_REASON: Final = "dado de cripto indisponível (fonte não licenciada)"

#: Campos que dependem do preço de mercado. A lista vale para qualquer modelo: o que
#: não tiver o campo simplesmente não é tocado.
PRICE_FIELDS: Final = frozenset(
    {
        "price",
        # `value` cobre o ponto de índice e o item da faixa; o item macro do BCB nunca
        # passa por aqui (a rota só trava os de origem B3 e cripto).
        "value",
        "close",
        "close_adjusted",
        "open",
        "high",
        "low",
        "change_day",
        "change_percent_day",
        "change_percent",
        "low_52w",
        "high_52w",
        "volume",
        "quote_date",
        "market_cap",
        "pe",
        "pb",
        "pvp",
        "ev_ebitda",
        "ev_ebit",
        "psr",
        "dy_12m",
    }
)


class Gate:
    """Decide o que pode sair. Construído uma vez por requisição, a partir do settings."""

    __slots__ = ("crypto_allowed", "prices_allowed")

    def __init__(self, settings: Settings) -> None:
        self.prices_allowed = settings.market_b3_prices_enabled
        self.crypto_allowed = settings.market_crypto_enabled

    def apply[Model: BaseModel](self, model: Model, *, crypto: bool = False) -> Model:
        """Devolve o modelo com os campos travados em `null` e o motivo registrado.

        O modelo é copiado, nunca mutado: o mesmo objeto pode vir de um cache em memória.
        """
        blocked = (crypto and not self.crypto_allowed) or (not crypto and not self.prices_allowed)
        if not blocked:
            return model

        reason = CRYPTO_REASON if crypto else PRICE_REASON
        fields = {name for name in PRICE_FIELDS if name in type(model).model_fields}
        if not fields:
            return model

        updates: dict[str, object] = dict.fromkeys(fields)
        if "missing_reasons" in type(model).model_fields:
            existing = dict(getattr(model, "missing_reasons", {}) or {})
            # Só marca o que de fato tinha valor: campo que já era `null` por falta de
            # dado mantém o motivo verdadeiro ("empresa não publicou DFP 2025").
            for name in fields:
                if getattr(model, name, None) is not None or name not in existing:
                    existing[name] = reason
            updates["missing_reasons"] = existing
        return model.model_copy(update=updates)

    def apply_all[Model: BaseModel](
        self, models: list[Model], *, crypto: bool = False
    ) -> list[Model]:
        return [self.apply(model, crypto=crypto) for model in models]
