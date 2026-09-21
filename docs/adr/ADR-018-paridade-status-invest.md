# ADR-018 — Paridade funcional com o Status Invest em dado público e ferramentas de carteira

- Data: 20/09/2026
- Status: aceita
- Complementa: ADR-010 (pipeline próprio sobre fontes oficiais), ADR-014 (competir em dado e em leitura)
- Abre: ADR-019 (provedor licenciado para dados internacionais — pendente, Fase 2)

## Contexto

O site.md de 19/09 já previa páginas de ativo (ações, FIIs, Tesouro, cripto), screener e comparador. Comparando com o Status Invest — a referência que o público-alvo já usa todo dia — faltavam: busca global e faixa de índices em todas as páginas; home/portal com "o que aconteceu hoje" e "o que vem esta semana"; ETFs, BDRs, índices (com composição), fundos de investimento e setores como páginas; agenda de eventos; comunicados/fatos relevantes por empresa; e, na carteira, rentabilidade por cotização contra benchmarks, calendário de proventos, favoritos, alertas e imposto de renda. Sem isso o visitante orgânico compara, não encontra o que espera e volta para o concorrente antes de conhecer o raio-x.

## Decisão

O site público e o app passam a ter **paridade funcional com o Status Invest naquilo que é dado público atribuído ou ferramenta de carteira**, mantendo o raio-x (as cinco leituras) como o diferencial e o CTA de toda página. A home `/` continua sendo a landing de captura do funil do YouTube; o portal fica em `/mercado`, no header (faixa + busca global) e nas rotas de classe.

**Entra**, nesta ordem (detalhe no site.md §11 e no plano v2.0):

- **v1.0 (09/10/2026):** header com `MarketStrip` e `GlobalSearch`; `/mercado` (Hoje / Eventos); `/agenda`; `/setores`; `/busca`; páginas de ações, FIIs, **ETFs, BDRs, índices com carteira teórica**, Tesouro e cripto; **comunicados CVM (IPE)** por empresa; presets de ordenação por URL com a métrica no título.
- **v1.x:** screener completo; `/carteira/calendario`; `/favoritos` (`localStorage` sem login); ITR e histórico de indicadores; `/carteira/evolucao` e `/carteira/rentabilidade` (TWR × CDI/Ibov/IFIX/IPCA); `/indicadores`; `/conta/alertas`; `/comparar`; informes de FII; **fundos de investimento (CVM)**; `/leitura`.
- **Fase 1:** **imposto de renda** (`/carteira/ir`: apuração mensal por classe, prejuízo a compensar, DARF, relatório anual — cálculo de fato com regras versionadas e disclaimer "não é consultoria tributária").
- **Fase 2:** **internacional** (stocks, REITs) somente com provedor licenciado e receita para pagá-lo (ADR-019).

**Não entra, nunca** (Res. CVM 20, §8.3 e §8.10 do site.md):

- Nota, score, selo, estrelas ou qualquer ranking editorial.
- "Melhores ações/FIIs/fundos", "baratas", "oportunidades", "top 10 para comprar".
- "Preço justo" ou valor intrínseco por fórmula (Graham, Bazin, DCF) sobre o ativo da página; preço-alvo.
- Notícias ou resumo de fato relevante (o site lista título, categoria, data e link para a CVM; não interpreta).
- Raspagem do Status Invest, Fundamentus, Investidor10 ou similares — nem para conferir.

## Alternativas descartadas

- **Manter o escopo de 19/09** (cinco leituras + páginas básicas). Perde o tráfego orgânico de cauda longa (ETFs, BDRs, índices, setores, agenda) e a visita recorrente diária, que é o que sustenta o funil sem depender do canal.
- **Transformar a home em portal** como o Status Invest. Quebra o funil do YouTube (a landing existe para capturar e-mail em 20 segundos) e a Etapa 2 já entregue. A faixa e a busca no header dão o mesmo efeito sem mexer na landing.
- **Lançar em 25/09 com o portal pela metade.** Contradiz a regra "sem 'em breve'": ou a rota existe completa ou não existe. Adiar duas semanas custa menos que abrir com metade do menu.
- **Internacional e fundos via provedor pago já no v1.** Custo mensal antes de receita; fundos têm fonte oficial gratuita (CVM) e entram no v1.x; internacional não tem e espera a Fase 2.

## Consequências

- v1.0 adiado de 25/09 para **09/10/2026**; v1.0 dividido em quatro tags (`v0.2.0` pipeline + páginas, `v0.3.0` portal, `v0.4.0` carteira/B3, `v1.0.0` análise). A Fase 0 (`v0.1.0`, 21/09) não muda.
- Três fontes novas no pipeline: carteiras teóricas de índices da B3 (não documentada — mesma verificação de termos do COTAHIST, ADR-017), CVM IPE (metadados + link, sem baixar documento) e, no v1.x, CVM Fundos (volume alto — partição por ano). Tabelas novas em `market`: `indices`, `index_daily`, `index_compositions`, `company_documents`, `funds`, `fund_daily`, `market_events`. Em `app`: `watchlist_items`, `alerts`, `tax_periods`.
- O header do site público deixa de ser 100 % estático: `MarketStrip` é server component com cache de 5 min e fallback "—"; `GlobalSearch` carrega no foco. Testes de CI garantem zero cookie e o orçamento de JS da landing.
- Alertas são avaliados por um job do `web` (o worker `data` não conhece usuários), lendo a API — a regra "uma API só" continua valendo.
- Um lint de conteúdo no CI bloqueia os termos da lista "não entra" em títulos, `content/` e textos de UI.
- Custo de manutenção do pipeline maior (mais jobs, mais fontes não documentadas). Mitigação: alerta de frescor por job e fallback por fonte.
