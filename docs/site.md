# alpherion.com.br — Especificação do site e do app

> Última atualização: 20/09/2026 (v2 — portal de mercado e paridade funcional com o Status Invest, ADR-018)
> Escopo: site público (landing + conteúdo + portal de dados de mercado), app (consolidador + conexão B3 + análise + ferramentas de carteira) e a API única do Alpherion.
> Este documento é a referência para o repositório de desenvolvimento. O que está aqui e não está no [roadmap](roadmap.md) é detalhe de implementação; se os dois conflitarem, o roadmap manda — exceto onde o roadmap tem nota datada remetendo a este documento.
> Novos módulos entram seguindo a convenção da §14.

---

## 0. Resumo executivo

| Item | Decisão |
| --- | --- |
| Domínios | `alpherion.com.br` (site público: landing, conteúdo, páginas de ativos) · `app.alpherion.com.br` (app) · `api.alpherion.com.br` (API única, uso interno + bot) · `stats.alpherion.com.br` (analytics self-hosted) |
| Frontend | Next.js 15+ (App Router, TypeScript), Tailwind, fontes self-hosted |
| API do Alpherion | Python 3.12 + FastAPI. Reaproveita a lógica de `ferramentas/` (pandas/numpy). Dona do schema `market` (dados de mercado) e do engine de risco. Não conhece usuários |
| Dados de mercado | **Pipeline próprio** (worker Python agendado) sobre fontes **oficiais e gratuitas**: CVM Dados Abertos, B3 COTAHIST, Tesouro Transparente, BCB SGS, CoinGecko. Sem provedor pago; sem Yahoo no produto |
| Conexão B3 | v1: **importação dos arquivos da Área do Investidor** (posição, negociações, proventos). Fase 1: **integração oficial da B3** (usuário autoriza na Área do Investidor; exige contrato com a B3). Nunca raspagem com senha do usuário. O CEI foi desativado em 2021 — o termo não aparece no produto |
| Banco | PostgreSQL 16, dois schemas: `app` (dono = Next.js: usuários, carteiras, movimentações, análises) e `market` (dono = API: cotações, demonstrações, indicadores). Redis para cache, rate limit e fila |
| Auth | Biblioteca self-hosted (Better Auth ou Auth.js): magic link por e-mail + Google. Sem senha no v1 |
| E-mail | Transacional via provedor SMTP (Resend/Postmark/SES). Lista: **Listmonk self-hosted** — a lista é o ativo, fica no nosso banco |
| LLM | Claude API, chamada **só** pela API do Alpherion, com carteira pseudonimizada e saída estruturada + filtro de linguagem de recomendação |
| Infra | VPS própria, Ubuntu 24.04 LTS, Docker Compose, nginx, Cloudflare na frente. Backups criptografados diários fora da VPS |
| Analytics | Umami self-hosted, sem cookie, sem banner |
| Conformidade | LGPD (consentimento com prova, direitos do titular no app, ROPA, plano de incidente), Marco Civil (logs 6 meses), CVM (disclaimer + guardrail no LLM + páginas de dados sem opinião de valor), CDC/Decreto 7.962 (identificação do fornecedor, arrependimento 7 dias no pago), LBI (WCAG 2.1 AA), termos de uso das fontes de dados |
| Escopo do v1 | **v1.0 (lançamento, 09/10/2026):** landing + lista · **portal de mercado** (busca global, faixa de índices no header, `/mercado` com Hoje/Eventos, `/agenda`, `/setores`) · **páginas de ativos** de ações, FIIs, **ETFs, BDRs, índices**, Tesouro e cripto (cotação, histórico, proventos, indicadores, comunicados CVM) · cadastro · carteira manual/CSV/**importação B3** · análise. **v1.x (semanas 4–12):** screener completo, calendário de proventos da carteira, favoritos, ITR, evolução + rentabilidade × benchmarks, glossário, alertas, comparador, informes de FII, **fundos de investimento (CVM)**, leitura semanal. **Fase 1:** B3 oficial + **imposto de renda**. **Fase 2:** pagamento + **internacional** (provedor licenciado). Detalhe na §11; o que entra e o que nunca entra está no ADR-018 |

---

## 1. Papel do site no funil

O site tem três públicos:

1. **Visitante vindo do YouTube.** Quer entender "o que é o Alpherion" em 20 segundos e decidir se entra na lista. → **Landing**: promessa, as cinco leituras, o que não faz, captura de e-mail.
2. **Visitante orgânico** que chega pela página de um ativo (busca "PETR4 dividendos", "MXRF11 P/VP"). Quer o dado. → **Página do ativo**: número, fonte, data — e um CTA contextual: "Tem [TICKER] na carteira? Veja o que ele faz no seu risco." É o motor de SEO e a porta de entrada que não depende do canal.
3. **Usuário cadastrado.** Quer colocar a carteira (à mão, CSV ou arquivos da B3) e apertar o botão. → **App**: fluxo curto, sem distração.
4. **Visitante recorrente** que usa o site como consulta diária (faixa de índices, busca de ticker, agenda de proventos e eventos, setores). É o público do Status Invest; ele volta pelo dado e conhece a leitura pelo CTA de cada página. → **Portal** (`/mercado`, `/agenda`, busca global no header).

**Métricas:** Fase 0 — e-mails confirmados. Fase 1 — carteiras com pelo menos uma análise; visitas orgânicas em páginas de ativo; conversão página de ativo → conta; sessões recorrentes em `/mercado` e `/agenda`; buscas globais por sessão.

### Regras herdadas do canal que valem para o site

- **Diagnóstico ≠ recomendação.** Nenhuma tela, texto, e-mail ou saída de IA indica compra/venda de ativo específico. Disclaimer visível em toda página que fala de carteira ou mercado.
- **Páginas de ativos são fato, não opinião.** Todo número tem fonte e data. Não existe "melhores ações", "top 10 para comprar", nota, score ou selo editorial. O screener ordena pelo critério que **o usuário** escolhe, e a ordem padrão é neutra (alfabética ou por liquidez). Ranking com recomendação implícita é análise (Res. CVM 20).
- **O Alpherion aparece como visão, nunca como obra.** Sem "em construção", sem countdown, sem data de lançamento, sem "beta em breve". A landing diz o que ele faz, o que não faz, e que quem está na lista entra primeiro.
- **Sem promessa de retorno.** A promessa é "você vai saber o que tem". Nunca "ganhe mais", "bata o mercado", "rentabilidade".
- **Ações/FII: educacional. Cripto: opinião com disclaimer.** Isso vale para qualquer texto publicado no site até o CNPI.
- **Todo termo técnico é definido na primeira vez que aparece** (tooltip ou frase). Nas páginas de ativo, todo indicador tem tooltip com definição e link para `/indicadores`.

---

## 2. Mapa do site

### 2.1 Site público — `alpherion.com.br`

#### Landing, conteúdo e legais

| Rota | Página | Objetivo | Renderização | Fase |
| --- | --- | --- | --- | --- |
| `/` | Home / landing | Captura de e-mail. Hero + as cinco leituras + o que não faz + últimos vídeos + FAQ | SSG | 0 |
| `/lista/confirmar?t=` | Confirmação de e-mail (double opt-in) | Confirma o token, marca `confirmed_at`, mostra "próximo passo" (inscrever-se no canal) | SSR | 0 |
| `/lista/obrigado` | Pós-cadastro | "Verifique seu e-mail". Instruções anti-spam | SSG | 0 |
| `/lista/sair?t=` | Descadastro em 1 clique | Obrigatório (LGPD art. 18 IX; CAPEM). Sem login, sem "tem certeza?" | SSR | 0 |
| `/raio-x` | O que é o raio-x de carteira | Explica as cinco leituras com o exemplo do vídeo 02 (carteira do "Rafael"). Prévia estática da análise | SSG | 0 |
| `/sobre` | Sobre / quem faz | Bryan, formação, o caminho regulatório (CNPI em andamento) dito com transparência, a tese | SSG | 0 |
| `/videos` | Vídeos por quadro | Lista dos vídeos (Leitura / Raio-X / Tese), embed com `youtube-nocookie.com` e carregamento sob clique | ISR | 0 |
| `/leitura` · `/leitura/[slug]` | Arquivo da Leitura de Mercado | Versão texto da Leitura semanal: números do `leitura-semanal.py` + comentário. SEO de cauda longa e hábito | ISR | 1 |
| `/manifesto` | A tese | Versão texto do vídeo 03 | SSG | 1 |
| `/privacidade` | Política de Privacidade | Ver §8 | SSG | 0 |
| `/termos` | Termos de Uso | Ver §8 | SSG | 0 |
| `/aviso-legal` | Aviso legal / disclaimer CVM | Ver §8.3 | SSG | 0 |
| `/contato` | Contato, canal do encarregado (LGPD) e correção de dados | E-mail de contato, de privacidade e de "encontrei um erro no dado". Sem formulário no v1 | SSG | 0 |
| `/planos` | Planos e preços | Só na Fase 2, com pagamento | SSG | 2 |
| `/sitemap.xml` · `/robots.txt` · `/manifest.webmanifest` | Técnicas | Geradas pelo Next; sitemap segmentado (`/sitemap/acoes.xml` etc.) | — | 0 |

#### Header do site público (todas as páginas de `alpherion.com.br`)

- **`MarketStrip`** — faixa com Ibovespa · IFIX · dólar (PTAX) · CDI 12 m · BTC (valor, variação do dia, hora da fonte). Server component lendo `GET /v1/market/strip` com revalidação de 300 s; se a API não responder, a faixa mostra "—" e a página continua estática. Zero JS no cliente.
- **`GlobalSearch`** — busca de ações, FIIs, ETFs, BDRs, índices, títulos do Tesouro, criptoativos e (v1.x) fundos. Client component carregado **no foco** do campo (não entra no JS inicial da landing); chama `app/api/market/search` (route handler com rate limit por IP) → `GET /v1/assets/search`. Enter sem seleção → `/busca?q=`.
- **Menu**: Ações · FIIs · ETFs · BDRs · Índices · Tesouro · Cripto · Setores · Agenda · Raio-X · Vídeos. No app, o header é o do app (§2.2).
- Regras: zero cookie (§8.5), orçamento de JS da landing mantido (§9), números tabulares, variação com sinal + cor semântica (§5).

#### Dados de mercado (todas ISR; revalidação após o fechamento do dia, cripto a cada hora)

| Rota | Página | O que mostra | Fase |
| --- | --- | --- | --- |
| `/mercado` | Portal de mercado | **Faixa completa:** Ibovespa, IFIX, IDIV, SMLL, dólar (PTAX), Selic, CDI 12 m, IPCA 12 m, BTC em BRL. **Blocos por classe** com contadores factuais e link: ações (nº de empresas listadas, nº de setores), FIIs (nº de fundos, nº de segmentos), ETFs, BDRs, índices, Tesouro (nº de títulos), cripto (nº acompanhados). **Tab Hoje:** maiores altas, maiores baixas e mais negociadas por volume financeiro — cada lista com a métrica no título e filtro de liquidez mínima. **Tab Eventos:** data-com e pagamentos do dia/semana, comunicados relevantes do dia (CVM), agenda macro (Copom, IPCA, FOMC, vencimento de opções). Busca global em destaque. Fonte e horário em cada bloco | v1.0 |
| `/busca?q=` | Resultado da busca global | Resultados agrupados por classe (ações, FIIs, ETFs, BDRs, índices, Tesouro, cripto, fundos), com cotação e link. SSR, `noindex` | v1.0 |
| `/acoes` | Lista / screener de ações | Tabela de todas as ações e units da B3 (BDRs e ETFs entram no catálogo como "outros" sem página própria no v1). Filtros: setor/subsetor, liquidez, P/L, P/VP, DY, ROE, dív. líq./EBITDA, market cap. Ordenação escolhida pelo usuário; padrão = liquidez. Sem "recomendado" | v1.0 básico (lista + busca) · v1.x filtros |
| `/acoes/[ticker]` | Página da ação | **Cabeçalho:** cotação, variação do dia, mín/máx 52 s, volume, market cap, fonte e data. **Gráfico:** 1M · 6M · 1A · 5A · máx, ajustado por proventos e eventos. **Indicadores** (tooltip + fonte): valuation — P/L, P/VP, EV/EBITDA, EV/EBIT, PSR, DY 12m, payout; rentabilidade — ROE, ROIC, ROA, margem bruta/EBITDA/líquida; endividamento — dív. líq./EBITDA, dív. líq./PL, liquidez corrente; crescimento — receita e lucro (CAGR 5a); por ação — LPA, VPA. **Demonstrações:** DRE, balanço e fluxo de caixa resumidos, anual (DFP) e trimestral (ITR), toggle. **Proventos:** tabela (tipo, data-com, pagamento, valor por ação) e gráfico por ano. **Eventos:** desdobramentos, grupamentos, bonificações, subscrições **e próximos data-com/pagamentos** anunciados. **Comunicados:** fatos relevantes, comunicados ao mercado, avisos aos acionistas e calendário de eventos corporativos entregues à CVM (título, categoria, data, link para o documento na CVM — sem resumo nem opinião). **Cadastro:** razão social, CNPJ, setor/subsetor/segmento B3, segmento de listagem, free float, tag along, site de RI. **Mesmo setor:** empresas do mesmo segmento B3 com cotação e liquidez (link para `/setores/[slug]`). **CTA:** "Tem [TICKER] na carteira?" → app | v1.0 (cotação, histórico, proventos, indicadores de valuation e rentabilidade a partir da DFP, eventos, comunicados, cadastro) · v1.x (trimestral, fluxo de caixa, crescimento, histórico de indicadores) |
| `/fiis` | Lista / screener de FIIs | Filtros: segmento (tijolo/papel/híbrido/fof), DY 12m, P/VP, liquidez, patrimônio. Mesma regra de ordenação | v1.0 básico · v1.x filtros |
| `/fiis/[ticker]` | Página do FII | Cotação, DY 12m, P/VP, patrimônio líquido e por cota, vacância física/financeira (quando informada), nº de cotistas, segmento, gestor/administrador, taxa de administração, rendimentos mensais (tabela + gráfico), informes mensais/trimestrais (link para o documento na CVM/B3), imóveis/ativos (quando no informe). CTA | v1.0 (cotação, DY, P/VP, rendimentos) · v1.x (informes, vacância, imóveis) |
| `/tesouro` | Tesouro Direto | Tabela dos títulos disponíveis: nome, vencimento, taxa de compra, taxa de venda, preço unitário, atualizado em | v1.0 |
| `/tesouro/[slug]` | Página do título | Histórico de taxa e preço, duration/vencimento, como funciona aquele indexador (uma frase), marcação a mercado explicada (link para o vídeo 09) | v1.0 |
| `/cripto` | Criptoativos | Top N por market cap em BRL: preço, 24h, 7d, market cap, volume, dominância do BTC | v1.0 |
| `/cripto/[id]` | Página do cripto | Preço em BRL e USD, histórico (1M–máx), market cap, volume, oferta circulante/máxima, ATH e distância do ATH, **correlação 30/90d com BTC, Ibovespa e dólar** (ponte com o Radar de risco do canal). CTA | v1.0 |
| `/etfs` · `/etfs/[ticker]` | ETFs listados na B3 | Lista (nome, índice de referência, gestor, cotação, variação, volume, patrimônio quando informado) e página: cotação, histórico, volume, taxa de administração, índice replicado (link para `/indices/[slug]` quando houver), proventos (quando distribui). CTA | v1.0 |
| `/bdrs` · `/bdrs/[ticker]` | BDRs | Lista (empresa, país, cotação, variação, volume) e página: cotação em BRL, histórico, volume, proventos, paridade (n BDRs por ação) e emissor/depositário. Sem dados fundamentalistas da empresa estrangeira no v1 (não há fonte oficial gratuita — §8.10) | v1.0 |
| `/indices` · `/indices/[slug]` | Índices da B3 | Lista (Ibovespa, IFIX, IDIV, SMLL, IBRX 100, IBRA, IFNC, IMOB, UTIL…) com valor, variação do dia/mês/ano. Página: histórico, **composição da carteira teórica** (ticker, participação %, quantidade teórica, data da carteira), setores mais representados como fato agregado, link para cada ativo. Sem previsão | v1.0 |
| `/setores` · `/setores/[slug]` | Setores e segmentos | Árvore setor → subsetor → segmento da classificação B3 e segmentos de FII (tijolo/papel/híbrido/fof). Página do setor: empresas/fundos com cotação, variação, liquidez, P/L, P/VP, DY 12 m, market cap; ordenação escolhida pelo usuário, padrão liquidez; agregados factuais (nº de empresas, market cap somado). Links internos em toda página de ativo | v1.0 |
| `/agenda` · `/agenda/[ano]-[semana]` | Agenda de eventos | Calendário semanal (e mensal) com: proventos (data-com, pagamento, valor por ação, tipo), comunicados relevantes entregues à CVM (por dia), eventos macro (Copom, IPCA, IGP-M, PTAX, FOMC, vencimento de opções e índices — de `content/agenda-macro.json`, com fonte). Filtros por classe e tipo; página do dia por âncora. Só fatos com data e fonte | v1.0 |
| `/fundos` · `/fundos/[slug]` | Fundos de investimento (CVM) | Lista com busca (nome, CNPJ, classe CVM, gestor) e página: cota do dia, patrimônio líquido, nº de cotistas, rentabilidade mês/ano/12 m/24 m como fato com a série ao lado, taxa de administração/performance, classe, público-alvo, gestor/administrador, histórico da cota. Slug = CNPJ numérico. Sem "melhores fundos" nem estrelas | v1.x |
| `/internacional` | Stocks e REITs | Só com provedor licenciado (ADR-019); entra na Fase 2 com o paywall. Até lá a rota **não existe** (sem "em breve") | Fase 2 |
| `/indicadores` · `/indicadores/[slug]` | Glossário de indicadores | Um por página: definição em uma frase, fórmula, de onde vem o dado, como o canal lê, limitações. É o destino dos tooltips | v1.x (v1.0 só tooltips) |
| `/comparar?a=&b=&c=` | Comparador | 2–4 ativos da mesma classe lado a lado: indicadores, proventos, histórico normalizado. Só fatos; sem veredito, sem "vencedor" | v1.x |

**Rankings:** não existe rota "ranking". Listas ordenadas são (a) as tabs de `/mercado` (altas, baixas, volume) e (b) **presets do screener por URL** (`/acoes?sort=dy_12m&dir=desc`, `/fiis?sort=pvp&dir=asc`), sempre com a métrica no título ("Maior dividend yield 12 m") e nunca com juízo ("melhores", "baratas", "oportunidades"). Regra da §8.10.

**Redirecionamentos:** `www.` → apex (301). `/entrar`, `/cadastro`, `/carteira` no domínio público → `app.alpherion.com.br`. Ticker em minúsculas → maiúsculas (301). Ticker inexistente → 404 com busca. `/acoes/[ticker]` de um ETF/BDR/FII → 301 para a rota da classe certa.

### 2.2 App — `app.alpherion.com.br`

| Rota | Tela | O que faz | Fase |
| --- | --- | --- | --- |
| `/entrar` | Login | E-mail (magic link) ou Google. Aceite de Termos + Privacidade com checkbox **não pré-marcado**. Sem cadastro separado: o primeiro login cria a conta | v1.0 |
| `/entrar/verificar` | "Verifique seu e-mail" | Após pedir o magic link | v1.0 |
| `/` | Painel | Redireciona: sem carteira → `/carteira/nova`; com carteira → `/carteira` | v1.0 |
| `/carteira` | Posições | Tabela de posições (derivadas de movimentações + ajustes): quantidade, preço médio, preço atual, valor, peso, resultado, classe. Botões: adicionar, importar, **Analisar** | v1.0 |
| `/carteira/nova` | Onboarding | Passo 1 nome da carteira; passo 2: "Tem conta na B3? Importe da Área do Investidor" · "Adicionar à mão" · "CSV" | v1.0 |
| `/carteira/importar` | Importar CSV genérico | Upload, prévia com mapeamento de colunas, confirmação. Modelo de CSV para download | v1.0 |
| `/carteira/importar/b3` | Importar da B3 (Área do Investidor) | Passo a passo com prints de onde exportar (Extratos → Posição / Negociação / Proventos → Excel). Upload de 1–3 arquivos, prévia normalizada (ativo, data, tipo, quantidade, preço), avisos por linha, **dedupe** por hash de arquivo e por (ativo, data, tipo, qtd, preço), confirmação. Nada do arquivo é guardado | v1.0 |
| `/carteira/movimentacoes` | Compras e vendas | Lista de transações (importadas ou manuais), edição, preço médio por ativo, custo total, taxas | v1.0 |
| `/carteira/proventos` | Proventos recebidos | Dividendos, JCP e rendimentos por mês e por ativo; total 12m; **yield on cost** como fato | v1.0 |
| `/carteira/evolucao` | Evolução | Patrimônio ao longo do tempo (a partir das movimentações + cotações históricas), aportes × valorização, comparação com CDI e Ibovespa como referência de fato (sem promessa) | v1.x |
| `/carteira/rentabilidade` | Rentabilidade | Rentabilidade da carteira por **cotização** (TWR — independe do momento dos aportes) por mês, ano e 12 m, lado a lado com CDI, Ibovespa, IFIX e IPCA no mesmo período, por classe e por ativo. Fato histórico com fonte; sem projeção | v1.x |
| `/carteira/calendario` | Calendário da carteira | Proventos **anunciados** dos ativos em carteira (data-com, pagamento, valor por ação × quantidade na data-com = valor estimado a receber), comunicados relevantes e eventos corporativos desses ativos, macro. Mês corrente + próximos; total estimado por mês | v1.x |
| `/favoritos` | Lista de acompanhamento | Ativos marcados com ★ nas páginas públicas. Sem login: `localStorage` do navegador (não é cookie, não sai do dispositivo). Com login: tabela `watchlist_items`, sincronizada no primeiro acesso com aviso. Tabela com cotação, variação, DY, P/VP e link | v1.x |
| `/conta/alertas` | Alertas | Por ativo: preço acima/abaixo de X, provento anunciado, comunicado relevante entregue. Canal: e-mail (Telegram na Fase 1). Limite por usuário; descadastro de cada alerta no próprio e-mail | v1.x |
| `/carteira/ir` | Imposto de renda | Apuração **mensal** por classe a partir das movimentações: ações (isenção de vendas até R$ 20 mil/mês, 15 % / 20 % day trade), FIIs (20 %), ETFs, BDRs, cripto (isenção até R$ 35 mil/mês), prejuízo a compensar por classe, valor do DARF (código, vencimento) e relatório anual (bens e direitos com custo, rendimentos isentos/tributáveis). **É cálculo de fato pelas regras vigentes, com `tax_rules_version`; não é consultoria tributária** — disclaimer próprio e link para a fonte (RFB). Só quando há histórico completo de movimentações | Fase 1 |
| `/analise/[id]` | Resultado | As cinco leituras em cards + texto do Alpherion em português + disclaimer fixo + "o que isso não é" | v1.0 |
| `/analises` | Histórico | Lista de análises anteriores (data, carteira, resumo) | v1.0 |
| `/conta` | Conta | E-mail, nome (opcional), sessões ativas, **exportar meus dados** (JSON), **excluir conta**, consentimentos | v1.0 |
| `/conta/integracoes` | Integrações | **Conexão B3 oficial:** botão "Conectar" → autorização na Área do Investidor → status, última sincronização, escopo (somente leitura), **revogar**. Exchanges/wallets com chave read-only | Fase 1 |
| `/conta/plano` | Assinatura | Status, faturas, cancelar em 1 clique | 2 |

Fluxo mínimo do v1.0: **entrar → importar da B3 (ou 3 posições à mão) → Analisar → ler**. Tem que caber em 3 minutos na primeira vez; é isso que o vídeo 03 demonstra.

### 2.3 API única — `api.alpherion.com.br`

A API do Alpherion é o **único** lugar onde existe cálculo de risco, dado de mercado e chamada de LLM. O app Next.js, o bot do Telegram (futuro) e a produção de research (futuro) são clientes dela. Se um deles precisar de uma conta que a API não faz, a conta entra na API — nunca no cliente. O `web` **nunca lê o schema `market` direto no banco**: passa pela API.

Auth de todos os endpoints: token de serviço (`Authorization: Bearer`), um por cliente (web, bot), com escopo. `GET /v1/health` é a exceção (só rede interna).

#### Análise e carteira

| Método e rota | O que faz | Fase |
| --- | --- | --- |
| `POST /v1/analyses` | Recebe `{positions: [{symbol, asset_class, quantity \| value_brl, avg_price?}], income_12m?, reference_date?, options}` → devolve as cinco leituras (JSON) + narrativa em pt-BR + `disclaimer` + `model_meta` | v1.0 |
| `POST /v1/portfolios/valuation` | Posições/movimentações → valor atual, preço médio, resultado por ativo e total, peso. Usado por `/carteira` | v1.0 |
| `POST /v1/portfolios/evolution` | Movimentações → série diária de patrimônio, aportes, valorização, CDI e Ibov no mesmo período | v1.x |
| `POST /v1/portfolios/performance` | Movimentações → rentabilidade por cotização (TWR) por período, por classe e por ativo, com CDI, Ibovespa, IFIX e IPCA no mesmo período | v1.x |
| `POST /v1/portfolios/income-calendar` | Posições → proventos anunciados (data-com futura ou pagamento futuro) × quantidade na data-com, comunicados e eventos dos ativos | v1.x |
| `POST /v1/portfolios/tax` | Movimentações do ano → apuração mensal por classe, prejuízo a compensar, DARF, relatório anual. Regras versionadas (`tax_rules_version`) | Fase 1 |
| `POST /v1/imports/csv/preview` | CSV genérico → linhas parseadas + erros por linha | v1.0 |
| `POST /v1/imports/b3/preview` | Arquivos da Área do Investidor (xlsx/csv) → transações e proventos normalizados + avisos. **Descarta CPF/nome no parser** | v1.0 |
| `GET /v1/assets/search?q=&type=` | Busca global (autocomplete): ações, FIIs, ETFs, BDRs, índices, Tesouro, cripto e (v1.x) fundos; resultado agrupado por classe. Usada pelo header do site e pelo app | v1.0 |

#### Dados de mercado

| Método e rota | O que faz | Fase |
| --- | --- | --- |
| `GET /v1/market/overview` | Índices, câmbio, juros, inflação, BTC, contadores por classe, altas/baixas/volume do dia, eventos do dia | v1.0 |
| `GET /v1/market/strip` | Faixa do header: Ibovespa, IFIX, PTAX, CDI 12 m, BTC — resposta mínima, cache 5 min | v1.0 |
| `GET /v1/market/movers?metric=change\|volume&dir=&type=&min_volume=` | Listas do dia ordenadas por uma métrica (fato); campos de lista fechada | v1.0 |
| `GET /v1/market/events?from=&to=&kind=&type=&ticker=` | Agenda: proventos (data-com/pagamento), documentos CVM, macro. Base de `/agenda`, da tab Eventos e do calendário da carteira | v1.0 |
| `GET /v1/sectors` · `GET /v1/sectors/{slug}?sort=&page=` | Árvore setor/subsetor/segmento (B3 e FII) e ativos do setor com cotação/indicadores | v1.0 |
| `GET /v1/indices` · `GET /v1/indices/{slug}` · `/composition?date=` · `/history?range=` | Índices, carteira teórica (com data) e histórico | v1.0 |
| `GET /v1/securities?type=stock\|fii\|etf\|bdr&filters…&sort=&page=` | Screener. Filtros e ordenação validados contra lista fechada de campos | v1.0 (busca/lista/presets de ordenação) · v1.x (filtros) |
| `GET /v1/securities/{ticker}` | Perfil + indicadores atuais + cadastro + fonte/data de cada bloco | v1.0 |
| `GET /v1/securities/{ticker}/history?range=&adjusted=` | OHLCV diário, ajustado ou não | v1.0 |
| `GET /v1/securities/{ticker}/dividends` | Proventos e eventos corporativos | v1.0 |
| `GET /v1/securities/{ticker}/events?from=` | Próximos data-com/pagamentos e eventos corporativos anunciados | v1.0 |
| `GET /v1/securities/{ticker}/documents?category=&page=` | Comunicados entregues à CVM (IPE): categoria, assunto, data, link. Sem texto do documento | v1.0 |
| `GET /v1/securities/{ticker}/financials?period=annual\|quarterly` | DRE/BP/FC resumidos | v1.0 anual · v1.x trimestral |
| `GET /v1/securities/{ticker}/indicators/history` | Série dos indicadores (P/L, DY etc.) | v1.x |
| `GET /v1/fiis/{ticker}/reports` | Informes mensais/trimestrais | v1.x |
| `GET /v1/treasury` · `GET /v1/treasury/{slug}/history` | Títulos e histórico | v1.0 |
| `GET /v1/crypto` · `GET /v1/crypto/{id}` · `/history` · `/correlations` | Cripto e correlações | v1.0 |
| `GET /v1/compare?tickers=` | Comparador (ações, FIIs, ETFs, BDRs, fundos — mesma classe) | v1.x |
| `GET /v1/funds?q=&class=&sort=&page=` · `GET /v1/funds/{cnpj}` · `/history?range=` | Fundos de investimento (CVM): cadastro, cota, PL, cotistas, rentabilidade como fato | v1.x |
| `GET /v1/quotes?symbols=` | Cotações atuais em BRL (cache) — usado pelo app | v1.0 |
| `POST /v1/market/weekly-reading` | Números da Leitura de Mercado (mesmo cálculo do `leitura-semanal.py`) — interno | v1.0 |

Contrato de resposta do `POST /v1/analyses` (o app renderiza isso; o bot resume):

```json
{
  "analysis_id": "uuid",
  "reference_date": "2026-09-18",
  "total_brl": 120000,
  "readings": {
    "concentration": { "top1": {"symbol": "BTC", "weight": 0.38}, "top3": 0.58, "top5": 0.73, "hhi": 0.189, "effective_n": 5.3, "by_class": {"Cripto": 0.50} },
    "correlation":   { "window_days": 365, "symbols": ["BTC", "ETH"], "matrix": [[1, 0.91], [0.91, 1]], "clusters": [["BTC", "ETH", "SOL"]] },
    "exposure":      { "factors": {"Cripto": 0.50, "Juros BR": 0.22}, "sensitivity": {"BTC": {"beta": 0.54, "corr": 0.96}} },
    "drawdown":      { "max": -0.344, "peak_date": "2025-10-06", "trough_date": "2026-06-05", "current": -0.21, "worst_month": {"month": "2025-02", "ret": -0.152}, "vol_annual": 0.279 },
    "liquidity":     { "per_position": [{"symbol": "MXRF11", "pct_of_daily_volume": 0.0003, "days_to_exit": 1}], "settlement": {"crypto": "24/7", "b3": "D+2", "tesouro": "D+1"} },
    "cost":          { "per_position": [{"symbol": "PETR4", "avg_price": 41.2, "price": 48.5, "result_pct": 0.177}], "income_12m_brl": 3120, "yield_on_cost": 0.041 }
  },
  "narrative": { "summary": "...", "by_reading": {"concentration": "..."}, "questions_for_you": ["..."] },
  "warnings": ["SOL: histórico de apenas 2 anos, correlação calculada em janela menor"],
  "disclaimer": "Este diagnóstico é uma leitura de risco...",
  "model_meta": { "engine_version": "1.3.0", "prompt_version": "2026-09-15", "llm": "<id do modelo>", "narrative_filtered": false }
}
```

Regra: `readings` é 100% determinístico (pandas). `narrative` é o LLM explicando `readings` — **o LLM nunca calcula nada e nunca recebe dado que não esteja em `readings`**. `cost` só aparece quando há movimentações com preço.

---

## 3. Arquitetura

### 3.1 Visão geral

```
                 ┌────────────────── Cloudflare (DNS, proxy, WAF, TLS de borda, cache das páginas de ativo) ──────────────────┐
                 │                                                                                                            │
 usuário ─HTTPS─►│  alpherion.com.br · app.alpherion.com.br · api.alpherion.com.br · stats.* · news.*                          │
                 └───────────────────────────────────┬────────────────────────────────────────────────────────────────────────┘
                                                     │ só IPs da Cloudflare (ufw) · TLS Full (strict) · Authenticated Origin Pulls
                                          ┌──────────▼──────────┐
                                          │  nginx (VPS)        │  TLS de origem, headers de segurança, rate limit básico, brotli
                                          └──┬──────┬──────┬───┘
                 ┌───────────────────────────┘      │      └────────────────────────────┐
          ┌──────▼──────┐                   ┌───────▼───────┐                     ┌──────▼──────┐
          │ web (Next)  │ ─token de serviço─►│ api (FastAPI) │ ─HTTPS─► Claude API │ umami       │
          │ site + app  │                   │ risco + dados │                     │ listmonk    │
          └──────┬──────┘                   │ + LLM         │                     └──────┬──────┘
                 │                          └───────┬───────┘                            │
                 │                                  │      ┌───────────────┐             │
                 │                                  │      │ data (worker) │ ─HTTPS─► CVM Dados Abertos · B3 COTAHIST/eventos
                 │                                  │      │ jobs agendados│ ─HTTPS─► Tesouro Transparente · BCB SGS · CoinGecko
                 │                                  │      └───────┬───────┘
          ┌──────▼──────────────────────────────────▼──────────────▼─────────────────────────────▼──────┐
          │  postgres 16 — schemas: app (web) · market (api + data) · bancos: umami, listmonk            │
          │  redis — cache de cotação/páginas, rate limit, fila                                          │
          └──────────────────────────────────────────────────────────────────────────────────────────────┘
                                                     │
                                       backup diário (pg_dump → age → storage externo)
```

Tudo roda em **uma rede Docker interna**; só o nginx publica portas (80/443). Postgres e Redis não têm porta no host. O worker `data` não tem rota HTTP e não enxerga o schema `app`.

### 3.2 Por que três serviços (Next + FastAPI + worker) e não um

- A lógica de risco já existe em Python (`ferramentas/raio-x-carteira.py`, `leitura-semanal.py`, `mercado.py`) e depende de pandas/numpy. Reescrever em TS custa dias e cria divergência entre o número do vídeo e o número do produto — exatamente o que não pode acontecer. O pipeline de dados (parse de COTAHIST, DFP/ITR da CVM, cálculo de indicadores) também é trabalho de pandas.
- "Uma API só": o bot do Telegram e a produção de research vão chamar a mesma API. Se a análise ou o dado morassem dentro do Next, o bot viraria um segundo backend.
- O Next fica dono de **usuários, sessões, carteiras, movimentações e histórico** (schema `app`). A API fica dona de **dados de mercado, cálculo e LLM** (schema `market`) e não sabe quem é o usuário: recebe posições, devolve leitura. Isso é também a fronteira de privacidade: a API, o worker e o LLM nunca veem e-mail ou nome.
- O worker `data` é o mesmo pacote Python da API rodando como processo separado (container `data`), para que a carga de um arquivo de 200 MB da CVM não trave a API que serve o site.

### 3.3 Repositório de desenvolvimento (monorepo)

```
alpherion/
├── apps/
│   ├── web/                    # Next.js — site público + app
│   │   ├── app/
│   │   │   ├── (site)/         # rotas públicas: /, /raio-x, /sobre, /videos, /leitura, legais
│   │   │   ├── (market)/       # /mercado, /acoes, /fiis, /tesouro, /cripto, /indicadores, /comparar
│   │   │   ├── (app)/          # rotas autenticadas: /carteira/*, /analise, /analises, /conta/* (middleware exige sessão)
│   │   │   ├── (auth)/         # /entrar
│   │   │   └── api/            # route handlers: /api/subscribe, /api/auth/*, /api/portfolio/*, /api/imports/*, /api/analyses
│   │   ├── components/         # ui/ (primitivos), site/, market/, app/
│   │   ├── lib/                # db (drizzle), auth, api-client, email, validation (zod), rate-limit, crypto, positions (derivação)
│   │   ├── content/            # MDX: leituras, manifesto, glossário de indicadores, páginas legais (versionadas)
│   │   ├── drizzle/            # schema + migrations do schema app
│   │   └── public/             # brand, og, csv-modelo.csv, prints do passo a passo da B3
│   └── api/                    # FastAPI — API do Alpherion + worker data
│       ├── alpherion/
│       │   ├── engine/         # concentration.py, correlation.py, exposure.py, drawdown.py, liquidity.py, cost.py (portados de ferramentas/)
│       │   ├── market/         # leitura do schema market: quotes.py, securities.py, indicators.py, treasury.py, crypto.py, overview.py
│       │   ├── data/           # pipeline (worker)
│       │   │   ├── sources/    # cvm.py (DFP/ITR/FRE/FCA/cadastro/FII), b3_cotahist.py, b3_events.py, tesouro.py, bcb.py, coingecko.py
│       │   │   ├── transform/  # cotahist_parser.py (layout posicional), cvm_statements.py (formato longo), adjust.py (fator de ajuste), indicators.py (fórmulas)
│       │   │   ├── jobs/       # um módulo por job; idempotentes; registram em etl_runs
│       │   │   └── scheduler.py
│       │   ├── importers/      # b3/ (parsers dos arquivos da Área do Investidor: posicao.py, negociacao.py, proventos.py), csv.py
│       │   ├── narrative/      # prompts/ (versionados), client.py (Claude), guard.py (filtro de recomendação), schemas.py
│       │   ├── routers/        # analyses.py, portfolios.py, imports.py, securities.py, fiis.py, treasury.py, crypto.py, market.py, assets.py, health.py
│       │   ├── db/             # SQLAlchemy 2 + Alembic para o schema market
│       │   └── settings.py
│       ├── tests/              # golden tests: carteira do vídeo 02 (38% / 0,91 / 0,96 / −34,4%); parsers com arquivos de exemplo anonimizados; fórmulas de indicadores contra casos conhecidos
│       └── pyproject.toml
├── infra/
│   ├── compose.yml             # produção: nginx, web, api, data, postgres, redis, umami, listmonk, uptime-kuma
│   ├── compose.dev.yml         # local
│   ├── nginx/                  # sites/*.conf, snippets/security-headers.conf, snippets/cloudflare-real-ip.conf, snippets/cache-market.conf
│   ├── scripts/                # bootstrap-vps.sh, deploy.sh, backup.sh, restore-test.sh, update-cloudflare-ips.sh, backfill-market.sh
│   └── env/                    # .env.example (nunca .env)
├── docs/                       # ADRs, runbooks (incidente, restore, rotação de chave, reprocessar job), ropa.md, dpa/, fontes-de-dados.md (licenças e termos)
├── .github/workflows/          # ci.yml (lint, test, build) · deploy.yml (build imagem → GHCR → ssh deploy)
└── README.md
```

### 3.4 Stack detalhada

| Camada | Escolha | Motivo / observação |
| --- | --- | --- |
| Framework web | Next.js 15+ App Router, TypeScript strict, React Server Components | SSG/ISR para o site e páginas de ativo, server actions/route handlers para o app. Um deploy só |
| Estilo | Tailwind CSS + tokens do brand kit (§5). Componentes próprios ou shadcn/ui (copiados para o repo, não dependência) | Sem UI kit pesado. Tema escuro é o padrão da marca |
| Gráficos | Biblioteca leve, renderizada no cliente só quando visível (`HistoryChart`, `DrawdownChart`); tabela como fallback acessível | Páginas de ativo precisam ser leves: o gráfico não pode custar o LCP |
| Fontes | Playfair Display + Inter via `next/font/local` (arquivos no repo) | Sem requisição ao Google Fonts (evita transferência de IP a terceiro e melhora LCP) |
| Validação | zod (web) · pydantic v2 (api) | Toda entrada de usuário passa por schema antes de tocar banco ou API. Filtros do screener validados contra lista fechada |
| ORM | Drizzle (web, schema `app`) · SQLAlchemy 2 + Alembic (api, schema `market`) | Migrations versionadas, revisadas em PR. Cada serviço migra só o seu schema |
| Auth | Better Auth (ou Auth.js v5). Magic link + Google OAuth. Sessão em cookie `HttpOnly; Secure; SameSite=Lax`, rotacionada, TTL 30 dias com sliding | Self-hosted: os dados de login ficam no nosso Postgres. Sem senha no v1 = sem vazamento de hash, sem reset. 2FA (TOTP/passkey) na Fase 2 junto com pagamento |
| E-mail transacional | Provedor SMTP/API com região ou DPA (Resend, Postmark ou Amazon SES `sa-east-1`) | Magic link, confirmação de lista, aviso de exclusão. SES em São Paulo evita transferência internacional |
| Lista de e-mail | Listmonk (self-hosted, Postgres próprio) enviando pelo mesmo SMTP, em subdomínio `news.alpherion.com.br` | A lista é **o ativo** do projeto — não fica em SaaS. Double opt-in nativo, unsubscribe em 1 clique, exportável |
| Dados de mercado | **Pipeline próprio** (§3.5) sobre fontes oficiais. Cache em Redis (cotação 5 min; páginas de ativo até a próxima carga) e na Cloudflare (`s-maxage` de 1 h nas páginas públicas) | Sem provedor pago; sem Yahoo no produto (fica só nas ferramentas de vídeo). Fallback licenciado (brapi) só se os termos da B3 exigirem — ver §8.10 |
| LLM | Claude API, chamado apenas pela API do Alpherion (§6) | Saída estruturada (JSON), temperatura baixa, prompt versionado, custo por análise registrado. Modelo: o mais econômico da família atual que passe nos testes do guard — consultar a documentação de modelos ao implementar |
| Cache / fila | Redis 7 | Cache, rate limit por IP/usuário, e fila (arq) para importações grandes. Análise síncrona com timeout de 30 s |
| Agendamento | Scheduler no container `data` (APScheduler) ou cron do host chamando `python -m alpherion.data.jobs.<job>` | Preferir cron do host: mais simples de inspecionar e reexecutar à mão. Jobs idempotentes, com lock no Redis |
| Analytics | Umami self-hosted | Sem cookie, sem PII, IP anonimizado. Dispensa banner. Eventos: `subscribe_submit`, `subscribe_confirm`, `analysis_run`, `b3_import`, `asset_cta_click` |
| Erros | GlitchTip self-hosted (compatível com SDK do Sentry) ou Sentry SaaS com `sendDefaultPii: false` e scrubbing | Nunca enviar e-mail, posições, arquivos ou tokens no evento |
| Uptime | Uptime Kuma na VPS (ou externo gratuito) com alerta no Telegram | Checa `/`, `/entrar`, `/acoes/PETR4`, `api /v1/health`, e **frescor dos dados** (`etl_runs` do dia) |
| Logs | stdout dos containers → journald (Loki opcional). Retenção: app 30 dias; **registros de acesso 6 meses** (Marco Civil) | Formato JSON, sem PII além do necessário (IP + timestamp + rota + hash do user_id) |
| CI/CD | GitHub Actions: lint + typecheck + testes + build; imagem → GHCR; deploy por SSH (`docker compose pull && up -d`) | Deploy por tag (`v1.2.3`). Sem zero-downtime no v1 |

### 3.5 Pipeline de dados de mercado (worker `data`)

| Fonte | O que é | Formato | Frequência | O que extraímos | Observação |
| --- | --- | --- | --- | --- | --- |
| **CVM Dados Abertos** (`dados.cvm.gov.br`) | Portal oficial de dados abertos da CVM | ZIP/CSV por ano e tipo | Diária (checa arquivo novo; carga inicial completa) | **Cias abertas:** cadastro (CNPJ, código CVM, setor), DFP (anual) e ITR (trimestral): DRE, BP ativo/passivo, DFC — formato longo (conta, descrição, valor); FRE/FCA para capital social, free float, ações em circulação. **FIIs:** cadastro, informes mensais/trimestrais/anuais (patrimônio, cotas, cotistas, rendimentos, vacância quando informada) | Dado aberto, oficial. Base dos indicadores fundamentalistas. Cuidado com republicações: usar a versão mais recente por período |
| **B3 COTAHIST** | Histórico de cotações da B3 (série histórica oficial) | Arquivo posicional (layout fixo) anual/mensal/diário, ZIP | Diária, após o fechamento (arquivo do dia) | Abertura, máx, mín, fechamento, volume, negócios, por ticker e data; tipo de mercado; ISIN | Cobre todo o histórico. **Ajuste por proventos/eventos é feito por nós** (`adjust.py`) a partir de `corporate_actions`. Verificar termos de uso da B3 para redistribuição — §8.10 |
| **B3 — cadastro e eventos corporativos** | Dados de listagem: empresa, setor/subsetor/segmento, segmento de listagem; proventos, desdobramentos, bonificações | Endpoints públicos do site de listagem da B3 (JSON) | Diária | `securities` (cadastro), `corporate_actions` | **Não documentado oficialmente**; pode mudar sem aviso. Ter fallback: FRE/CVM para cadastro, provedor licenciado para proventos. Registrar em `data_sources` |
| **Tesouro Transparente** | Dados abertos do Tesouro Nacional | CSV diário (preços e taxas de compra/venda por título) | Diária | `treasury_bonds`, `treasury_daily` | Oficial e aberto |
| **BCB SGS** (`api.bcb.gov.br`) | Séries temporais do Banco Central | JSON | Diária | Selic meta e efetiva, CDI, IPCA, IGP-M, PTAX | Oficial e aberto. Séries por código (documentar os códigos em `bcb.py`) |
| **CoinGecko** (Demo em dev; **plano pago em produção** — ADR-017) | Dados de cripto | JSON | Horária (preços/market cap), diária (histórico) | `crypto_metrics`, histórico em USD e BRL | Demo: atribuição obrigatória e **sem uso comercial**; produção só com plano Analyst (ou outra fonte licenciada) |
| **B3 — carteiras teóricas de índices** | Composição dos índices (Ibovespa, IFIX, IDIV, SMLL, IBRX 100…) e valor de fechamento | CSV/JSON públicos do site da B3 (download da carteira teórica; valor do índice via COTAHIST/consulta) | Diária (carteira muda a cada quadrimestre, com prévias) | `indices`, `index_daily`, `index_compositions` | **Não documentado oficialmente**; mesma política de dados da B3 (§8.10). Fallback: manter a última carteira carregada e mostrar a data. Registrar em `data_sources` |
| **CVM — IPE** (`dados.cvm.gov.br/dados/CIA_ABERTA/DOC/IPE/`) | Documentos periódicos e eventuais entregues pelas companhias (fato relevante, comunicado ao mercado, aviso aos acionistas, calendário de eventos, assembleias) | CSV por ano (metadados + link do documento) | Diária, incremental por data de entrega | `company_documents` | Dado aberto. Só metadados e link; **o texto do documento não é baixado nem resumido** (sem IA sobre comunicados) |
| **CVM — Fundos** (`dados.cvm.gov.br/dados/FI/CAD/` e `FI/DOC/INF_DIARIO/`) | Cadastro de fundos e informe diário (cota, PL, captação, resgate, cotistas) | CSV mensal (cadastro) e mensal por dia (informe diário) | Diária, incremental | `funds`, `fund_daily` | Dado aberto. Volume grande (dezenas de milhares de fundos × dias): carga incremental, partição por ano. **v1.x** |
| **Agenda macro** (`content/agenda-macro.json`) | Datas do Copom, IPCA/IPCA-15, IGP-M, FOMC, vencimentos de opções/índices | JSON no repositório, mantido à mão por ano a partir dos calendários oficiais (BCB, IBGE, FGV, Fed, B3) | Anual (revisão manual) | `market_events` (kind `macro`) | Cada item com `source_url`. Sem estimativa de resultado — só a data |
| **Internacional** (stocks, REITs) | Cotações e cadastro de ativos dos EUA | Provedor licenciado — a definir no ADR-019 | — | `securities` com `market='us'` | **Fase 2.** Sem fonte oficial gratuita; entra só com contrato e receita |

Jobs (todos idempotentes, com lock, registrando `etl_runs`): `cotahist_daily` (19h30, dias úteis) · `b3_listing` (diário; inclui ETFs e BDRs) · `b3_corporate_actions` (diário) · `b3_index_composition` (diário; carteira teórica e fechamento dos índices) · `cvm_companies` (diário) · `cvm_statements` (diário; carga completa no bootstrap via `backfill-market.sh`) · `cvm_fii_reports` (diário) · `cvm_documents` (diário, incremental; IPE) · `cvm_funds` e `cvm_funds_daily` (diário; **v1.x**) · `tesouro_daily` (diário) · `bcb_series` (diário) · `coingecko_prices` (horário) · `coingecko_history` (diário) · `adjust_factors` (após eventos) · `indicators_rebuild` (após tudo, calcula `indicators_daily`) · `market_events_rebuild` (após proventos, documentos e agenda macro; materializa `market_events`) · `revalidate_pages` (chama o endpoint de revalidação do Next para as páginas afetadas, incluindo `/mercado`, `/agenda`, setores e índices).

Fórmulas dos indicadores ficam em `transform/indicators.py`, documentadas em `/indicadores`, com testes contra casos calculados à mão. Qualquer indicador cuja entrada esteja faltando fica `null` e a página mostra "—" com o motivo no tooltip ("empresa não publicou DFP 2025"), nunca zero.

---

## 4. Modelo de dados

Convenções: `id uuid` (v7 se disponível), `created_at`/`updated_at timestamptz`, soft delete só onde a lei exige reter; fora isso, delete é delete.

### 4.1 Schema `app` — identidade e consentimento (dono: `web`)

| Tabela | Campos principais | Notas |
| --- | --- | --- |
| `users` | `id, email (citext unique), name?, email_verified_at, locale='pt-BR', plan='free', delete_requested_at?, deleted_at?` | Nome é opcional — minimização. `delete_requested_at` abre a carência de 7 dias antes da exclusão definitiva |
| `sessions` · `accounts` · `verification_tokens` | Da biblioteca de auth | Tokens de magic link: uso único, expiram em 15 min, hash no banco |
| `consents` | `id, user_id?, subscriber_email_hash?, kind ('terms','privacy','newsletter'), document_version, accepted_at, ip, user_agent, source ('landing','app_signup','app_settings'), withdrawn_at?` | **Prova de consentimento** (LGPD art. 8 §2: o ônus da prova é do controlador). Versão do documento aceito é obrigatória |
| `data_requests` | `id, user_id?, email, kind ('access','export','delete','correct','portability'), status, requested_at, fulfilled_at, notes` | Registro de atendimento aos direitos do titular (art. 18). Prazo interno: 15 dias |

A lista de e-mail (`subscribers`, status, tokens de confirmação e de descadastro) vive no **Listmonk**, que é a fonte da verdade. O `web` só chama a API do Listmonk na inscrição e grava o `consents`.

### 4.2 Schema `app` — carteira, movimentações e análise (dono: `web`)

| Tabela | Campos principais | Notas |
| --- | --- | --- |
| `portfolios` | `id, user_id, name, base_currency='BRL', created_at` | Uma por usuário no v1 (o modelo suporta N) |
| `transactions` | `id, portfolio_id, asset_id, date, side ('buy','sell'), quantity numeric(28,10), price numeric(18,6), fees numeric(18,2), source ('manual','csv','b3_import','b3_api'), import_batch_id?, external_key?, note?` | Fonte da verdade da posição. `external_key` = hash (ativo, data, tipo, qtd, preço) para dedupe de importação. Cifrada na aplicação (§7.4) |
| `income_events` | `id, portfolio_id, asset_id, date, kind ('dividend','jcp','fii_income','interest','other'), gross numeric(18,2), net numeric(18,2), source, import_batch_id?, external_key?` | Proventos **recebidos** pelo usuário (diferente de `market.corporate_actions`, que é o provento anunciado pelo emissor) |
| `position_adjustments` | `id, portfolio_id, asset_id, quantity? \| value_brl?, avg_price?, note?, updated_at` | O "adicionar à mão" de hoje: posição informada sem histórico. Constraint: `quantity` **ou** `value_brl` |
| `positions` (view materializada) | `portfolio_id, asset_id, quantity, avg_price, cost_brl` | = Σ `transactions` (preço médio pelo método da Receita: compras ponderadas, venda não altera o PM) + `position_adjustments`. Recalculada por trigger/serviço a cada mudança |
| `import_batches` | `id, user_id, portfolio_id, source ('csv','b3_posicao','b3_negociacao','b3_proventos'), file_sha256, rows_in, rows_imported, rows_skipped, warnings jsonb, status, created_at` | **Sem o arquivo.** Só o hash (dedupe de reenvio) e a contagem |
| `b3_connections` | `id, user_id, provider='b3', external_consent_id, scope ('read_positions','read_transactions','read_income'), token_ciphertext, key_version, expires_at, last_sync_at, revoked_at` | **Fase 1** (integração oficial). Token cifrado como as posições; revogação em 1 clique gera `audit_log` |
| `assets` | `id, symbol, name, asset_class ('crypto','stablecoin','stock_br','bdr','etf_br','fii','fixed_income','treasury','other'), market_ref ('ticker'\|'coingecko_id'\|'treasury_slug'), currency, factor_map jsonb, active` | Catálogo do app; aponta para o schema `market` por `market_ref`. `factor_map` é o mapeamento ativo→fatores hoje hardcoded em `raio-x-carteira.py`; para ações vem do setor B3 por padrão |
| `analyses` | `id, user_id, portfolio_id, reference_date, input_snapshot jsonb, readings jsonb, narrative jsonb, warnings jsonb, engine_version, prompt_version, llm_model, llm_tokens_in, llm_tokens_out, cost_usd, narrative_filtered bool, duration_ms, created_at` | `input_snapshot` congela a carteira (posições, preço médio, proventos 12m) no momento da análise. Retenção: enquanto a conta existir |
| `analysis_feedback` | `id, analysis_id, rating (1–5), comment?, created_at` | v2. Único feedback loop de qualidade da narrativa |
| `watchlist_items` | `id, user_id, asset_id, created_at` — unique (user_id, asset_id) | Favoritos com login (v1.x). Sem login, a lista fica em `localStorage` e nunca chega ao servidor |
| `alerts` | `id, user_id, asset_id, kind ('price_above','price_below','income_announced','document'), threshold numeric?, channel ('email'), active bool, last_fired_at?, created_at` | v1.x. Avaliados por um job do `web` (o `data` não conhece usuários) que lê `/v1/quotes` e `/v1/market/events`; limite por usuário; cada e-mail traz link de desativação do alerta |
| `tax_periods` | `id, user_id, portfolio_id, month, asset_class, gross_sales, result, loss_carry_in, loss_carry_out, tax_due, tax_rules_version, darf_generated_at?, created_at` | **Fase 1.** Resultado da apuração de IR (`POST /v1/portfolios/tax`), gravado para o relatório anual. Colunas financeiras cifradas como as demais (§7.4) |

### 4.3 Schema `market` — dados de mercado (dono: `api` + `data`)

| Tabela | Campos principais | Notas |
| --- | --- | --- |
| `securities` | `ticker (pk), isin, cnpj, cvm_code, type ('stock','unit','bdr','etf','fii','fiagro'), market ('br' \| 'us' na Fase 2), company_name, trade_name, sector, subsector, segment, sector_slug, listing_segment, status, ri_url, etf_index_slug?, bdr_ratio?, updated_at` | Cadastro de todas as classes listadas (ações, units, ETFs, BDRs, FIIs, fiagros). Origem: B3 listagem + CVM. `sector_slug` alimenta `/setores` |
| `daily_quotes` | `ticker, date, open, high, low, close, volume, trades, adj_factor` — pk (ticker, date), **particionada por ano** | Origem: COTAHIST. `adj_factor` acumulado calculado por `adjust_factors` |
| `corporate_actions` | `id, ticker, kind ('dividend','jcp','fii_income','split','reverse_split','bonus','subscription'), ex_date, record_date, payment_date, value_per_share, ratio, source` | Proventos e eventos **anunciados** |
| `financial_statements` | `cvm_code, period_end, period_type ('annual','quarterly'), statement ('dre','bp_ativo','bp_passivo','dfc'), consolidated bool, account_code, account_name, value, version` — pk composta | Formato longo, igual ao da CVM. `version` para republicação |
| `company_facts` | `cvm_code, reference_date, shares_outstanding, free_float, capital_social` | Origem: FRE/FCA |
| `indicators_daily` | `ticker, date, pe, pb, ev_ebitda, ev_ebit, psr, dy_12m, payout, roe, roic, roa, gross_margin, ebitda_margin, net_margin, net_debt_ebitda, net_debt_equity, current_ratio, revenue_cagr_5y, earnings_cagr_5y, eps, bvps, market_cap, inputs jsonb` | Calculada por `indicators_rebuild`. `inputs` guarda os valores usados (auditoria: "de onde veio esse P/L") |
| `fii_reports` | `ticker, period (month), nav, nav_per_share, shareholders, income_per_share, vacancy_physical?, vacancy_financial?, admin_fee?, manager, administrator, document_url` | Origem: informes CVM |
| `treasury_bonds` | `slug (pk), name, index_type ('selic','ipca','prefixado','renda+','educa+'), maturity, coupon bool` | |
| `treasury_daily` | `slug, date, buy_rate, sell_rate, buy_price, sell_price` | Origem: Tesouro Transparente |
| `macro_series` | `series ('selic','cdi','ipca','igpm','ptax'), date, value` | Origem: BCB SGS |
| `crypto_assets` · `crypto_daily` · `crypto_metrics` | id CoinGecko, símbolo, nome; preço USD/BRL, market cap, volume por dia; snapshot horário (preço, 24h, 7d, dominância, ATH) | |
| `indices` | `slug (pk), b3_code, name, description, rebalance_note` | Ibovespa, IFIX, IDIV, SMLL, IBRX 100… |
| `index_daily` | `slug, date, value, change_pct` — pk (slug, date) | Fechamento diário do índice |
| `index_compositions` | `slug, date, ticker, weight, theoretical_qty` — pk (slug, date, ticker) | Carteira teórica vigente por data de carga; a página mostra a data |
| `company_documents` | `id, cvm_code, ticker?, category, type, subject, delivered_at, reference_date?, url, protocol` — unique (protocol) | Origem: CVM IPE. Só metadados e link |
| `funds` | `cnpj (pk), name, short_name, cvm_class, anbima_class?, manager, administrator, admin_fee, perf_fee, target_audience, status, started_at` | Origem: CVM cadastro. **v1.x** |
| `fund_daily` | `cnpj, date, nav_per_share, total_nav, inflow, outflow, shareholders` — pk (cnpj, date), particionada por ano | Origem: CVM informe diário. **v1.x** |
| `market_events` (view materializada) | `id, kind ('ex_date','payment','document','macro','corporate'), date, ticker?, cvm_code?, payload jsonb, source` | Une `corporate_actions`, `company_documents` e `content/agenda-macro.json`; base de `/agenda`, da tab Eventos e do calendário da carteira. Rebuild pelo job `market_events_rebuild` |
| `etl_runs` | `id, job, period, started_at, finished_at, status, rows, error?` | Base do alerta de frescor |
| `data_sources` | `source, url, license_note, terms_checked_at, last_loaded_at` | Registro das fontes e dos termos de uso (§8.10) |

### 4.4 Segurança e auditoria (schema `app`)

| Tabela | Campos principais | Notas |
| --- | --- | --- |
| `audit_log` | `id, actor_user_id?, action ('login','logout','portfolio.update','transaction.create','import.commit','analysis.run','account.export','account.delete_request','consent.withdraw','b3.connect','b3.revoke', ...), target, ip, user_agent, metadata jsonb, created_at` | Append-only (o usuário de banco do app não tem UPDATE/DELETE nela). Base para resposta a incidente e para o relatório de acesso do titular |
| `access_log` | `id, ip, user_id?, route, status, created_at` | Registro de acesso a aplicação (Marco Civil art. 15). Pode ser o log do nginx exportado — desde que guardado 6 meses com integridade. Sem corpo de requisição |
| rate limits | Redis, não tabela | Chaves `rl:{scope}:{ip|user}` com TTL |

### 4.5 Retenção (tabela para a Política de Privacidade)

| Dado | Base legal (LGPD art. 7) | Retenção | Depois |
| --- | --- | --- | --- |
| E-mail da lista + prova de consentimento | Consentimento (I) | Até descadastro | E-mail vai para lista de supressão (hash) para não reenviar; prova de consentimento mantida 5 anos (exercício regular de direitos, art. 7 VI) |
| Conta, carteira, movimentações, proventos recebidos, análises | Execução de contrato (V) | Enquanto a conta existir | Exclusão em 7 dias após o pedido (carência para arrependimento), exceto o que abaixo exige reter |
| Arquivos importados (CSV, Área do Investidor) | — | **Não são armazenados** (parse em memória e descarte) | Só o hash e as contagens em `import_batches`, por 12 meses |
| Tokens da conexão B3 oficial (Fase 1) | Execução de contrato (V) + consentimento na B3 | Até revogação ou expiração | Apagados na revogação; registro da revogação no `audit_log` |
| Registros de acesso (IP, data/hora) | Obrigação legal (II) — Marco Civil art. 15 | **6 meses** | Apagados automaticamente |
| Logs de auditoria de segurança | Legítimo interesse (IX) — segurança | 12 meses | Apagados; entradas ligadas a incidente podem ser retidas até o encerramento |
| Dados fiscais / faturas (Fase 2) | Obrigação legal (II) | 5 anos | Apagados |
| Backups | Mesmas bases dos dados originais | 30 dias rotativos | Sobrescritos; uma exclusão de conta "expira" do backup em até 30 dias — dizer isso na política |
| Favoritos e alertas (v1.x) | Execução de contrato (V) | Enquanto a conta existir | Apagados com a conta; favoritos sem login nunca saem do navegador |
| Apuração de IR (Fase 1) | Execução de contrato (V) | Enquanto a conta existir (o titular pode precisar por 5 anos — ele exporta) | Apagados com a conta |
| Dados de mercado (schema `market`) | Não são dados pessoais | Indefinida | — |

---

## 5. Design system (do brand kit)

| Token | Valor | Uso |
| --- | --- | --- |
| `--navy` | `#0B192C` | Fundo padrão de todo o site e app |
| `--navy-2` | `#11213A` | Superfícies elevadas (cards, inputs) |
| `--navy-3` | `#1A2E4C` | Bordas, divisores, hover |
| `--gold` | `#C5A059` | Acento: **uma** palavra em destaque por seção, botão primário, ícone do logo, números-chave |
| `--gold-2` | `#D4AF37` | Hover do dourado, brilho |
| `--ice` | `#F8F9FA` | Texto principal |
| `--ice-70` | `rgba(248,249,250,.7)` | Texto secundário, fontes e datas |
| `--ok` / `--warn` / `--risk` | `#4CAF7D` / `#E0A64C` / `#D9534F` | Nos cards de leitura (semântica de risco) e em variação positiva/negativa de preço, sempre com sinal/ícone + texto. Nunca como decoração. **Texto pequeno em `--risk` usa `--risk-text` `#E56E6A`** (o `#D9534F` dá 4,07 de contraste sobre `--navy-2`, abaixo do AA); fundos e bordas seguem com `--risk` |
| Tipografia | Playfair Display 600/700 para H1–H2 e números de destaque; Inter 400/500/600 para todo o resto; **números tabulares** (`font-variant-numeric: tabular-nums`) em tabelas e indicadores | Tamanhos: H1 40/48, H2 28/36, corpo 16/26, tabelas 14/22 |
| Grid | Container 1120 px (1280 nas páginas de ativo e screener), gutter 16 px no mobile, 24 px desktop | Mobile-first: metade do tráfego do YouTube é celular; tabelas largas rolam horizontalmente dentro do card, nunca a página |
| Componentes base | `Button`, `Input`, `Checkbox`, `Card`, `Badge`, `Table`, `Tooltip` (definição de termo), `Disclaimer`, `EmailCapture`, `VideoEmbed` (nocookie, lazy) | Documentar em `/design` (rota só em dev) |
| Componentes de análise | `ReadingCard` (uma das cinco leituras), `CorrelationMatrix`, `DrawdownChart` | |
| Componentes de mercado | `PriceHeader` (cotação, variação, 52 s, fonte/data), `HistoryChart` (linha/candles, períodos, ajustado on/off), `IndicatorGrid` (grupos: valuation / rentabilidade / endividamento / crescimento; cada célula com tooltip de definição + `SourceBadge`), `FinancialTable` (anual/trimestral, toggle, valores em milhões), `DividendTable` + `DividendChart`, `EventList`, `Screener` (filtros, tabela ordenável, paginação, URL com estado), `CompareTable`, `TreasuryTable`, `CryptoTable`, `SourceBadge` ("Fonte: CVM · DFP 2025 · atualizado em 18/09/2026"), `AssetCTA` ("Tem PETR4 na carteira?"), `MarketStrip` (faixa do header), `GlobalSearch` (busca global, lazy), `MoversList` (altas/baixas/volume com a métrica no título), `EventCalendar` (agenda por dia/semana), `DocumentList` (comunicados CVM), `IndexCompositionTable`, `SectorTree`, `WatchStar` (favorito; `localStorage` sem login) | **Regra: nenhum número de mercado sem `SourceBadge`.** Valores ausentes mostram "—" com o motivo no tooltip. Listas ordenadas sempre com a métrica no título |
| Modo claro | Não no v1. A marca é escura | `color-scheme: dark` declarado |
| Regra da palavra dourada | Igual à thumbnail: em cada título, no máximo uma palavra em `--gold` | Ex.: "Você sabe o que **tem**?" |

**Estrutura da landing (`/`)**, de cima para baixo:

1. **Hero** — H1 "Você sabe o que **tem**?" · sub: "O Alpherion lê a sua carteira — cripto, ações, FIIs, renda fixa — e devolve cinco leituras de risco, em segundos, em português. Não diz o que comprar." · `EmailCapture` (e-mail + checkbox de consentimento + botão "Entrar na lista") · microcopy: "Grátis. Quem está na lista entra primeiro. Sem spam — no máximo um e-mail por semana."
2. **As cinco leituras** — 5 cards: Concentração, Correlação, Exposição, Drawdown, Liquidez. Cada um com a pergunta ("Você está concentrado?"), a definição em uma frase e o número da carteira do vídeo 02 como exemplo (38% · 0,91 · 0,96 · −34% · 0,03% do volume).
3. **Prévia** — imagem estática de um `ReadingCard` real com a carteira ilustrativa do vídeo 02, rotulada "carteira ilustrativa".
4. **O que o Alpherion não faz** — duas colunas FAZ / NÃO FAZ, o mesmo card do vídeo. "Não é recomendação. Não considera seu perfil. Não indica compra ou venda."
5. **Dados de mercado** — "Cotações, indicadores e proventos de toda a B3, Tesouro e cripto — com fonte em cada número." Busca de ticker + 4 links (`/acoes`, `/fiis`, `/tesouro`, `/cripto`).
6. **Últimos vídeos** — 3 cards (um por quadro), thumbnails locais, link para o YouTube.
7. **Quem faz** — 3 linhas sobre o Bryan + link `/sobre`. Transparência regulatória em uma frase.
8. **FAQ** — 7 perguntas: é grátis? · precisa conectar corretora? (não; importa da Área do Investidor da B3, à mão ou CSV) · vocês guardam minha carteira? (sim, cifrada, você apaga quando quiser) · vocês guardam meu arquivo da B3? (não) · é recomendação? (não) · quando abre? ("quem está na lista sabe primeiro") · de onde vêm os dados? (CVM, B3, Tesouro, BCB, CoinGecko — link para `/indicadores`).
9. **Segundo `EmailCapture`.**
10. **Rodapé** — logo · links legais · razão social + CNPJ + cidade/UF · e-mail de contato e de privacidade · disclaimer CVM de 2 linhas · atribuição das fontes de dados · "© 2026 Alpherion Finance".

**Estrutura da página de ativo (`/acoes/[ticker]`)**, de cima para baixo: `PriceHeader` → `HistoryChart` → `IndicatorGrid` → `AssetCTA` → Proventos (`DividendTable` + `DividendChart`) → Demonstrações (`FinancialTable`) → Eventos → Cadastro → `Disclaimer` + "Encontrou um erro? `/contato`" → ativos do mesmo setor (links internos). Tudo abaixo do `IndicatorGrid` carrega sob demanda.

---

## 6. Análise por IA — desenho e guardrails

### 6.1 Pipeline

```
posições + movimentações (app) ─► POST /v1/analyses ─► normaliza/valida ─► histórico do schema market (cache) ─► engine (pandas) ─► readings (JSON)
                                                                                                                          │
                                                                                                              pseudonimiza + resume
                                                                                                                          ▼
                                                                                                       prompt versionado ─► Claude API ─► JSON
                                                                                                                          │
                                                                                                         guard.py ─► narrativa OK / regenera / fallback
                                                                                                                          ▼
                                                                                              resposta = readings + narrativa + disclaimer + warnings + meta
```

O engine lê histórico de `market.daily_quotes` (ajustado), `macro_series` e `crypto_daily` — a mesma base das páginas públicas. O número que a página mostra e o número que a leitura usa vêm da mesma tabela.

### 6.2 O que vai para o LLM (e o que não vai)

| Vai | Não vai, nunca |
| --- | --- |
| `readings` (números agregados), símbolos, classes, pesos, data de referência, janela, faixa do total ("R$ 100–150 mil"), resultado percentual por posição (de `cost`) | E-mail, nome, `user_id`, IP, ID de carteira, quantidades absolutas, preços médios em R$, datas das compras, notas livres do usuário, indicadores fundamentalistas dos ativos |

A chamada usa um identificador **opaco** (hash) só para o rate limit do provedor. A API do Alpherion registra `prompt_version`, tokens e custo em `analyses`.

### 6.3 Regras de conteúdo da narrativa (system prompt — resumo)

- Papel: "analista de risco que descreve; não aconselha". Voz do canal: profissional, direta, termo definido na primeira vez.
- Proibido: verbos de ordem sobre ativo específico (comprar, vender, aumentar, reduzir, trocar, realizar lucro, fazer caixa, "considere adicionar"), previsões de preço, adjetivos de valor sobre ação/FII ("barata", "cara", "oportunidade", "descontada"), promessas de retorno. **Indicadores fundamentalistas não entram na narrativa** — nem como fato ("P/L de 5") nem como juízo; a narrativa é sobre a carteira, não sobre a empresa.
- Permitido: descrever concentração, co-movimento, exposição, histórico de queda, liquidez, resultado acumulado como fato ("PETR4 está 17% acima do seu preço médio"); terminar com **perguntas** para o usuário levar à própria carteira ("Você decidiu ter 50% em cripto ou isso aconteceu?").
- Cripto: pode comentar o comportamento do ativo; ainda assim sem ordem de operação.
- Sempre citar as limitações (dado passado, contexto desconhecido, cotação pode estar defasada).
- Saída em JSON conforme `schemas.py`; qualquer campo extra é descartado.

### 6.4 `guard.py` — filtro pós-geração

1. Lista de padrões de recomendação (pt-BR, com flexões): se casar, regenerar uma vez com instrução reforçada; se casar de novo, devolver narrativa **genérica pré-escrita** por leitura e marcar `narrative_filtered = true`. Nunca falhar a análise por causa da narrativa — os números sempre saem.
2. Validação do schema (pydantic). Falhou → mesmo fallback.
3. Todo texto exibido ao usuário vem acompanhado do `disclaimer` do backend (o front não pode omitir; teste de UI cobre isso).
4. Amostragem semanal: 10 narrativas revisadas à mão pelo Bryan; achados viram casos em `tests/test_guard.py`.

### 6.5 Limites e custo

- Free: N análises/dia por usuário (começar em 3), 1 carteira, até 100 posições (importação da B3 traz mais linhas que a manual). Configurável por env.
- Timeout total 30 s; LLM 15 s. Falha do LLM não derruba a análise (fallback de narrativa).
- Orçamento: contador de custo diário no Redis com alerta no Telegram ao passar o teto.

---

## 7. Segurança

### 7.1 Princípios

Privacy by design (LGPD art. 46 §2): coletar o mínimo, cifrar o que é sensível, segregar quem vê o quê, registrar quem fez o quê, apagar quando não precisar. Referência de checklist: OWASP ASVS nível 2 para o app; OWASP Top 10 revisado a cada release maior.

### 7.2 Borda (Cloudflare + nginx)

- DNS na Cloudflare, registro em **Registro.br** (obrigatório para `.com.br`) com **DNSSEC** ativado.
- Proxy laranja em todos os hosts públicos. TLS **Full (strict)** com certificado de origem da Cloudflare (ou Let's Encrypt via DNS-01) no nginx. **Authenticated Origin Pulls** ligado. HSTS com `preload` (após 1 semana estável).
- WAF managed rules + rate limiting na borda: `/api/subscribe` e `/api/auth/*` (10/min por IP), `/api/analyses` e `/api/imports/*` (por sessão), `/v1/securities` (por IP), Bot Fight Mode. **Cache de borda** nas páginas de ativo (`Cache-Control: public, s-maxage=3600, stale-while-revalidate=86400`) — são estáticas por natureza e é o que segura um pico de tráfego orgânico.
- Firewall na VPS (`ufw`): 80/443 **só** para as faixas de IP da Cloudflare (`update-cloudflare-ips.sh` no cron); SSH só por chave; `fail2ban` nos logs do sshd e do nginx.
- nginx: `real_ip` a partir de `CF-Connecting-IP` (para rate limit e logs corretos), `client_max_body_size 5m` (arquivos da B3), `limit_req` de segurança, `server_tokens off`.
- **Cloudflare é operador de dados** (vê IPs e tráfego). Consta na Política de Privacidade como suboperador com transferência internacional (§8.4).

### 7.3 Headers HTTP

> **Revisado em 21/09/2026 (Etapa 2.4).** O Next envia todos os headers abaixo **exceto HSTS** (`next.config.ts` → `headers()`); o nginx acrescenta só o HSTS (depende do TLS) e **não repete** os demais — CSP duplicada é aplicada em interseção. **CSP sem nonce no site público:** nonce por request obriga renderização dinâmica de toda página no Next, o que inviabiliza o SSG da landing e o ISR com cache de borda das páginas de ativo (§9) — um nonce cacheado deixa de ser nonce. `'unsafe-inline'` cobre os scripts inline do próprio Next (é o que a documentação do framework recomenda para páginas estáticas). O app autenticado (rotas dinâmicas por natureza) ganha CSP com nonce via `proxy.ts` na Etapa 5.

```
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
Content-Security-Policy (site público): default-src 'self'; script-src 'self' 'unsafe-inline' https://stats.alpherion.com.br; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://i.ytimg.com; font-src 'self'; connect-src 'self' https://stats.alpherion.com.br; frame-src https://www.youtube-nocookie.com; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; upgrade-insecure-requests
Content-Security-Policy (app, Etapa 5): igual, com script-src 'self' 'nonce-{nonce}' 'strict-dynamic' https://stats.alpherion.com.br
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()
Cross-Origin-Opener-Policy: same-origin
X-Frame-Options: DENY
```

Meta: nota A+ no securityheaders.com e no SSL Labs antes do dia 8.

### 7.4 Aplicação (web)

- **Auth:** magic link de uso único (15 min, hash no banco), Google OAuth com `state` + PKCE. Sessão em cookie `HttpOnly Secure SameSite=Lax`, ID aleatório de 256 bits, rotação no login, revogação em `/conta`. Logout invalida no servidor.
- **CSRF:** cookies `SameSite=Lax` + verificação de `Origin` nos route handlers mutáveis (o Next faz isso nas server actions; conferir para route handlers).
- **Validação:** zod em todo input; limites explícitos (posições ≤ 100, símbolo ≤ 20 chars, CSV ≤ 2 MB / 1.000 linhas, arquivos B3 ≤ 5 MB cada / 3 por envio). Erros de validação não vazam stack.
- **Importação (CSV e B3):** parse no servidor (API), em memória, nunca `eval`; **xlsx via openpyxl em modo `read_only`, sem macros, com limite de linhas/células e checagem de tamanho descomprimido** (zip bomb); aceitar só `text/csv` e `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` e checar o conteúdo, não a extensão. **Os arquivos da Área do Investidor contêm CPF e nome do titular: o parser lê apenas as colunas de ativo/data/tipo/quantidade/preço e descarta o resto antes de qualquer log ou retorno.** Nenhum arquivo é persistido; só o `sha256` para dedupe. Ao **exportar** CSV, prefixar células que começam com `= + - @` com `'` (CSV injection).
- **Autorização:** todo acesso a `portfolios`/`transactions`/`analyses`/`import_batches` filtra por `user_id` da sessão (nunca por ID vindo do cliente sem esse filtro). Teste automatizado: usuário A não lê análise nem importação de B (IDOR).
- **Rate limit** por IP e por usuário (Redis): subscribe, login, análise, importação, export.
- **Segredos:** `.env` só na VPS (permissão 600), nunca no repo; `.env.example` sem valores. Tokens de serviço da API com 256 bits, um por cliente, rotacionáveis (runbook). Chave da Claude API e da CoinGecko só na API/worker.
- **Dependências:** Renovate/Dependabot semanal, `pnpm audit` e `pip-audit` no CI, lockfiles commitados, imagens Docker `node:22-slim` / `python:3.12-slim` com usuário não-root e `read_only` onde der.
- **Cifra em repouso:** disco da VPS com LUKS se o provedor permitir; independentemente disso, `transactions`, `income_events`, `position_adjustments`, `analyses.input_snapshot` e `b3_connections.token_ciphertext` cifrados na aplicação (AES-256-GCM, chave em env, `key_version` na linha) — dado financeiro pessoal merece defesa em profundidade contra dump de banco. A view `positions` é recalculada em memória no serviço, não no banco, para não exigir campos em claro. Backups cifrados com `age` antes de sair da máquina.
- **Logs sem PII:** e-mail, posições, movimentações e conteúdo de arquivos nunca em log; `user_id` só como hash curto. Nada de `console.log` de request body.
- **Erros:** páginas 4xx/5xx próprias; mensagens genéricas ao usuário, detalhe só no GlitchTip.

### 7.5 API do Alpherion e worker `data`

- API acessível pela rede Docker **e** por `api.alpherion.com.br` atrás da Cloudflare com token de serviço (para o bot no futuro). CORS: só `https://app.alpherion.com.br`.
- Cada token tem escopo (`analyses:write`, `imports:write`, `market:read`, `quotes:read`) e rate limit próprio.
- Sem estado de usuário; sem PII; sem chamadas externas além dos provedores listados (lista fechada de hosts).
- Screener: filtros e campos de ordenação validados contra lista fechada (nunca interpolar nome de coluna vindo do cliente); paginação obrigatória (≤ 100 por página); índices em todos os campos filtráveis; `statement_timeout` de 5 s no usuário de banco da API.
- **Worker `data`:** usuário de banco próprio com acesso **só** ao schema `market` (nem leitura no `app`); egress restrito aos hosts das fontes; download em diretório temporário com limite de tamanho; arquivos ZIP das fontes verificados contra zip bomb; falha de um job não derruba os outros; alerta se um job crítico (`cotahist_daily`) não rodou até 21h.
- `/v1/health` não expõe versões.

### 7.6 VPS

- Ubuntu 24.04 LTS, `unattended-upgrades` para segurança, reboot programado de madrugada quando exigir kernel.
- Usuário de deploy sem sudo interativo; root por SSH desabilitado; `PasswordAuthentication no`.
- Docker: sem `--privileged`, redes separadas (`edge`, `internal`), volumes nomeados, `logging: json-file` com rotação.
- Postgres: usuário por serviço (`web` → schema `app`; `api` → `market` leitura + `app` nenhum; `data` → `market` escrita; `umami`, `listmonk` bancos próprios). `web` **sem** UPDATE/DELETE em `audit_log`; `pg_hba` só rede interna; `ssl=on` mesmo interno. Dimensionar disco: COTAHIST completo + DFP/ITR históricos ficam na casa de dezenas de GB — planejar volume separado para `market`.
- Redis com senha e `protected-mode`.
- **Backups:** `pg_dump` diário de cada banco → `age` (chave pública; a privada fica fora da VPS) → storage S3-compatível fora da VPS. Retenção 30 dias. O schema `market` é reconstruível das fontes (`backfill-market.sh`); fazer dump semanal dele, não diário, para não inflar o backup. **Teste de restore mensal** (`restore-test.sh` sobe um Postgres efêmero e confere contagens). Chave privada de backup guardada em dois lugares offline.
- **Localização:** se a VPS ou o storage de backup estiverem fora do Brasil, isso é **transferência internacional** (LGPD art. 33) e precisa constar na política com base legal (cláusulas contratuais padrão da ANPD — Res. CD/ANPD 19/2024 — ou o DPA do provedor). Preferir VPS e storage com região no Brasil (São Paulo). Se não der, documentar e seguir.
- Monitoramento: Uptime Kuma + alerta de disco (> 80%), de falha de backup, de erro 5xx (> 1%/5 min) e de **dado velho** (`etl_runs` sem sucesso no dia) no Telegram.

### 7.7 Plano de resposta a incidente (runbook em `docs/incidente.md`)

1. **Conter:** revogar tokens/sessões, rotacionar segredos, isolar container, bloquear na Cloudflare.
2. **Avaliar:** quais dados, quantos titulares, janela de tempo, causa. Preservar logs (`audit_log`, `access_log`, nginx).
3. **Comunicar à ANPD e aos titulares** quando houver risco ou dano relevante: prazo de **3 dias úteis** a partir do conhecimento (Res. CD/ANPD nº 15/2024), pelo formulário da ANPD; comunicado aos titulares em linguagem simples com o que aconteceu, o que foi feito e o que eles devem fazer.
4. **Registrar:** relatório interno mesmo quando não houver comunicação (a ANPD pode pedir).
5. **Corrigir e testar:** post-mortem sem culpa; cada item vira teste ou regra.

Contato de incidente e de privacidade: `privacidade@alpherion.com.br` (mesmo canal do encarregado).

---

## 8. Conformidade legal (Brasil)

### 8.1 LGPD (Lei 13.709/2018) — o que implementar, não só escrever

| Exigência | Como o site cumpre |
| --- | --- |
| Identificar controlador e encarregado (art. 41) | Rodapé e política: razão social, CNPJ, e-mail do encarregado. Como agente de pequeno porte (Res. CD/ANPD 2/2022) a nomeação formal é dispensável, mas o **canal de atendimento é obrigatório** — Bryan assume como encarregado |
| Base legal por finalidade (art. 7) | Tabela em §4.5. Newsletter = **consentimento** com double opt-in; app (inclusive importação de arquivos da B3) = execução de contrato; logs = obrigação legal / legítimo interesse |
| Consentimento livre, informado, inequívoco e **comprovável** (art. 8) | Checkbox não pré-marcado, texto específico ("quero receber a Leitura de Mercado e avisos do Alpherion por e-mail"), link para a política, registro em `consents` com versão, IP, data, user-agent. Revogável em 1 clique |
| Direitos do titular (art. 18) | Em `/conta`: **exportar** (JSON com tudo que temos, incluindo movimentações e proventos), **excluir conta**, corrigir dados, ver consentimentos e revogar, revogar conexão B3. Fora do app: e-mail ao encarregado, resposta em até 15 dias, registro em `data_requests` |
| Transparência (art. 9) | Política em linguagem simples, com tabela de dados × finalidade × base × retenção × com quem compartilhamos |
| Segurança (art. 46) | §7 inteiro |
| Registro das operações de tratamento (art. 37) | `docs/ropa.md` no repo — versão simplificada permitida ao pequeno porte. Atualizar a cada novo tratamento (importação B3, conexão oficial, pagamento) |
| Transferência internacional (art. 33) | §8.4 |
| Incidente (art. 48) | §7.7 |
| Menores (art. 14) | Termos: uso restrito a maiores de 18 anos. Sem verificação de idade no v1 além da declaração |
| Privacy by default | Nome opcional; CPF nunca coletado; arquivos nunca guardados; sem tracking de terceiros; analytics sem cookie; e-mail marketing só com opt-in; movimentações cifradas |

### 8.2 Marco Civil da Internet (Lei 12.965/2014)

- Art. 15: provedor de aplicação constituído como PJ com fim econômico deve guardar **registros de acesso à aplicação** (IP, data e hora) por **6 meses**, em sigilo e ambiente controlado. → `access_log` (ou log do nginx exportado com integridade) com purge automático em 6 meses.
- Art. 7: não usar os dados para fins além do informado; entregar ao usuário quando pedir (coincide com LGPD art. 18).

### 8.3 CVM — Resoluções 19 (consultores) e 20 (analistas)

- O site **não** publica análise de valor mobiliário com opinião de valor nem recomendação individualizada até o credenciamento. Isso vale para o LLM (§6), para `/leitura` (descrever, não opinar sobre ação/FII) e para as **páginas de ativos**: cotação, histórico, demonstrações e indicadores calculados por fórmula pública são **informação**, não análise — desde que não venham acompanhados de opinião de valor, nota, ranking editorial ou "preço-alvo". Um indicador é um número com fonte; a interpretação fica no glossário, em termos gerais ("P/L alto pode indicar…"), nunca sobre o ativo da página.
- **Aviso legal** (`/aviso-legal`, resumido no rodapé e integral em toda análise):

  > As informações deste site e do aplicativo têm caráter educacional e informativo. Não constituem recomendação, consultoria, análise ou oferta de investimento, não consideram objetivos, situação financeira ou necessidades de qualquer pessoa e não indicam compra ou venda de nenhum ativo. O diagnóstico de carteira é uma leitura de risco baseada em dados históricos, que não garantem resultados futuros. Cotações, indicadores e demonstrações são obtidos de fontes públicas (CVM, B3, Tesouro Nacional, Banco Central, CoinGecko) e podem conter erros ou atrasos; confira sempre na fonte. Alpherion Finance e seus responsáveis não são analistas de valores mobiliários (Res. CVM 20) nem consultores de valores mobiliários (Res. CVM 19) credenciados pela CVM. Criptoativos são ativos de alto risco. Decisões de investimento são de exclusiva responsabilidade do usuário.

- Quando vier o CNPI: campo em config para "Relatórios assinados por [nome], CNPI nº [x]" e uma segunda versão do aviso. Não antes.
- **Comunicados CVM** (`/acoes/[ticker]` → Comunicados, `/agenda`): o site lista título, categoria, data e link para o documento na CVM. Não resume, não destaca, não comenta — resumo de fato relevante é interpretação.
- **Imposto de renda** (`/carteira/ir`, Fase 1): cálculo aritmético a partir das regras publicadas pela Receita Federal, com a versão das regras gravada. Disclaimer próprio: "não é consultoria tributária; confira com um contador; a responsabilidade pela declaração é do contribuinte". Não é atividade privativa, mas o aviso evita expectativa de assessoria.
- Sem depoimentos de rentabilidade, sem "resultados de usuários" com retorno financeiro.
- Vídeo 15 (carteiras de inscritos): a página de envio, se existir, deixa claro que o resultado é agregado e anônimo e que **não haverá resposta individual**.

### 8.4 Transferência internacional de dados

Listar na política, por suboperador: **Cloudflare** (proxy/DNS — IP e tráfego), **provedor de e-mail** (endereço de e-mail; escolher região SP quando possível), **Anthropic** (Claude API — recebe só dados pseudonimizados de carteira, sem identificação; ainda assim listar), **storage de backup** (dados cifrados), **Google** (só se o usuário escolher login com Google), **CoinGecko** (recebe só requisições do servidor, sem dado de usuário — não é transferência, mas listar como fonte), e o **provedor da VPS** se estiver fora do Brasil. Base: cláusulas-padrão contratuais (Res. CD/ANPD 19/2024) ou o DPA do provedor + minimização. Manter os DPAs aceitos em `docs/dpa/`.

### 8.5 Cookies

- Site público: **nenhum cookie** (Umami é cookieless; fontes locais; YouTube só em `youtube-nocookie.com` e carregado ao clicar). Preferências do screener ficam na URL, não em cookie.
- App: só o cookie de sessão (estritamente necessário). Pelo Guia de Cookies da ANPD, cookies necessários não exigem consentimento → **sem banner**. A política tem uma seção "Cookies" listando o de sessão.
- Se um dia entrar pixel de anúncio, aí sim entra banner com opt-in real — e esse é um motivo forte para não entrar.

### 8.6 Consumidor (CDC + Decreto 7.962/2013) — ativa na Fase 2, preparada agora

- Rodapé desde o dia 1: razão social, CNPJ, endereço físico (pode ser o da ME), e-mail de atendimento.
- Ao vender assinatura: preço total com impostos, condições, período, renovação automática explicada **antes** do clique, resumo do contrato antes da confirmação, confirmação por e-mail, **direito de arrependimento em 7 dias** com reembolso integral (CDC art. 49), cancelamento **self-service** tão fácil quanto assinar, atendimento em até 5 dias.
- Pagamento por gateway que suporte **Pix**, cartão e boleto (Stripe BR, Asaas, Pagar.me ou Mercado Pago). **Nunca** tocar dado de cartão (checkout hospedado/tokenizado → escopo PCI mínimo, SAQ-A). NFS-e automática pela ME a cada cobrança (gateway com integração ou ENotas/NFE.io).

### 8.7 Acessibilidade (LBI — Lei 13.146/2015, art. 63)

Sites de empresa devem ser acessíveis. Alvo **WCAG 2.1 AA**: contraste (dourado sobre navy passa em texto grande; para texto pequeno usar `--ice`), navegação por teclado, foco visível, `aria-label` em ícones, tabelas com cabeçalho e `caption`, alternativa textual para gráficos (tabela de dados escondível por trás de "ver como tabela"; a narrativa já é a alternativa da matriz de correlação), sem informação transmitida só por cor (sinal + ícone em variações de preço e nos cards de risco), screener operável por teclado. Lighthouse Accessibility ≥ 95 no CI.

### 8.8 E-mail

- Autenticação do domínio: **SPF, DKIM, DMARC** (`p=quarantine` → `p=reject`) para `alpherion.com.br` e para o subdomínio de envio `news.alpherion.com.br`. MTA-STS e TLS-RPT opcionais. Isso é entregabilidade **e** anti-phishing em nome da marca.
- Lista: double opt-in, `List-Unsubscribe` + `List-Unsubscribe-Post` (one-click) em todo envio, remetente identificado, endereço físico no rodapé (CAPEM / boas práticas). Frequência prometida na landing: até 1 por semana.
- Transacional e marketing em **remetentes diferentes** (`no-reply@` vs `leitura@news.`) para a reputação de um não afetar o outro.

### 8.9 Cripto (Lei 14.478/2022)

O site não custodia, não intermedeia, não converte criptoativos. Registrar isso na análise de escopo (`docs/ropa.md`) para deixar claro que não é prestador de serviço de ativos virtuais. Se a Fase 1 ler exchanges por API, usar chaves **somente leitura** e dizer isso em tela (nunca pedir chave com permissão de saque ou trade).

### 8.10 Dados públicos de mercado — fontes, termos e apresentação

- **Atribuição em todo número** (`SourceBadge`): fonte, documento/período e data de atualização. Rodapé das páginas de ativo e de `/mercado` com a lista de fontes e "dados podem conter erros ou atrasos; confira na fonte".
- **Termos de uso, a verificar e registrar em `docs/fontes-de-dados.md` antes do lançamento:**
  - **CVM Dados Abertos:** dados abertos do governo (Lei 12.527/2011 + política de dados abertos); uso e redistribuição livres com atribuição.
  - **Tesouro Transparente** e **BCB SGS:** dados abertos; uso livre com atribuição.
  - **B3 (COTAHIST, listagem, eventos, carteiras teóricas de índices):** **verificado em 21/09/2026 ([fontes-de-dados.md](fontes-de-dados.md), ADR-017):** os termos do site vedam uso comercial sem autorização escrita e a Política de Consumo de Market Data 2026 exige licença (Distribuição em Atraso Snapshot, R$ 320/mês por dataset) para exibir em site aberto e contrato de Produtizador para armazenar histórico e usar em análise. **Nenhum preço da B3 em produção sem a licença registrada**; flag `MARKET_B3_PRICES_ENABLED`. Provedor licenciado (brapi etc.) resolve só o canal de acesso, não a licença de exibição. Dados derivados das demonstrações (CVM) não dependem disso.
  - **CoinGecko:** **verificado em 21/09/2026:** o plano Demo (100 req/min, 10.000/mês, atribuição obrigatória) **não permite uso comercial** — serve só para dev. Produção exige plano pago (Analyst) ou outra fonte com termos de exibição; flag `MARKET_CRYPTO_ENABLED`.
  - **CVM IPE e CVM Fundos:** dados abertos (mesma política do item CVM); os documentos do IPE são linkados no site da CVM, não copiados.
  - **Provedor internacional (Fase 2):** contrato comercial com direito de exibição (display) no site e no app; registrar em `data_sources` e no ADR-019 antes de qualquer página.
  - Nada de raspar Status Invest, Fundamentus, Investidor10 ou similares — nem para "conferir".
- **Sem opinião de valor:** nenhuma página de ativo tem nota, score, selo, ranking editorial, "compra/venda", "preço justo" (Graham, Bazin ou qualquer fórmula de valor intrínseco), preço-alvo ou "melhores". O screener ordena pelo que o usuário escolher; padrão neutro. Listas como "maiores altas do dia" ou presets de screener são fato ordenado por um número, com a métrica no título. Registrado no ADR-018.
- **Correção de dados:** canal em `/contato` ("encontrei um erro no dado de X"); erro confirmado é corrigido na fonte do pipeline (nunca à mão no banco) e registrado em `etl_runs`.
- **Propriedade intelectual das fórmulas:** os indicadores são calculados por fórmulas públicas documentadas em `/indicadores`; o dado bruto continua sendo da fonte e é atribuído.

### 8.11 Conexão com a conta B3

- **Importação de arquivos (v1):** o próprio titular exporta os arquivos da Área do Investidor (B3) e envia. Base legal: execução de contrato. O app instrui exatamente quais extratos exportar e **avisa antes do upload que o CPF e o nome contidos no arquivo são descartados na leitura e não são armazenados**. Nenhuma credencial da B3 é pedida, nunca — nem "só para importar".
- **Integração oficial (Fase 1):** a B3 oferece às plataformas um fluxo em que o **usuário autoriza o compartilhamento dentro da Área do Investidor** e a plataforma recebe posições/movimentações por API. Pré-requisitos: contrato comercial com a B3 (CNPJ), homologação técnica, adesão às exigências de segurança e LGPD da B3 (a B3 é controladora conjunta/operadora conforme o contrato — definir no ROPA), custo por conta conectada. Só entra quando houver contrato; até lá o botão "Conectar B3" **não existe** na interface (sem "em breve").
- **Raspagem com login do usuário: descartada.** Viola os termos da B3, exige guardar credencial de terceiro, e é o pior cenário de incidente possível. Registrado no ADR 11.
- Escopo sempre **somente leitura**; revogação em 1 clique em `/conta/integracoes`; tokens cifrados; `audit_log` em conectar/sincronizar/revogar.

---

## 9. Performance, SEO e conteúdo

- Landing 100% estática (SSG), imagens em AVIF/WebP com `next/image`, fontes com `font-display: swap` e subset latin. Alvos: LCP < 2,0 s no 4G, CLS < 0,05, JS inicial **≤ 170 kB gzip** na landing e **≤ 250 kB** nas páginas de ativo (gráfico carregado sob demanda). Lighthouse ≥ 95 em tudo. *(Revisado em 21/09/2026: o alvo original de 90 kB era inatingível — o runtime do Next 16 + React 19 sozinho, sem código nosso, transfere ~150 kB gzip; o código próprio da landing são ~4 kB. O orçamento é verificado no CI pelo `@lhci/cli`.)*
- **Páginas de ativo são o motor de SEO** (milhares de URLs). ISR com revalidação disparada pelo job `revalidate_pages` após cada carga; `sitemap` segmentado por classe (`/sitemap/acoes.xml`, `/sitemap/fiis.xml`, …) com `lastmod`; título padronizado ("PETR4 — cotação, dividendos e indicadores | Alpherion Finance"), `description` gerada a partir dos dados (sem IA), canônica em maiúsculas, JSON-LD (`Organization` na home, `Corporation` na página da empresa, `Dataset` opcional nos históricos, `VideoObject` em `/videos`, `BreadcrumbList`), links internos (setor, comparador, glossário).
- `lang="pt-BR"`, `metadata` por página, Open Graph com imagem gerada (`next/og` funciona self-hosted) no estilo da thumbnail (navy + uma palavra dourada; nas páginas de ativo, o ticker em dourado + cotação), `robots.txt` (app: `Disallow: /`; screener com parâmetros: `noindex` para evitar explosão de URLs).
- `/leitura` como arquivo semanal: título no padrão do canal, resumo, os números, embed do vídeo. Publicado no mesmo dia do vídeo.
- Nenhum conteúdo gerado por IA é publicado no site público sem revisão humana (regra editorial + regulatória). Descrições e textos das páginas de ativo são templates com dados, não texto gerado.

---

## 10. Ambientes, deploy e operação

| Ambiente | Onde | Dados | Como sobe |
| --- | --- | --- | --- |
| `dev` | Máquina do Bryan | Postgres/Redis em `compose.dev.yml`, seed com a carteira do vídeo 02, **subconjunto do schema `market`** (20 ações, 10 FIIs, Tesouro, top 20 cripto, 3 anos) gerado por `backfill-market.sh --sample`, Mailpit para e-mail | `pnpm dev` + `uvicorn --reload` + jobs à mão |
| `prod` | VPS | Real | `deploy.sh v1.2.3` via GitHub Actions (SSH) → `docker compose pull && up -d` → migrações (`drizzle migrate` no `app`, `alembic upgrade` no `market`) → smoke test (`/`, `/entrar`, `/acoes/PETR4`, `/v1/health`) |

- Sem `staging` no v1 (uma pessoa). Feature flags simples por env para ligar `/planos`, integrações, screener avançado etc.
- Migrations: sempre aditivas na primeira release; destrutivas em release separada após deploy.
- Versionar: `web` e `api` com a mesma tag; `engine_version` e `prompt_version` gravados em cada análise; versão das fórmulas de indicadores em `indicators_daily.inputs`.
- **Bootstrap do `market` em produção:** `backfill-market.sh` (COTAHIST completo, DFP/ITR desde 2010, cadastro, eventos, Tesouro, BCB, cripto) roda **antes** do lançamento, leva horas, e é reexecutável por fonte. Runbook `docs/reprocessar-job.md`.
- Checklist pré-deploy: CI verde · migrações revisadas · `.env` atualizado na VPS · backup manual antes de migração destrutiva · securityheaders/SSL Labs após mudança no nginx · `etl_runs` do dia verdes.

---

## 11. Fases (alinhadas ao roadmap, com as notas de 19/09 e 20/09/2026)

> O roadmap original limitava o v1 a conteúdo, cadastro e análise. Decisão de 19/09/2026: dados de mercado e importação B3 entram no v1 (ADR-014). Decisão de **20/09/2026 (ADR-018)**: o site público passa a ter **paridade funcional com o Status Invest em dado público e ferramentas de carteira** — portal de mercado (busca global, faixa, `/mercado` com Hoje/Eventos, `/agenda`, `/setores`), todas as classes listadas na B3 (ações, FIIs, ETFs, BDRs, índices) mais Tesouro e cripto, comunicados CVM; depois fundos, calendário, rentabilidade, favoritos, alertas; IR na Fase 1; internacional na Fase 2. O que **nunca** entra: nota/score, "melhores", preço justo, ranking editorial, notícias. Para caber, o **v1.0 foi adiado de 25/09 para 09/10/2026**; a Fase 0 não muda. Dentro do v1.0 a ordem é (1) pipeline + páginas de ativo, (2) portal, (3) carteira/B3, (4) análise e lançamento — porque as páginas e o portal são o que os vídeos mostram e o que traz tráfego orgânico desde o primeiro dia. O plano de execução com checklists e tags está em [plano-de-desenvolvimento.md](plano-de-desenvolvimento.md).

### Fase 0 — Landing (dias 5–7 do sprint · antes do vídeo 1 em 21/09) → `v0.1.0`

- [ ] Registro.br + Cloudflare + DNSSEC + SPF/DKIM/DMARC
- [ ] VPS bootstrap (`bootstrap-vps.sh`): usuário, ufw (só Cloudflare), fail2ban, docker, unattended-upgrades, volume para `market`
- [X] `web` com `/`, `/raio-x`, `/sobre`, `/videos`, `/contato`, legais (`/privacidade`, `/termos`, `/aviso-legal`)
- [X] Listmonk + double opt-in + `/lista/*` + registro de consentimento
- [ ] Umami · Uptime Kuma · backup diário com restore testado uma vez
- [ ] Headers A+, Lighthouse ≥ 95, WCAG básico
- [ ] `docs/ropa.md` v1, `docs/incidente.md`, `docs/fontes-de-dados.md` (termos da B3 verificados, incluindo carteiras teóricas — decide a fonte das cotações)

### v1.0 — Portal + app (21/09 → 09/10 · aberto no vídeo 3 em 09/10)

**Bloco 1 · pipeline e páginas de ativo → `v0.2.0` (28/09)**
- [ ] Schema `market` + Alembic (incl. `indices`, `index_daily`, `index_compositions`, `company_documents`, `market_events`); jobs `cotahist_daily`, `b3_listing` (ações, ETFs, BDRs), `b3_corporate_actions`, `b3_index_composition`, `cvm_companies`, `cvm_statements` (DFP anual), `cvm_fii_reports`, `cvm_documents`, `tesouro_daily`, `bcb_series`, `coingecko_*`, `adjust_factors`, `indicators_rebuild`, `market_events_rebuild`, `revalidate_pages`; `backfill-market.sh` rodado em produção
- [ ] Endpoints `/v1/market/*` (overview, strip, movers, events), `/v1/securities*` (perfil, history, dividends, events, documents, financials anual), `/v1/sectors*`, `/v1/indices*`, `/v1/treasury*`, `/v1/crypto*`, `/v1/quotes`, `/v1/assets/search`
- [ ] Páginas `/acoes` (lista + busca + presets), `/acoes/[ticker]` (cotação, histórico, proventos, indicadores, DRE/BP anual, eventos, comunicados, cadastro, mesmo setor), `/fiis`, `/fiis/[ticker]`, `/etfs`, `/etfs/[ticker]`, `/bdrs`, `/bdrs/[ticker]`, `/indices`, `/indices/[slug]`, `/tesouro`, `/tesouro/[slug]`, `/cripto`, `/cripto/[id]`; tooltips de indicadores; `SourceBadge` em tudo; sitemaps por classe; cache de borda
- [ ] Alerta de frescor de dados

**Bloco 2 · portal de mercado → `v0.3.0` (02/10)**
- [ ] Header do site público: `MarketStrip` + `GlobalSearch` (lazy) + menu novo; landing continua ≤ 170 kB gzip e zero cookie
- [ ] `/mercado` completo (faixa, blocos por classe, tabs Hoje/Eventos), `/agenda`, `/setores`, `/setores/[slug]`, `/busca`
- [ ] `content/agenda-macro.json` do ano com fontes; JSON-LD `ItemList`/`Event`; `noindex` em `/busca` e presets

**Bloco 3 · conexão B3 e carteira → `v0.4.0` (06/10)**
- [ ] Auth (magic link + Google), aceite de termos com prova
- [ ] Parsers dos arquivos da Área do Investidor (posição, negociações, proventos) com fixtures anonimizadas e descarte de CPF/nome; `/v1/imports/b3/preview`; `/carteira/importar/b3` com passo a passo e dedupe
- [ ] `transactions`, `income_events`, `position_adjustments`, `positions` derivada; `/carteira` com preço médio e resultado; `/carteira/movimentacoes`; `/carteira/proventos`; carteira manual + CSV genérico

**Bloco 4 · análise e lançamento → `v1.0.0` (09/10)**
- [ ] Engine portado de `ferramentas/` lendo do schema `market`, com golden tests da carteira do vídeo 02; leitura `cost`
- [ ] `POST /v1/analyses` com narrativa + guard; tela de resultado; histórico
- [ ] `/conta`: exportar, excluir, sessões, consentimentos
- [ ] Cifra de movimentações, `audit_log`, `access_log` com purge, rate limits
- [ ] Testes: IDOR, disclaimer obrigatório, guard, parsers, fórmulas de indicadores; smoke test do portal

### v1.x — Semanas 4–12 (uma tag por entrega, nesta ordem)

1. Screener completo com filtros (`/acoes`, `/fiis`, `/etfs`, `/bdrs`) · 2. `/carteira/calendario` + `/favoritos` · 3. ITR, DFC, CAGR e histórico de indicadores · 4. `/carteira/evolucao` + `/carteira/rentabilidade` · 5. `/indicadores` (glossário completo) · 6. `/conta/alertas` · 7. `/comparar` · 8. informes de FII (vacância, imóveis) · 9. **fundos de investimento** (`/fundos`) · 10. `/leitura` como arquivo + `/manifesto` · 11. `analysis_feedback`.

### Fase 1 — Consolidador de verdade (meses 1–4) → `v2.0.0`

- **Integração oficial da B3** (contrato, homologação, `/conta/integracoes`, `b3_connections`, sincronização) · exchanges/wallets read-only · importação de nota de corretagem · **imposto de renda** (`/carteira/ir`, `POST /v1/portfolios/tax`, `tax_periods`, DARF, relatório anual) · alertas por Telegram · 2FA · bot do Telegram consumindo a mesma API.

### Fase 2 — Monetização (meses 3–9) → `v3.0.0`

- Pagamento + `/planos` + NFS-e + CDC (§8.6) · paywall no relatório com IA e em recursos avançados (IR, alertas, histórico longo de indicadores, comparador, rentabilidade detalhada) · **internacional** (stocks, REITs) com provedor licenciado (ADR-019).

### Fase 3+ — Research e consultoria

- Área de assinante com relatórios assinados (CNPI) · relatório do cliente de consultoria gerado a partir da mesma API · segunda versão do aviso legal.

---

## 12. Decisões registradas (ADRs curtos)

| # | Decisão | Alternativa descartada | Por quê |
| --- | --- | --- | --- |
| 1 | Engine e pipeline em Python (FastAPI + worker) separados do Next | Tudo em Next/TS | Reaproveita pandas e garante que vídeo e produto dão o mesmo número; "uma API só" para o bot |
| 2 | Auth self-hosted (biblioteca) | Clerk/Auth0 | Dados de login no Brasil, sem custo por MAU, sem mais um suboperador na política |
| 3 | Listmonk self-hosted | Mailchimp/Beehiiv | A lista é o ativo; exportável, sem limite de contatos, LGPD mais simples |
| 4 | Umami sem cookie | GA4 | Sem banner, sem transferência de dado de navegação, suficiente para as métricas da fase |
| 5 | Yahoo Finance fora do produto | Usar como nos scripts | Sem termos de uso para produto; CVM/B3/Tesouro/BCB/CoinGecko são oficiais ou licenciados |
| 6 | Narrativa nunca bloqueia a análise | Falhar se o LLM falhar | Os números são o produto; a narrativa é tradução. Fallback genérico mantém o SLA e a conformidade |
| 7 | Sem senha no v1 | E-mail + senha | Menos superfície (sem hash, sem reset, sem credential stuffing); magic link já basta para o fluxo |
| 8 | Movimentações e posições cifradas na aplicação | Só cifra de disco | Dump de banco não expõe carteira; custo baixo de implementar |
| 9 | Sem banner de cookies | Banner "para garantir" | Não há cookie não essencial; banner sem necessidade é ruído e reduz conversão |
| 10 | Pipeline próprio sobre fontes oficiais e gratuitas | Provedor pago (brapi PRO, Fintz) | Custo zero de dado, controle das fórmulas, atribuição direta à fonte, sem dependência de terceiro. Custo: construir e manter o pipeline. Fallback licenciado só se os termos da B3 exigirem (§8.10) |
| 11 | Importação de arquivos da Área do Investidor no v1; integração oficial da B3 na Fase 1; **nunca raspagem com credencial** | Pedir login da B3 ao usuário | Funciona hoje sem contrato; zero credencial de terceiro; a integração oficial é o caminho correto e exige contrato que a Fase 1 comporta |
| 12 | Posições derivadas de movimentações (+ ajustes manuais) | Posição como dado primário | Preço médio, proventos e evolução exigem histórico; a posição manual continua existindo como ajuste |
| 13 | API passa a ter schema próprio (`market`) | API stateless sem tabelas (decisão anterior) | O dado de mercado é da API por definição; `web` continua sem acesso direto ao schema |
| 14 | Competir em dado **e** em leitura | "Não competir com Status Invest em dado" (roadmap original) | Páginas de ativo trazem tráfego orgânico independente do canal e alimentam a carteira; o diferencial continua sendo a leitura, mas o dado é a porta. Decisão de 19/09/2026, refletida no roadmap |

---

## 13. Placeholders a preencher antes de publicar

- `[RAZÃO SOCIAL]`, `[CNPJ]`, `[ENDEREÇO]` da ME — rodapé, termos, política.
- Nome do encarregado e e-mail `privacidade@` funcionando (com resposta automática confirmando recebimento).
- Localização da VPS e do storage de backup (Brasil ou exterior) — muda a seção de transferência internacional.
- Provedor de e-mail escolhido e seu DPA.
- Versão `v1.0` dos textos legais com data — o app grava essa versão no aceite.
- **Resultado da verificação dos termos da B3** (§8.10) — decide se as cotações vêm do COTAHIST ou de provedor licenciado.
- Chave da CoinGecko (Demo) e texto de atribuição.
- Prints do passo a passo de exportação da Área do Investidor (para `/carteira/importar/b3`).
- URL e termos verificados da carteira teórica dos índices da B3 (mesma verificação do COTAHIST).
- `content/agenda-macro.json` do ano corrente (Copom, IPCA, FOMC, vencimentos) com `source_url` em cada item.
- Provedor de dados internacionais, contrato e limites (Fase 2, ADR-019).

---

## 14. Convenção de módulos (para os próximos prompts)

Cada funcionalidade nova entra neste documento como um **módulo**, com o mesmo bloco de campos, para que rotas, dados, segurança e conformidade nasçam juntos:

| Campo | O que preencher |
| --- | --- |
| Objetivo no funil | Qual dos três públicos atende e qual métrica move |
| Rotas | Site público e/ou app, com renderização e fase |
| Endpoints | Na API única (nunca lógica nova no `web`) |
| Tabelas | Schema `app` (dado do usuário) ou `market` (dado público); retenção; o que é cifrado |
| Fonte de dados e licença | Fonte oficial, formato, frequência, termos verificados em `docs/fontes-de-dados.md` |
| Regra legal | LGPD (base legal, novo item no ROPA), CVM (fato vs opinião), CDC se cobrar, outra específica |
| Segurança | Superfície nova (upload, integração, token) e como é limitada |
| Fase | v1.0 · v1.x · Fase 1 · 2 · 3 |
| ADR | Decisão e alternativa descartada, se houver |

### Módulos já especificados

| Módulo | Seções |
| --- | --- |
| Landing e lista de e-mail | §2.1, §4.1, §5, §8.1, §8.8 |
| Conta e direitos do titular | §2.2, §4.1, §8.1 |
| Carteira, movimentações e importação (CSV, B3) | §2.2, §2.3, §4.2, §7.4, §8.11 |
| Análise por IA (cinco leituras + custo) | §2.3, §6 |
| Dados de mercado (ações, FIIs, Tesouro, cripto, screener, comparador, glossário) | §2.1, §2.3, §3.5, §4.3, §5, §8.10, §9 |
| Conexão oficial B3 | §2.2, §4.2, §8.11, Fase 1 |
| Portal de mercado (header com faixa e busca global, `/mercado` Hoje/Eventos, `/agenda`, `/setores`, `/busca`) | §1 (público 4), §2.1, §2.3, §3.5 (agenda macro), §4.3 (`market_events`), §5, §8.10, §9, ADR-018 |
| ETFs, BDRs e índices (páginas e composição) | §2.1, §2.3, §3.5 (carteiras teóricas), §4.3 (`securities`, `indices*`), §8.10 |
| Comunicados CVM (IPE) por empresa e na agenda | §2.1, §2.3, §3.5, §4.3 (`company_documents`), §8.3 |
| Fundos de investimento (CVM) | §2.1, §2.3, §3.5, §4.3 (`funds`, `fund_daily`), v1.x |
| Carteira avançada (calendário, rentabilidade TWR, favoritos, alertas) | §2.2, §2.3, §4.2 (`watchlist_items`, `alerts`), §4.5, v1.x |
| Imposto de renda | §2.2, §2.3, §4.2 (`tax_periods`), §4.5, §8.3, Fase 1 |
| Internacional (stocks, REITs) | §2.1, §3.5, §4.3 (`securities.market`), §8.10, Fase 2, ADR-019 (pendente) |

### Próximos módulos

_(a preencher conforme chegarem — um bloco por módulo, no formato acima)_
