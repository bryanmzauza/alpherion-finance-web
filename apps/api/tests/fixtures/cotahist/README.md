# Fixtures do COTAHIST

Os arquivos aqui são **sintéticos**: foram escritos por nós seguindo o layout oficial
(`SeriesHistoricas_Layout.pdf`, revisão 01 de 13/04/2017), com valores inventados.

Nenhum dado real da B3 entra no repositório — o ADR-017 registra que a redistribuição
depende de licença, e um arquivo de teste também é redistribuição.

Os tickers são reais porque o parser não olha para eles (só para posição e formato), e
usar nomes conhecidos deixa o teste legível. Os preços não correspondem a pregão nenhum.

`amostra.txt` cobre, de propósito:

| Linha | O que exercita |
| --- | --- |
| header `00` | registro que o parser ignora |
| PETR4 | caso normal, lote padrão (`CODBDI 02`, `TPMERC 010`) |
| MXRF11 | FII (`CODBDI 12`) |
| BOVA11 | ETF |
| VALE3F | mercado fracionário (`TPMERC 020`) |
| PETRW20 | opção (`TPMERC 070`) — precisa ser descartada |
| ANTIGA3 | `FATCOT 1000`: preço por lote de mil, normalizado para unitário |
| SEMNEG3 | papel sem negócio no dia (`PREULT` zerado) — descartado |
| DIRTO3 | direito de subscrição (`ESPECI DIR`) — descartado |
| trailer `99` | registro que o parser ignora |
