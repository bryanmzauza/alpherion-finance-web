"""Proteções do cliente HTTP do worker (site.md §7.5)."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import httpx
import pytest

from alpherion.data.sources.http import SourceError, check_host, download, extract_single

CVM = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_2025.zip"


def _transport(handler: object) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))  # type: ignore[arg-type]


def test_host_fora_da_lista_e_recusado() -> None:
    with pytest.raises(SourceError, match="host não permitido"):
        check_host("https://exemplo-malicioso.com/arquivo.zip")


def test_host_da_lista_passa() -> None:
    check_host(CVM)  # não levanta


def test_download_grava_o_arquivo(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"conteudo")

    dest = download(CVM, tmp_path / "a.zip", max_bytes=1024, http=_transport(handler))
    assert dest.read_bytes() == b"conteudo"


def test_download_aborta_ao_passar_do_limite(tmp_path: Path) -> None:
    """Não confiamos no Content-Length: o corte é pelo que chega de verdade."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * 5000)

    dest = tmp_path / "grande.zip"
    with pytest.raises(SourceError, match="limite de download"):
        download(CVM, dest, max_bytes=1000, http=_transport(handler))
    assert not dest.exists(), "arquivo parcial não pode ficar no disco"


def test_redirect_para_host_estranho_e_recusado(tmp_path: Path) -> None:
    """Redirect é o caminho clássico para fazer o worker buscar dado em outro servidor."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "dados.cvm.gov.br":
            return httpx.Response(302, headers={"location": "https://malicioso.example/x.zip"})
        return httpx.Response(200, content=b"nao deveria chegar aqui")

    with pytest.raises(SourceError, match="host não permitido"):
        download(CVM, tmp_path / "a.zip", max_bytes=1024, http=_transport(handler))


def test_redirect_para_host_permitido_e_seguido(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "dados.cvm.gov.br":
            return httpx.Response(302, headers={"location": "https://arquivos.b3.com.br/ok.zip"})
        return httpx.Response(200, content=b"final")

    dest = download(CVM, tmp_path / "a.zip", max_bytes=1024, http=_transport(handler))
    assert dest.read_bytes() == b"final"


def test_http_de_erro_vira_source_error(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    with pytest.raises(SourceError, match="HTTP 503"):
        download(CVM, tmp_path / "a.zip", max_bytes=1024, http=_transport(handler))


def _zip(tmp_path: Path, name: str, content: bytes) -> Path:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, content)
    path = tmp_path / "pacote.zip"
    path.write_bytes(buffer.getvalue())
    return path


def test_extrai_arquivo_unico(tmp_path: Path) -> None:
    zip_path = _zip(tmp_path, "dados.csv", b"a;b\n1;2\n")
    dest = extract_single(zip_path, tmp_path / "out", max_bytes=1024)
    assert dest.name == "dados.csv"
    assert dest.read_bytes() == b"a;b\n1;2\n"


def test_zip_bomb_e_recusado_pelo_tamanho_declarado(tmp_path: Path) -> None:
    """1 MB de zeros comprime para alguns KB: é o formato do ataque."""
    zip_path = _zip(tmp_path, "bomba.csv", b"\0" * (1 << 20))
    with pytest.raises(SourceError, match="descomprimidos"):
        extract_single(zip_path, tmp_path / "out", max_bytes=1024)


def test_caminho_de_fuga_no_zip_e_neutralizado(tmp_path: Path) -> None:
    """`../../etc/cron.d/x` no nome do membro não pode escrever fora do destino."""
    zip_path = _zip(tmp_path, "../../fuga.csv", b"x")
    dest = extract_single(zip_path, tmp_path / "out", max_bytes=1024)
    assert dest.parent == tmp_path / "out"
    assert dest.name == "fuga.csv"


def test_zip_com_varios_arquivos_e_recusado(tmp_path: Path) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("a.csv", b"1")
        archive.writestr("b.csv", b"2")
    zip_path = tmp_path / "dois.zip"
    zip_path.write_bytes(buffer.getvalue())
    with pytest.raises(SourceError, match="esperado 1 arquivo"):
        extract_single(zip_path, tmp_path / "out", max_bytes=1024)
