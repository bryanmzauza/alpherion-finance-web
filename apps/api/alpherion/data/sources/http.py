"""Cliente HTTP do worker `data`, com as proteções do site.md §7.5.

O worker baixa arquivos de terceiros (CVM, B3, Tesouro, BCB, CoinGecko) — é a maior
superfície de ataque do pipeline. Três defesas, todas aqui e não espalhadas nos jobs:

1. **Lista fechada de hosts.** Um redirecionamento não leva o worker para outro domínio.
2. **Limite de download.** O corpo é lido em pedaços e a transferência é abortada ao
   passar do teto — não confiamos no `Content-Length` (o servidor pode mentir).
3. **Limite de descompressão** (`zip bomb`): um ZIP de 2 MB pode virar 20 GB em disco.

Nada aqui depende de licença: a proteção vale para toda fonte. O que depende de licença
é *publicar* o resultado (ADR-017).
"""

from __future__ import annotations

import logging
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Final
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

#: Hosts que o worker pode acessar. Qualquer outro é erro, inclusive via redirect.
ALLOWED_HOSTS: Final = frozenset(
    {
        "dados.cvm.gov.br",
        "www.b3.com.br",
        "bvmf.bmfbovespa.com.br",
        "sistemaswebb3-listados.b3.com.br",
        "arquivos.b3.com.br",
        "www.tesourotransparente.gov.br",
        "api.bcb.gov.br",
        "api.coingecko.com",
    }
)

DEFAULT_TIMEOUT: Final = httpx.Timeout(30.0, connect=10.0, read=120.0)
USER_AGENT: Final = "AlpherionFinance/0.1 (+https://alpherion.com.br; contato@alpherion.com.br)"
CHUNK: Final = 1 << 16  # 64 kB


class SourceError(RuntimeError):
    """Falha ao obter dado de uma fonte externa (host, tamanho, HTTP, formato)."""


def check_host(url: str) -> None:
    host = urlparse(url).hostname or ""
    if host not in ALLOWED_HOSTS:
        raise SourceError(f"host não permitido: {host!r} (ver ALLOWED_HOSTS em sources/http.py)")


@contextmanager
def client(**kwargs: object) -> Iterator[httpx.Client]:
    """Cliente com timeout, user-agent identificável e redirect **desligado**.

    Redirect desligado de propósito: quem decide seguir é o chamador, e aí o host novo
    passa por `check_host` de novo.
    """
    with httpx.Client(
        timeout=DEFAULT_TIMEOUT,
        follow_redirects=False,
        headers={"User-Agent": USER_AGENT},
        **kwargs,  # type: ignore[arg-type]
    ) as http:
        yield http


def download(
    url: str,
    dest: Path,
    *,
    max_bytes: int,
    max_redirects: int = 3,
    http: httpx.Client | None = None,
) -> Path:
    """Baixa `url` para `dest`, abortando se passar de `max_bytes`.

    Cada redirecionamento é validado contra a lista de hosts — é o caminho clássico de
    fazer um worker buscar dado em servidor de terceiro.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    def _fetch(session: httpx.Client) -> Path:
        current = url
        for _ in range(max_redirects + 1):
            check_host(current)
            with session.stream("GET", current) as response:
                if response.is_redirect:
                    location = response.headers.get("location", "")
                    current = str(httpx.URL(current).join(location))
                    continue
                if response.status_code != httpx.codes.OK:
                    raise SourceError(f"{current}: HTTP {response.status_code}")
                written = 0
                with dest.open("wb") as file:
                    for chunk in response.iter_bytes(CHUNK):
                        written += len(chunk)
                        if written > max_bytes:
                            file.close()
                            dest.unlink(missing_ok=True)
                            raise SourceError(
                                f"{current}: passou de {max_bytes} bytes (limite de download, §7.5)"
                            )
                        file.write(chunk)
                logger.info("baixado %s (%d bytes) → %s", current, written, dest)
                return dest
        raise SourceError(f"{url}: redirecionamentos demais")

    if http is not None:
        return _fetch(http)
    with client() as session:
        return _fetch(session)


def safe_name(member: zipfile.ZipInfo, archive_name: str) -> str:
    """Nome de arquivo sem diretório e sem caminho de fuga (`../`, caminho absoluto)."""
    name = Path(member.filename.replace("\\", "/")).name
    if not name or name.startswith("."):
        raise SourceError(f"{archive_name}: nome de arquivo suspeito: {member.filename!r}")
    return name


def _extract_member(
    archive: zipfile.ZipFile,
    member: zipfile.ZipInfo,
    dest: Path,
    *,
    max_bytes: int,
    archive_name: str,
) -> int:
    """Escreve um membro em `dest`, cortando se a descompressão passar de `max_bytes`.

    Checamos o tamanho **declarado** antes de extrair e o **real** durante a escrita:
    o cabeçalho do ZIP é dado do atacante como qualquer outro.
    """
    if member.file_size > max_bytes:
        raise SourceError(
            f"{archive_name}: {member.filename} declara {member.file_size} bytes "
            f"descomprimidos (limite {max_bytes}, §7.5)"
        )
    written = 0
    with archive.open(member) as source, dest.open("wb") as target:
        while chunk := source.read(CHUNK):
            written += len(chunk)
            if written > max_bytes:
                target.close()
                dest.unlink(missing_ok=True)
                raise SourceError(f"{archive_name}: descompressão passou de {max_bytes} bytes")
            target.write(chunk)
    return written


def extract_all(
    zip_path: Path,
    dest_dir: Path,
    *,
    max_bytes: int,
    match: str | None = None,
) -> list[Path]:
    """Extrai os arquivos de um ZIP com vários membros (os pacotes da CVM têm dezenas).

    `max_bytes` é o teto **por arquivo** e também o do total: um pacote da DFP traz
    BPA, BPP, DRE, DFC e DMPL do ano inteiro, e só lemos alguns deles — `match` filtra
    por trecho do nome antes de gastar disco.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    total = 0
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            name = safe_name(member, zip_path.name)
            if match is not None and match.lower() not in name.lower():
                continue
            dest = dest_dir / name
            total += _extract_member(
                archive, member, dest, max_bytes=max_bytes, archive_name=zip_path.name
            )
            if total > max_bytes:
                for path in [*extracted, dest]:
                    path.unlink(missing_ok=True)
                raise SourceError(f"{zip_path.name}: descompressão total passou de {max_bytes}")
            extracted.append(dest)
    if not extracted:
        raise SourceError(f"{zip_path.name}: nenhum arquivo casou com {match!r}")
    logger.info("extraídos %d arquivos de %s (%d bytes)", len(extracted), zip_path.name, total)
    return extracted


def extract_single(zip_path: Path, dest_dir: Path, *, max_bytes: int) -> Path:
    """Extrai o único arquivo de um ZIP, recusando `zip bomb` e caminho de fuga."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        members = [m for m in archive.infolist() if not m.is_dir()]
        if len(members) != 1:
            raise SourceError(f"{zip_path.name}: esperado 1 arquivo, veio {len(members)}")
        member = members[0]
        dest = dest_dir / safe_name(member, zip_path.name)  # descarta o diretório do caminho
        written = _extract_member(
            archive, member, dest, max_bytes=max_bytes, archive_name=zip_path.name
        )
    logger.info("extraído %s (%d bytes) → %s", zip_path.name, written, dest)
    return dest
