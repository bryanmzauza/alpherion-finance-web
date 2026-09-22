# Fontes de dados — termos de uso verificados

> Verificação: 21/09/2026 · Responsável: Bryan · Exigido por [site.md §8.10](site.md#810-dados-públicos-de-mercado--fontes-termos-e-apresentação) e pela Etapa 2.5 do [plano](plano-de-desenvolvimento.md).
> Regra: nenhuma fonte entra em produção com status diferente de **OK**. Cópias dos documentos citados ficam em [`fontes-de-dados/`](fontes-de-dados/). Reverificar a cada mudança de política da fonte e, no mínimo, uma vez por ano (a B3 revisa a política todo janeiro).

## Resumo

| Fonte | Uso no produto | Licença / termos | Status |
| --- | --- | --- | --- |
| CVM Dados Abertos (cias abertas: cadastro, DFP, ITR, FRE/FCA, IPE; fundos: cadastro, informe diário) | Demonstrações, indicadores fundamentalistas, comunicados, fundos | Dados abertos do Poder Executivo Federal (Lei 12.527/2011; Decreto 8.777/2016, art. 4: livre utilização) | **OK** — atribuição "Fonte: CVM" |
| Tesouro Transparente (preços e taxas do Tesouro Direto) | `/tesouro`, engine | ODbL (Open Data Commons), declarada no dataset | **OK** — atribuição "Fonte: Tesouro Nacional" |
| BCB SGS (Selic, CDI, IPCA, IGP-M, PTAX) | Faixa, `/mercado`, engine | Portal de dados abertos do BCB (ODbL declarada no catálogo — confirmar na primeira carga) | **OK** — atribuição "Fonte: Banco Central do Brasil" |
| **B3 — COTAHIST, listagem, eventos, carteiras teóricas de índices** | Cotação, histórico, volume, market cap, todos os indicadores que dependem de preço, `/indices` | Termos de uso do site vedam uso comercial sem autorização escrita; Política de Consumo de Market Data 2026 exige licença | **BLOQUEADO em produção até autorização/licença** — [ADR-017](adr/ADR-017-fonte-das-cotacoes.md) |
| **CoinGecko (plano Demo)** | `/cripto`, engine (BTC/ETH/…) | Demo: 100 req/min, 10.000 req/mês, atribuição obrigatória, **sem uso comercial** | **BLOQUEADO em produção** — exige plano pago (Analyst) ou outra fonte |
| Agenda macro (`content/agenda-macro.json`) | `/agenda` | Datas públicas dos calendários oficiais (BCB, IBGE, FGV, Fed, B3) transcritas à mão, com `source_url` | **OK** |
| Provedor internacional | Fase 2 | Contrato de exibição (display) | **PENDENTE** — ADR-019 |

## B3 — o que foi verificado

Documentos (cópias em `fontes-de-dados/`):

1. **Termos de uso do site b3.com.br** (https://www.b3.com.br/pt_br/termos-de-uso-e-protecao-de-dados/termos-de-uso/), lidos em 21/09/2026:
   - "Todo o conteúdo deste website, tais como informações, materiais, instrumentos, gráficos e desenhos, pertencem à B3 ou a terceiros."
   - "É vedada a utilização dos dados contidos neste website para fins comerciais salvo mediante autorização prévia e por escrito da B3."
   - "Os ÍNDICES e quaisquer direitos, inclusive de propriedade intelectual, a eles relacionados pertencem exclusivamente à B3, não podendo ser, de qualquer forma ou por qualquer meio, utilizados por terceiros."
   - "É vedada a distribuição, redistribuição, transferência, transmissão … da Difusão de Dados, exceto mediante prévio e expresso consentimento da B3."
   - A página de **Cotações Históricas** (COTAHIST) não tem termo próprio nem exceção: vale o termo geral do site.
2. **Política de Consumo de Market Data B3 v1.0** (vigente desde 01/01/2026, OC 104/2025-PRE):
   - "Market Data Histórico B3: … qualquer dado ou informação que não seja aquela em Tempo Real ou com Atraso, gerado a partir de informações dos Dados constantes do Market Data B3" — o histórico é tratado como dado da B3, "de titularidade da B3".
   - §2: "É expressamente vedado o uso dos Dados constantes do Market Data B3 em Tempo Real ou Atraso sem a contratação da competente Licença … Qualquer uso …, incluindo o Market Data Histórico B3, que extrapole os termos desta Política … deverá ser objeto de autorização específica e por escrito por parte da B3."
   - §3.3.2: com **Licença de Distribuição em Atraso**, dados podem ser exibidos em "websites abertos … de forma não contínua (snapshot)": último preço/variação, mín/máx/abertura/fim de dia, volume. "Salvo … Licença para Desenvolvimento de Produtos, os Dados … em Atraso, Dados de Fim de Dia B3 e o Market Data Histórico B3 apenas poderão ser utilizados para construção de gráficos e tabelas informacionais, sendo vedados: (i) a comercialização, desenvolvimento de produtos, Distribuição, ou permissão de download …; (ii) o armazenamento com o intuito de desenvolvimento de produtos".
   - §6.3: **Produtizador** (Licença para Desenvolvimento de Produtos) cobre "soluções de análise e inteligência de dados … incluindo em Atraso, Dados de Fim de Dia B3 e o Market Data Histórico B3"; "deverá ser avaliada previamente pela B3 e formalizada por meio de Contrato".
3. **Política Comercial de Market Data B3 — 2026** (tabela de preços, dataset "Mercados Listados", valores nacionais ao mês, por dataset): Distribuição em Tempo Real R$ 6.000 · **Atraso Contínuo R$ 1.920 · Atraso Snapshot R$ 320** · Uso Próprio em Tempo Real R$ 3.200. Não há preço tabelado para Produtizador (é por contrato). "A B3, a seu exclusivo critério, poderá conceder descontos e isenções."
4. Política Comercial anterior (v3.0.4, 15/10/2024, revogada): §7.9 e §7.10 diziam que dados de fim de dia e históricos "podem ser distribuídos sem custo pelos DISTRIBUIDORES ou REDISTRIBUIDORES sem a necessidade de autorização prévia" — sem custo **para quem já tem contrato**. A nova política mantém a lógica: o custo está na licença, não no dado.

**Conclusão:** o arquivo é de download público, mas a B3 não licencia o uso comercial dele sem autorização escrita. O que o Alpherion faz (site aberto com cotação, histórico e indicadores calculados sobre preço; engine de risco; paywall na Fase 2) se enquadra em Distribuição em Atraso Snapshot (exibição) **mais** Produtizador (armazenamento de histórico e análise). Enquadramento e preço só a B3 confirma → [e-mail rascunhado](fontes-de-dados/email-b3-licenca.md). Contato: `contratacao@b3.com.br` · +55 11 2565-5080 · `produtos-marketdata@b3.com.br`.

**O que NÃO depende da B3:** todo o schema `market` vindo da CVM (demonstrações, cadastro, comunicados, informes de FII, fundos), Tesouro, BCB e a agenda macro. Indicadores que **não** usam preço (ROE, ROIC, margens, dívida líquida/EBITDA, liquidez corrente, LPA, VPA, CAGR) podem ser publicados. Indicadores com preço (P/L, P/VP, EV/EBITDA, PSR, DY, market cap) e qualquer cotação/gráfico, não.

## CoinGecko — o que foi verificado

Página de planos da API (21/09/2026): plano **Demo** — 100 chamadas/min, 10.000/mês, "Attribution required" ("prominently display the message 'Data provided by CoinGecko' and include a hyperlink to https://www.coingecko.com/en/api"), **sem licença comercial**; os planos pagos (a partir do Analyst) incluem licença comercial com atribuição e proíbem revenda/redistribuição. Termos: https://www.coingecko.com/en/api_terms.

**Conclusão:** o site é um negócio (funil de assinatura e consultoria; paywall na Fase 2) — o Demo serve para **dev** e nada mais. Opções: (a) CoinGecko Analyst (≈ US$ 129/mês em 21/09/2026, confirmar); (b) API pública de exchange brasileira com termos que permitam exibição (verificar Mercado Bitcoin / Binance); (c) CoinMarketCap tem a mesma restrição no free tier. Decisão junto com o ADR-017 (mesmo problema: "dado gratuito" ≠ "dado licenciado").

## CVM, Tesouro e BCB — o que foi verificado

- **CVM** (`dados.cvm.gov.br`): portal de dados abertos da CVM; conjuntos de cias abertas (FRE, FCA, ITR, DFP, IPE) e fundos (cadastro, informe diário e mensal). Base legal do uso livre: Lei de Acesso à Informação (12.527/2011) e Decreto 8.777/2016 (Política de Dados Abertos do Poder Executivo Federal — art. 4: dados abertos disponibilizados para "livre utilização"). O portal não exibe licença na página inicial; confirmar a licença declarada por conjunto no `dados.gov.br` na primeira carga e registrar em `data_sources`.
- **Tesouro Transparente**: dataset "Taxas dos títulos ofertados pelo Tesouro Direto", publicador CODIP, atualização diária, licença **ODbL** declarada. CSV: `https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/precotaxatesourodireto.csv`.
- **BCB SGS** (`api.bcb.gov.br/dados/serie/bcdata.sgs.{código}/dados`): dados abertos do BCB (catálogo `dadosabertos.bcb.gov.br`, licença ODbL no catálogo — confirmar na primeira carga). Códigos usados documentados em `bcb.py`.

## Regras derivadas (valem para o código)

- Cada linha de `market.data_sources` guarda `license_note` e `terms_checked_at`; o job não roda em produção para fonte com `terms_checked_at` vazio.
- `SourceBadge` usa o texto de atribuição desta tabela; CoinGecko com link obrigatório.
- Feature flag `MARKET_B3_PRICES_ENABLED` (env): com `false`, as páginas de ativo renderizam sem cotação/gráfico/indicadores de preço (mostram "—" com o motivo "cotação indisponível") e `/indices` não é publicada. Só vira `true` com a autorização da B3 registrada aqui.
- Feature flag `MARKET_CRYPTO_ENABLED` (env): idem para `/cripto` e para a classe cripto no engine, até a fonte licenciada.
