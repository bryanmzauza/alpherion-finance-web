"""Prévia de importação (site.md §2.3, §7.4): arquivo → linhas normalizadas + avisos.

A API **não grava nada** e **não guarda o arquivo**: lê em memória, devolve a prévia e
descarta. Quem grava (cifrado) é o `web`, depois que a pessoa confirma.

- **Em memória de verdade.** O parser de multipart do Starlette manda para disco toda
  parte acima de 1 MB; aqui o limite de spool é o do próprio corpo, então o arquivo
  nunca toca o disco. O corpo é limitado **antes** de ler (`Content-Length`) e contado
  **durante** a leitura (quem mente no cabeçalho para no limite).
- **Sem conteúdo em log.** Erro inesperado de parse vira aviso genérico e o log registra
  só o tipo da exceção — a mensagem poderia conter o valor de uma célula.
"""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import AsyncGenerator, Callable
from typing import Annotated, Final
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser

from alpherion.auth import require_scopes
from alpherion.db.session import get_session
from alpherion.importers import b3, generic_csv
from alpherion.importers.base import ParseResult, build_preview
from alpherion.importers.catalog import DbCatalog
from alpherion.importers.models import ImportPreview
from alpherion.importers.tabular import MAX_CSV_BYTES, MAX_FILE_BYTES, ImportFileError

log = logging.getLogger(__name__)

router = APIRouter(
    prefix="/imports", tags=["imports"], dependencies=[Depends(require_scopes("imports:write"))]
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]

MAX_B3_FILES: Final = 3
#: Folga do envelope multipart (cabeçalhos das partes, boundaries).
ENVELOPE: Final = 64 * 1024
TZ: Final = ZoneInfo("America/Sao_Paulo")


class _InMemoryParser(MultiPartParser):
    spool_max_size = MAX_B3_FILES * MAX_FILE_BYTES + ENVELOPE


async def _read_files(request: Request, *, max_files: int, max_file_bytes: int) -> list[bytes]:
    limit = max_files * max_file_bytes + ENVELOPE
    too_large = HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "envio maior que o permitido")
    declared = request.headers.get("content-length")
    if declared is None:
        raise HTTPException(status.HTTP_411_LENGTH_REQUIRED, "Content-Length obrigatório")
    if not declared.isdigit() or int(declared) > limit:
        raise too_large
    if not request.headers.get("content-type", "").startswith("multipart/form-data"):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "envie multipart/form-data")

    async def bounded() -> AsyncGenerator[bytes, None]:
        received = 0
        async for chunk in request.stream():
            received += len(chunk)
            if received > limit:
                raise too_large
            yield chunk

    parser = _InMemoryParser(
        request.headers, bounded(), max_files=max_files, max_fields=2, max_part_size=1024
    )
    try:
        form = await parser.parse()
    except MultiPartException as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "envio multipart inválido") from error
    try:
        uploads = [f for f in form.getlist("files") if isinstance(f, UploadFile)]
        if not 1 <= len(uploads) <= max_files:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, f"envie de 1 a {max_files} arquivos"
            )
        return [await upload.read() for upload in uploads]
    finally:
        await form.close()


def _safe_parse(
    parse: Callable[[bytes, int, dt.date], ParseResult], data: bytes, file: int, today: dt.date
) -> ParseResult:
    try:
        return parse(data, file, today)
    except ImportFileError as error:
        result = ParseResult(file=file, kind=None)
        result.warn(f"arquivo {file}: {error}")
        return result
    except Exception as error:  # noqa: BLE001 - arquivo do usuário; nunca derruba a rota
        log.warning("falha inesperada no parse do arquivo (%s)", type(error).__name__)
        result = ParseResult(file=file, kind=None)
        result.warn(f"arquivo {file}: não foi possível ler o arquivo")
        return result


@router.post("/b3/preview", response_model=ImportPreview)
async def preview_b3(request: Request, session: SessionDep) -> ImportPreview:
    """1 a 3 arquivos da Área do Investidor (posição, negociação, movimentação/proventos)."""
    files = await _read_files(request, max_files=MAX_B3_FILES, max_file_bytes=MAX_FILE_BYTES)
    today = dt.datetime.now(TZ).date()
    results = [_safe_parse(b3.parse_file, data, i, today) for i, data in enumerate(files, 1)]
    del files
    return await build_preview(results, DbCatalog(session))


@router.post("/csv/preview", response_model=ImportPreview)
async def preview_csv(request: Request, session: SessionDep) -> ImportPreview:
    """CSV genérico de movimentações (≤ 2 MB, ≤ 1000 linhas; modelo no `web`)."""
    [data] = await _read_files(request, max_files=1, max_file_bytes=MAX_CSV_BYTES)
    today = dt.datetime.now(TZ).date()
    result = _safe_parse(generic_csv.parse_file, data, 1, today)
    del data
    return await build_preview([result], DbCatalog(session))
