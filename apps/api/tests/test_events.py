"""Montagem da agenda (`transform/events.py`).

A regra do produto que estes testes prendem: **a agenda só tem fato com data e fonte**.
Item sem `source_url` não entra; provento gera dois eventos (data-com e pagamento, que
são decisões diferentes); documento é listado e linkado, nunca resumido (§8.3).
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from alpherion.data.transform import events
from alpherion.data.transform.events import CorporateActionInput, DocumentInput

DIVIDENDO = CorporateActionInput(
    id=42,
    ticker="PETR4",
    kind="dividend",
    ex_date=date(2026, 11, 12),
    payment_date=date(2026, 11, 30),
    value_per_share=Decimal("0.35"),
    ratio=None,
    source="b3",
)

DOCUMENTO = DocumentInput(
    protocol="123456",
    cvm_code=9512,
    ticker="PETR4",
    category="Fato Relevante",
    subject="Aquisição de ativo",
    delivered_at=date(2026, 9, 18),
)


def _macro_file(tmp_path: Path, eventos: list[dict[str, object]]) -> Path:
    path = tmp_path / "agenda-macro.json"
    path.write_text(json.dumps({"ano": 2026, "eventos": eventos}), encoding="utf-8")
    return path


# --- proventos --------------------------------------------------------------


def test_provento_vira_dois_eventos() -> None:
    """Data-com e pagamento são decisões diferentes: comprar até, e receber em."""
    ex, pagamento = sorted(events.from_corporate_actions([DIVIDENDO]), key=lambda e: e.date)

    assert (ex.kind, ex.date) == ("ex_date", date(2026, 11, 12))
    assert "data-com" in ex.title
    assert (pagamento.kind, pagamento.date) == ("payment", date(2026, 11, 30))
    assert "pagamento" in pagamento.title
    assert ex.payload is not None
    assert ex.payload["valor_por_acao"] == "0.35"


def test_evento_societario_nao_gera_pagamento() -> None:
    """Desdobramento não paga nada: gerar um evento de pagamento seria inventar fato."""
    desdobramento = CorporateActionInput(
        id=7,
        ticker="VALE3",
        kind="split",
        ex_date=date(2026, 5, 4),
        payment_date=date(2026, 5, 10),
        value_per_share=None,
        ratio="1:2",
        source="b3",
    )
    (evento,) = list(events.from_corporate_actions([desdobramento]))
    assert evento.kind == "corporate"
    assert evento.payload is not None
    assert evento.payload["proporcao"] == "1:2"


def test_provento_so_com_data_de_pagamento() -> None:
    sem_ex = CorporateActionInput(
        id=8,
        ticker="MXRF11",
        kind="fii_income",
        ex_date=None,
        payment_date=date(2026, 10, 15),
        value_per_share=Decimal("0.10"),
        ratio=None,
        source="b3",
    )
    (evento,) = list(events.from_corporate_actions([sem_ex]))
    assert evento.kind == "payment"


def test_tipo_fora_do_vocabulario_e_ignorado() -> None:
    estranho = CorporateActionInput(
        id=9,
        ticker="AAAA3",
        kind="coisa_nova",
        ex_date=date(2026, 1, 5),
        payment_date=None,
        value_per_share=None,
        ratio=None,
        source="b3",
    )
    assert list(events.from_corporate_actions([estranho])) == []


# --- documentos -------------------------------------------------------------


def test_documento_e_listado_sem_resumo() -> None:
    """§8.3: resumir fato relevante é interpretação, e interpretação é análise."""
    (evento,) = list(events.from_documents([DOCUMENTO]))
    assert evento.kind == "document"
    assert evento.title == "PETR4 — Fato Relevante"
    assert evento.payload == {"categoria": "Fato Relevante", "assunto": "Aquisição de ativo"}
    assert evento.id == "doc:123456", "o protocolo é a chave: reconstruir não duplica"


# --- agenda macro -----------------------------------------------------------


def test_item_macro_com_fonte_entra(tmp_path: Path) -> None:
    path = _macro_file(
        tmp_path,
        [
            {
                "data": "2026-12-09",
                "titulo": "Decisão do Copom",
                "source_url": "https://www.bcb.gov.br/publicacoes/calendarioreunioes",
            }
        ],
    )
    (evento,) = list(events.from_macro(path))
    assert evento.kind == "macro"
    assert evento.date == date(2026, 12, 9)
    assert evento.payload is not None
    assert evento.payload["fonte"].startswith("https://")


def test_item_macro_sem_fonte_e_descartado(tmp_path: Path) -> None:
    """A agenda só tem fato com origem — sem link que prove, não entra."""
    path = _macro_file(tmp_path, [{"data": "2026-12-09", "titulo": "Decisão do Copom"}])
    assert list(events.from_macro(path)) == []


def test_item_macro_sem_data_e_descartado(tmp_path: Path) -> None:
    path = _macro_file(tmp_path, [{"titulo": "Algo", "source_url": "https://exemplo.gov.br"}])
    assert list(events.from_macro(path)) == []


def test_arquivo_macro_ausente_ou_invalido_nao_quebra_a_agenda(tmp_path: Path) -> None:
    assert list(events.from_macro(tmp_path / "nao-existe.json")) == []
    quebrado = tmp_path / "quebrado.json"
    quebrado.write_text("{isto não é json", encoding="utf-8")
    assert list(events.from_macro(quebrado)) == []


#: Quem pode ser fonte da agenda macro: o órgão que decide ou publica o número. Agregador,
#: jornal e corretora ficam de fora — a agenda cita quem anuncia, não quem repercute.
FONTES_OFICIAIS = (
    "https://www.bcb.gov.br/",
    "https://www.federalreserve.gov/",
    "https://www.ibge.gov.br/",
    "https://portalibre.fgv.br/",
    "https://www.b3.com.br/",
)


def test_arquivo_macro_do_repositorio_segue_o_schema() -> None:
    """O arquivo versionado cumpre `agenda-macro.schema.json` item a item.

    Sem `jsonschema` no projeto, as regras do schema são conferidas aqui à mão — e o
    teste lê o próprio schema para que as duas coisas não divirjam em silêncio.
    """
    schema = json.loads(events.MACRO_FILE.with_suffix(".schema.json").read_text(encoding="utf-8"))
    item_schema = schema["properties"]["eventos"]["items"]
    permitidos = set(item_schema["properties"])
    obrigatorios = set(item_schema["required"])

    payload = json.loads(events.MACRO_FILE.read_text(encoding="utf-8"))
    assert set(schema["required"]) <= set(payload)
    ano = payload["ano"]
    itens = payload["eventos"]
    assert itens, "a agenda macro do ano não pode estar vazia"

    for item in itens:
        assert obrigatorios <= set(item), item
        assert set(item) <= permitidos, f"campo fora do schema: {set(item) - permitidos}"
        dia = date.fromisoformat(item["data"])
        assert dia.year == ano, item
        assert 3 <= len(item["titulo"]) <= 160
        assert item.get("detalhe") is None or len(item["detalhe"]) <= 300
        assert item["source_url"].startswith(FONTES_OFICIAIS), item["source_url"]

    # Ordem por data e nenhum item repetido: o id do evento é data + título.
    chaves = [(item["data"], item["titulo"]) for item in itens]
    assert chaves == sorted(chaves)
    assert len(set(chaves)) == len(chaves)
    # Nada é descartado na leitura: o arquivo inteiro vira agenda.
    assert len(list(events.from_macro())) == len(itens)


def test_agenda_macro_nao_projeta_nada() -> None:
    """Só o que alguém anunciou: nenhuma expectativa, consenso ou "provável"."""
    texto = events.MACRO_FILE.read_text(encoding="utf-8").lower()
    for proibido in ("espera-se", "expectativa", "consenso", "projeção", "provável", "deve "):
        assert proibido not in texto, proibido


# --- agenda completa --------------------------------------------------------


def test_agenda_sai_ordenada_por_data(tmp_path: Path) -> None:
    path = _macro_file(
        tmp_path,
        [{"data": "2026-10-01", "titulo": "IPCA", "source_url": "https://ibge.gov.br"}],
    )
    agenda = events.build([DIVIDENDO], [DOCUMENTO], macro_file=path)
    assert [e.date for e in agenda] == sorted(e.date for e in agenda)
    assert {e.kind for e in agenda} == {"document", "macro", "ex_date", "payment"}


def test_reconstruir_da_os_mesmos_ids(tmp_path: Path) -> None:
    """Ids determinísticos são o que torna o rebuild idempotente."""
    primeira = events.build([DIVIDENDO], [DOCUMENTO], macro_file=tmp_path / "vazio.json")
    segunda = events.build([DIVIDENDO], [DOCUMENTO], macro_file=tmp_path / "vazio.json")
    assert [e.id for e in primeira] == [e.id for e in segunda]
