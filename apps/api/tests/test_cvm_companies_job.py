"""O `cvm_companies` completa o cadastro sem mexer no que é da B3."""

from __future__ import annotations

import inspect

from alpherion.data.jobs import cvm_companies


def test_status_do_papel_nao_vem_da_cvm() -> None:
    """Registro ativo na CVM não é papel listado; quem decide o status é o b3_listing.

    Copiar o status da CVM reativou 579 códigos antigos e inativou 9 papéis negociados
    no banco de dev (23/09/2026).
    """
    fonte = inspect.getsource(cvm_companies.run)
    assert "status=" not in fonte


def test_nome_de_pregao_da_b3_nao_e_apagado() -> None:
    fonte = inspect.getsource(cvm_companies.run)
    assert "coalesce(Security.trade_name" in fonte
