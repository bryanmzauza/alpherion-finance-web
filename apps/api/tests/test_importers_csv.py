"""CSV genérico de movimentações (`importers/generic_csv.py`)."""

from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal

import pytest

from alpherion.importers import generic_csv
from alpherion.importers.assets import CryptoInfo, MemoryCatalog, SecurityInfo, TreasuryInfo
from alpherion.importers.base import build_preview
from alpherion.importers.models import ImportPreview
from alpherion.importers.tabular import ImportFileError

HOJE = date(2026, 9, 23)
CATALOGO = MemoryCatalog(
    securities_={"PETR4": SecurityInfo("PETR4", "stock", "PETROBRAS")},
    treasury_=[TreasuryInfo("ipca-2035-05-15", "Tesouro IPCA+", date(2035, 5, 15))],
    crypto_={"BTC": CryptoInfo("bitcoin", "BTC", "Bitcoin", False)},
)

MODELO = """data;tipo;ativo;quantidade;preco;taxas;classe
12/03/2026;compra;PETR4;100;38,52;4,90;acao
2026-03-13;venda;PETR4;50;40;0;
01/04/2026;compra;Tesouro IPCA+ 2035;0,5;3.100,00;;tesouro
02/04/2026;compra;BTC;0,01;350000;;cripto
03/04/2026;compra;ETH;1;15000;;
04/04/2026;doacao;PETR4;1;1;;
05/04/2099;compra;PETR4;1;1;;
06/04/2026;compra;PETR4;-1;1;;
07/04/2026;compra;PETR4;1;1;;fundo exotico
"""


def _preview(text: str) -> ImportPreview:
    result = generic_csv.parse_file(text.encode("utf-8"), 1, HOJE)
    return asyncio.run(build_preview([result], CATALOGO))


def test_modelo() -> None:
    preview = _preview(MODELO)
    [arquivo] = preview.files
    assert (arquivo.kind, arquivo.rows_in, arquivo.rows_ok) == ("csv", 9, 5)
    linhas = [
        (t.asset.symbol, t.asset.asset_class, t.side, t.quantity, t.price, t.fees)
        for t in preview.transactions
    ]
    assert linhas == [
        ("PETR4", "stock_br", "buy", Decimal("100"), Decimal("38.52"), Decimal("4.90")),
        ("PETR4", "stock_br", "sell", Decimal("50"), Decimal("40"), Decimal("0")),
        ("ipca-2035-05-15", "treasury", "buy", Decimal("0.5"), Decimal("3100.00"), Decimal("0")),
        ("bitcoin", "crypto", "buy", Decimal("0.01"), Decimal("350000"), Decimal("0")),
        ("ETH", "crypto", "buy", Decimal("1"), Decimal("15000"), Decimal("0")),
    ]
    eth = preview.transactions[-1].asset
    assert (eth.known, eth.market_ref) == (False, "none")
    avisos = [(w.origin.row if w.origin else None, w.message) for w in preview.warnings]
    assert (7, "tipo precisa ser compra ou venda") in avisos
    assert any("ETH" in m for _, m in avisos)
    assert any("classe" in m for _, m in avisos)


def test_virgula_como_separador() -> None:
    preview = _preview("date,side,ticker,quantity,price\n2026-03-12,buy,PETR4,10,38.5\n")
    assert preview.transactions[0].price == Decimal("38.5")


def test_cabecalho_errado_vira_aviso() -> None:
    preview = _preview("a;b;c\n1;2;3\n")
    assert preview.files[0].rows_in == 0
    assert "cabeçalho" in preview.warnings[0].message


def test_limite_de_linhas() -> None:
    corpo = "data;tipo;ativo;quantidade;preco\n" + "12/03/2026;compra;PETR4;1;1\n" * 1001
    with pytest.raises(ImportFileError, match="1000 linhas"):
        generic_csv.parse_file(corpo.encode(), 1, HOJE)


def test_planilha_na_rota_de_csv_e_recusada() -> None:
    from pathlib import Path

    xlsx = (Path(__file__).parent / "fixtures" / "b3" / "negociacao.xlsx").read_bytes()
    with pytest.raises(ImportFileError, match="CSV"):
        generic_csv.parse_file(xlsx, 1, HOJE)
