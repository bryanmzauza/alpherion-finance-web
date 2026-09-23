"""Arquivos da Área do Investidor da B3: posição, negociação e proventos.

O tipo de cada arquivo é **detectado pelo conteúdo** (abas e cabeçalhos), não pelo nome:
a pessoa pode mandar os três em qualquer ordem, com o nome que o navegador der.
"""

from __future__ import annotations

from datetime import date

from alpherion.importers.b3 import negociacao, posicao, proventos
from alpherion.importers.base import ParseResult
from alpherion.importers.tabular import read_file


def parse_file(data: bytes, file: int, today: date) -> ParseResult:
    """Lê um arquivo e devolve o rascunho. `ImportFileError` para arquivo recusado."""
    sheets = read_file(data)

    if posicao.is_position_file(sheets):
        result = ParseResult(file=file, kind="b3_posicao")
        posicao.parse_workbook(sheets, result, today)
        return result

    for sheet in sheets:
        table = negociacao.find(sheet)
        if table is not None:
            result = ParseResult(file=file, kind="b3_negociacao")
            negociacao.parse(table, sheet, result, today)
            return result
        table = proventos.find(sheet)
        if table is not None:
            result = ParseResult(file=file, kind="b3_proventos")
            proventos.parse(table, sheet, result, today)
            return result

    result = ParseResult(file=file, kind=None)
    result.warn(
        "não reconhecemos este arquivo como posição, negociação ou movimentação da Área do "
        "Investidor da B3"
    )
    return result
