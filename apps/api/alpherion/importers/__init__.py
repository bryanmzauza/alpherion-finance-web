"""Importadores: arquivos da Área do Investidor da B3 e CSV genérico (Etapa 5.2).

Fluxo: `tabular.read_file` (leitura segura) → parser (`b3/`, `generic_csv`) só com as
colunas permitidas → `base.build_preview` (resolve ativos no schema `market`) → prévia.
Tudo em memória; o arquivo é descartado ao fim da requisição e nunca é logado. CPF e
nome não passam da leitura: o parser não pede essas colunas, então elas não existem
para nada que vem depois.
"""
