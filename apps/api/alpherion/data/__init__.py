"""Pipeline de dados de mercado (worker `data`). Só escreve no schema `market`.

sources/   download das fontes oficiais (CVM, B3, Tesouro, BCB, CoinGecko)
transform/ parsers e fórmulas (cotahist_parser, cvm_statements, adjust, indicators)
jobs/      um módulo por job; idempotentes, com lock no Redis, registram `etl_runs`
"""
