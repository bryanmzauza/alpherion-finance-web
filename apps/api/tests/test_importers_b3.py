"""Importadores da Área do Investidor (Etapa 5.2) sobre as fixtures de `fixtures/b3/`.

O que se prova aqui:

- cada arquivo é reconhecido pelo conteúdo e vira as linhas certas (ETF e BDR inclusos);
- **CPF, nome, conta e instituição não aparecem na prévia nem em log**;
- duas execuções idênticas no mesmo dia são dois negócios (ocorrência 1 e 2), e o mesmo
  provento em dois relatórios gera a mesma chave (sem duplicar);
- arquivo hostil (macro, zip bomb, binário) é recusado com mensagem, sem derrubar a rota.
"""

from __future__ import annotations

import asyncio
import io
import logging
import zipfile
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from alpherion.db.session import get_session
from alpherion.importers import b3
from alpherion.importers.assets import MemoryCatalog, SecurityInfo, TreasuryInfo
from alpherion.importers.base import build_preview
from alpherion.importers.models import ImportPreview
from alpherion.importers.tabular import (
    MAX_UNCOMPRESSED_BYTES,
    ImportFileError,
    parse_decimal,
    parse_ticker,
    read_file,
)
from alpherion.routers import imports as imports_router

from .conftest import IMPORTS_TOKEN, READONLY_TOKEN
from .fixtures.b3.gerar import CONTA, CORRETORA, CORRETORA_2, CPF, NOME

FIXTURES = Path(__file__).parent / "fixtures" / "b3"
HOJE = date(2026, 9, 23)

CATALOGO = MemoryCatalog(
    securities_={
        "PETR4": SecurityInfo("PETR4", "stock", "PETROBRAS"),
        "VALE3": SecurityInfo("VALE3", "stock", "VALE"),
        "AAPL34": SecurityInfo("AAPL34", "bdr", "APPLE"),
        "BOVA11": SecurityInfo("BOVA11", "etf", "ISHARES BOVA"),
        "HGLG11": SecurityInfo("HGLG11", "fii", "CSHG LOGÍSTICA"),
    },
    treasury_=[
        TreasuryInfo("ipca-2035-05-15", "Tesouro IPCA+", date(2035, 5, 15)),
        TreasuryInfo(
            "ipca-juros-2035-05-15", "Tesouro IPCA+ com Juros Semestrais", date(2035, 5, 15)
        ),
        TreasuryInfo("selic-2029-03-01", "Tesouro Selic", date(2029, 3, 1)),
    ],
)

SENSIVEIS = (NOME, CPF, "12345678909", CONTA, CORRETORA, CORRETORA_2, "FULANA")


def _bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _preview(*names: str) -> ImportPreview:
    results = [b3.parse_file(_bytes(n), i, HOJE) for i, n in enumerate(names, 1)]
    return asyncio.run(build_preview(results, CATALOGO))


# --- valores ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("R$ 1.234,56", Decimal("1234.56")),
        ("38,5", Decimal("38.5")),
        ("1234.56", Decimal("1234.56")),
        ("1.234.567", Decimal("1234567")),
        (38.5, Decimal("38.5")),
        # Float do Excel: sem lixo de ponto flutuante além de 10 casas, sem expoente.
        (0.1 + 0.2, Decimal("0.3000000000")),
        ("1e5", Decimal("100000")),
        ("-", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_decimal(raw: Any, expected: Decimal | None) -> None:
    assert parse_decimal(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("PETR4", "PETR4"),
        ("petr4f", "PETR4"),
        ("PETR4 - PETROLEO BRASILEIRO", "PETR4"),
        ("AAPL34", "AAPL34"),
        ("BOVA11", "BOVA11"),
        ("PETRJ300", None),
        ("Tesouro Selic 2029", None),
    ],
)
def test_parse_ticker(raw: str, expected: str | None) -> None:
    assert parse_ticker(raw) == expected


# --- negociação -------------------------------------------------------------


def test_negociacao() -> None:
    preview = _preview("negociacao.xlsx")
    [arquivo] = preview.files
    assert (arquivo.kind, arquivo.rows_in, arquivo.rows_ok, arquivo.rows_skipped) == (
        "b3_negociacao",
        8,
        7,
        1,
    )
    petr = [t for t in preview.transactions if t.asset.symbol == "PETR4"]
    assert [(str(t.date), t.side, t.quantity, t.occurrence) for t in petr] == [
        ("2024-01-10", "buy", Decimal(100), 1),
        ("2024-03-15", "buy", Decimal(50), 1),
        ("2024-03-15", "buy", Decimal(50), 2),  # segunda execução idêntica: outro negócio
        ("2024-05-20", "buy", Decimal(5), 1),  # PETR4F → PETR4
        ("2024-07-02", "sell", Decimal(55), 1),
    ]
    assert petr[3].price == Decimal("36.40")
    classes = {t.asset.symbol: t.asset.asset_class for t in preview.transactions}
    assert classes == {"PETR4": "stock_br", "AAPL34": "bdr", "BOVA11": "etf_br"}
    avisos = " ".join(w.message for w in preview.warnings)
    assert "Opção de Compra" in avisos
    assert "não traz taxas" in avisos


# --- posição ----------------------------------------------------------------


def test_posicao() -> None:
    preview = _preview("posicao.xlsx")
    [arquivo] = preview.files
    assert (arquivo.kind, arquivo.rows_in, arquivo.rows_ok) == ("b3_posicao", 10, 9)
    by_symbol = {p.asset.symbol: p for p in preview.positions}

    # PETR4 em duas corretoras vira uma posição só.
    assert by_symbol["PETR4"].quantity == 200
    assert by_symbol["VALE3"].quantity == 300
    assert by_symbol["AAPL34"].asset.asset_class == "bdr"
    assert by_symbol["BOVA11"].asset.asset_class == "etf_br"
    assert by_symbol["HGLG11"].asset.asset_class == "fii"

    ipca = by_symbol["ipca-2035-05-15"]  # não o "com Juros Semestrais" do mesmo vencimento
    assert (ipca.asset.market_ref, ipca.quantity, ipca.avg_price) == (
        "treasury_slug",
        Decimal("1.5"),
        Decimal("2000"),
    )
    assert by_symbol["selic-2029-03-01"].avg_price == Decimal("15000")

    cdb = by_symbol["CDB924ABC12"]
    assert (cdb.asset.asset_class, cdb.quantity, cdb.value_brl) == (
        "fixed_income",
        None,
        Decimal("5490"),  # na curva, não o MTM
    )
    assert "LCI000VENC1" not in by_symbol  # vencida

    avisos = " ".join(w.message for w in preview.warnings)
    assert "Opções" in avisos and "vencido" in avisos
    assert all(p.asset.known for p in preview.positions)


# --- proventos --------------------------------------------------------------


def test_movimentacao_so_proventos_pagos() -> None:
    preview = _preview("movimentacao.xlsx")
    [arquivo] = preview.files
    assert (arquivo.kind, arquivo.rows_in, arquivo.rows_ok) == ("b3_proventos", 8, 3)
    assert [(i.asset.symbol, i.kind, i.net, i.gross) for i in preview.income] == [
        ("PETR4", "dividend", Decimal("108"), None),
        ("PETR4", "jcp", Decimal("42.5"), None),
        ("HGLG11", "fii_income", Decimal("33"), None),
    ]
    avisos = " ".join(w.message for w in preview.warnings)
    assert "Transferência - Liquidação (2)" in avisos
    assert "Dividendo - Transferido" in avisos
    assert "futura" in avisos and "sem valor" in avisos


def test_mesmo_provento_em_dois_relatorios_nao_duplica() -> None:
    preview = _preview("movimentacao.xlsx", "proventos-recebidos.xlsx")
    dividendos = [
        (i.asset.symbol, i.date, i.kind, i.net, i.gross, i.occurrence)
        for i in preview.income
        if i.kind == "dividend"
    ]
    # Mesma tupla nos dois arquivos → mesma chave de dedupe no `web` → uma linha só.
    assert len(dividendos) == 2 and dividendos[0] == dividendos[1]


def test_tres_arquivos_juntos_em_qualquer_ordem() -> None:
    preview = _preview("movimentacao.xlsx", "posicao.xlsx", "negociacao.xlsx")
    assert [f.kind for f in preview.files] == ["b3_proventos", "b3_posicao", "b3_negociacao"]
    assert preview.transactions and preview.positions and preview.income


# --- privacidade ------------------------------------------------------------


def test_cpf_nome_conta_e_instituicao_nao_saem(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    preview = _preview("posicao.xlsx", "negociacao.xlsx", "movimentacao.xlsx").model_dump_json()
    preview += _preview("proventos-recebidos.xlsx").model_dump_json()
    for valor in SENSIVEIS:
        assert valor not in preview, valor
        assert valor not in caplog.text, valor


# --- arquivos hostis --------------------------------------------------------


def _xlsx_com(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in entries.items():
            z.writestr(name, content)
    return buffer.getvalue()


def test_recusa_macro() -> None:
    data = _xlsx_com({"[Content_Types].xml": b"<Types/>", "xl/vbaProject.bin": b"\x00" * 10})
    with pytest.raises(ImportFileError, match="macros"):
        read_file(data)


def test_recusa_macro_pelo_content_type() -> None:
    tipo = b"application/vnd.ms-excel.sheet.macroEnabled.main+xml"
    tipos = b'<Types><Override ContentType="' + tipo + b'"/></Types>'
    with pytest.raises(ImportFileError, match="macros"):
        read_file(_xlsx_com({"[Content_Types].xml": tipos}))


def test_recusa_zip_bomb() -> None:
    data = _xlsx_com(
        {"[Content_Types].xml": b"<Types/>", "xl/bomba.xml": b"0" * (MAX_UNCOMPRESSED_BYTES + 1)}
    )
    assert len(data) < 1024 * 1024  # pequeno comprimido, enorme aberto
    with pytest.raises(ImportFileError, match="descomprimida"):
        read_file(data)


def test_recusa_binario_e_vazio() -> None:
    with pytest.raises(ImportFileError):
        read_file(b"\x00\x01\x02 binario qualquer")
    with pytest.raises(ImportFileError, match="vazio"):
        read_file(b"")


def test_arquivo_desconhecido_vira_aviso() -> None:
    result = b3.parse_file(b"coluna;outra\n1;2\n", 1, HOJE)
    assert result.kind is None
    assert "não reconhecemos" in result.warnings[0].message


# --- rota -------------------------------------------------------------------


@pytest.fixture
def imports_client(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    async def fake_session() -> Any:
        yield None

    app = client.app
    app.dependency_overrides[get_session] = fake_session  # type: ignore[attr-defined]
    monkeypatch.setattr(imports_router, "DbCatalog", lambda _session: CATALOGO)
    yield client
    app.dependency_overrides.clear()  # type: ignore[attr-defined]


def _files(*names: str) -> list[tuple[str, tuple[str, bytes, str]]]:
    return [("files", (n, _bytes(n), "application/octet-stream")) for n in names]


def test_rota_b3(imports_client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    response = imports_client.post(
        "/v1/imports/b3/preview",
        files=_files("posicao.xlsx", "negociacao.xlsx", "movimentacao.xlsx"),
        headers={"Authorization": f"Bearer {IMPORTS_TOKEN}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert [f["kind"] for f in body["files"]] == ["b3_posicao", "b3_negociacao", "b3_proventos"]
    assert body["transactions"][0]["quantity"] == "100"  # decimal como string
    for valor in SENSIVEIS:
        assert valor not in response.text
        assert valor not in caplog.text


def test_rota_b3_exige_escopo(imports_client: TestClient) -> None:
    response = imports_client.post(
        "/v1/imports/b3/preview",
        files=_files("posicao.xlsx"),
        headers={"Authorization": f"Bearer {READONLY_TOKEN}"},
    )
    assert response.status_code == 403


def test_rota_b3_no_maximo_tres_arquivos(imports_client: TestClient) -> None:
    response = imports_client.post(
        "/v1/imports/b3/preview",
        files=_files(
            "posicao.xlsx", "negociacao.xlsx", "movimentacao.xlsx", "proventos-recebidos.xlsx"
        ),
        headers={"Authorization": f"Bearer {IMPORTS_TOKEN}"},
    )
    assert response.status_code in (400, 422)


def test_rota_b3_arquivo_ruim_nao_derruba_os_outros(imports_client: TestClient) -> None:
    response = imports_client.post(
        "/v1/imports/b3/preview",
        files=[
            *_files("negociacao.xlsx"),
            (
                "files",
                (
                    "x.xlsm",
                    _xlsx_com({"[Content_Types].xml": b"<Types/>", "xl/vbaProject.bin": b"1"}),
                    "application/octet-stream",
                ),
            ),
        ],
        headers={"Authorization": f"Bearer {IMPORTS_TOKEN}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["files"][1]["kind"] is None
    assert any("macros" in w["message"] for w in body["warnings"])
    assert body["transactions"]


def test_rota_b3_recusa_corpo_grande_pelo_cabecalho(imports_client: TestClient) -> None:
    response = imports_client.post(
        "/v1/imports/b3/preview",
        content=b"x",
        headers={
            "Authorization": f"Bearer {IMPORTS_TOKEN}",
            "Content-Type": "multipart/form-data; boundary=x",
            "Content-Length": str(50 * 1024 * 1024),
        },
    )
    assert response.status_code == 413
