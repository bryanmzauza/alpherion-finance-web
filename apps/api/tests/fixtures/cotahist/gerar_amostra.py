"""Gera `amostra.txt` (fixture sintética do COTAHIST).

    uv run python tests/fixtures/cotahist/gerar_amostra.py

Escrever o arquivo por um gerador — em vez de commitar bytes à mão — deixa explícito
quais campos cada caso de teste exercita, e permite recriar a fixture se o layout mudar.
Nenhum dado real da B3: ver README.md desta pasta.
"""

from __future__ import annotations

from pathlib import Path

from alpherion.data.transform.cotahist_parser import FIELDS, RECORD_SIZE

OUT = Path(__file__).parent / "amostra.txt"


def record(**values: str) -> str:
    """Monta um registro de 245 bytes posicionando cada campo pelo layout."""
    line = [" "] * RECORD_SIZE
    for field, raw in values.items():
        start, end = FIELDS[field]
        width = end - start + 1
        if len(raw) > width:
            raise ValueError(f"{field}: {raw!r} não cabe em {width} bytes")
        # Numérico é alinhado à direita com zeros; texto, à esquerda com espaços.
        filled = raw.rjust(width, "0") if raw.isdigit() else raw.ljust(width)
        line[start - 1 : end] = list(filled)
    return "".join(line)


def quote(
    *,
    ticker: str,
    data: str = "20260921",
    codbdi: str = "02",
    tpmerc: str = "010",
    especi: str = "ON",
    nomres: str = "EMPRESA",
    preabe: str = "0",
    premax: str = "0",
    premin: str = "0",
    premed: str = "0",
    preult: str = "0",
    totneg: str = "0",
    quatot: str = "0",
    voltot: str = "0",
    fatcot: str = "1",
    codisi: str = "",
) -> str:
    return record(
        tipreg="01",
        data=data,
        codbdi=codbdi,
        codneg=ticker,
        tpmerc=tpmerc,
        nomres=nomres,
        especi=especi,
        preabe=preabe,
        premax=premax,
        premin=premin,
        premed=premed,
        preult=preult,
        totneg=totneg,
        quatot=quatot,
        voltot=voltot,
        fatcot=fatcot,
        codisi=codisi,
    )


def build() -> list[str]:
    return [
        record(tipreg="00", data="20260921"),
        # PETR4: caso normal. Fechamento 41,20; volume R$ 1.234.567,89.
        quote(
            ticker="PETR4",
            especi="PN",
            nomres="PETROBRAS",
            preabe="4050",
            premax="4180",
            premin="4030",
            premed="4110",
            preult="4120",
            totneg="15234",
            quatot="29970",
            voltot="123456789",
            codisi="BRPETRACNPR6",
        ),
        # MXRF11: FII (CODBDI 12), cota a 10,45.
        quote(
            ticker="MXRF11",
            codbdi="12",
            especi="CI",
            nomres="MAXI REN",
            preabe="1040",
            premax="1048",
            premin="1039",
            premed="1045",
            preult="1045",
            totneg="8900",
            quatot="450000",
            voltot="47025000",
        ),
        # BOVA11: ETF, cota a 128,90.
        quote(
            ticker="BOVA11",
            codbdi="14",
            especi="CI",
            nomres="ISHARES",
            preult="12890",
            totneg="5000",
            quatot="20000",
            voltot="257800000",
        ),
        # VALE3F: mercado fracionário do mesmo papel.
        quote(
            ticker="VALE3F",
            tpmerc="020",
            especi="ON",
            nomres="VALE",
            preult="5530",
            totneg="42",
            quatot="97",
            voltot="536410",
        ),
        # Opção de compra: fora do escopo do v1 (não é o que a página mostra).
        quote(
            ticker="PETRW20",
            tpmerc="070",
            especi="PN",
            nomres="PETROBRAS",
            preult="150",
            totneg="900",
            quatot="100000",
            voltot="15000000",
        ),
        # Papel cotado por lote de mil (FATCOT 1000): 12.500,00 por lote = 12,50 unitário.
        quote(
            ticker="ANTIGA3",
            especi="ON",
            nomres="ANTIGA SA",
            preabe="1250000",
            premax="1260000",
            premin="1240000",
            preult="1250000",
            totneg="10",
            quatot="3000",
            voltot="3750000",
            fatcot="1000",
        ),
        # Sem negócio no dia: PREULT zerado.
        quote(ticker="SEMNEG3", especi="ON", nomres="PARADA", preult="0"),
        # Direito de subscrição: não é papel que publicamos.
        quote(
            ticker="DIRTO3",
            especi="DIR ORD",
            nomres="DIREITO",
            preult="230",
            totneg="5",
            quatot="100",
            voltot="23000",
        ),
        record(tipreg="99"),
    ]


if __name__ == "__main__":
    lines = build()
    for index, line in enumerate(lines):
        if len(line) != RECORD_SIZE:
            raise SystemExit(f"linha {index}: {len(line)} bytes (esperado {RECORD_SIZE})")
    OUT.write_text("\n".join(lines) + "\n", encoding="latin-1")
    print(f"{OUT} — {len(lines)} registros")  # noqa: T201
