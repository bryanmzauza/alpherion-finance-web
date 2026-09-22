# Plano de desenvolvimento — Alpherion Finance

> Versão do plano: **2.0** · Data: 20/09/2026 · Responsável: Bryan
> Especificação de referência: [site.md](site.md) · Estratégia: [roadmap.md](roadmap.md) · Decisões: [adr/](adr/README.md)
> Regra: a **ordem** das etapas é fixa (§11 do site.md). As datas são metas; se escorregarem, a ordem não muda.

## Histórico do plano

| Versão | Data       | Mudança                                                                                                                                                             |
| ------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1.0     | 19/09/2026 | Plano inicial a partir do site.md. Decisões: monorepo, SemVer com tags por marco, Better Auth. Auth antecipada para o início do Bloco 2 (a carteira exige sessão) |
| 1.0     | 19/09/2026 | Nota (sem mudança de escopo): Etapa 1 entregue com Next.js 16 (site.md §3.4 diz "15+"); texto da etapa ajustado                                                    |
| 2.0     | 22/09/2026 | Nota (sem mudança de escopo): Etapa 3.2 — fontes da CVM entregues (cadastro, DFP/ITR, FCA, informes de FII, IPE). O leitor do FRE (free float) fica para a entrega dos indicadores, que é onde o número é usado; até lá `company_facts.free_float` fica `null` e a página mostra "—" |
| 2.0     | 22/09/2026 | Nota (sem mudança de escopo): Etapa 2.6 entregue — compose de produção, nginx, scripts de operação, `deploy.yml` e runbook de deploy. Falta só a parte manual (domínio, Cloudflare, VPS, e-mail) |
| 2.0     | 21/09/2026 | Nota (sem mudança de escopo): Etapa 2.4 entregue com CSP sem nonce no site público e orçamento de JS de 170 kB gzip (site.md §7.3 e §9 revisados com a justificativa) |
| 2.0     | 20/09/2026 | **Paridade funcional com o Status Invest** ([ADR-018](adr/ADR-018-paridade-status-invest.md)). v1.0 adiado de 25/09 para **09/10/2026**. Entram no v1.0: portal de mercado (header com faixa e busca global, `/mercado` Hoje/Eventos, `/agenda`, `/setores`, `/busca`), ETFs, BDRs, índices com composição, comunicados CVM. v1.0 dividido em quatro blocos (`v0.2.0` → `v0.4.0` → `v1.0.0`). v1.x reordenado (11 entregas) com calendário da carteira, favoritos, rentabilidade TWR, alertas e fundos de investimento. IR na Fase 1; internacional na Fase 2 (ADR-019 pendente). Etapas 0–2 inalteradas |

## Como este plano é mantido

- Cada etapa tem entregas em checklist, critério de **pronto** e a **tag** que fecha o marco.
- Marcar os checkboxes aqui mesmo, no commit da entrega.
- Mudança de escopo ou de ordem → incrementa a versão do plano, entra no histórico acima, commit `docs(plano): …`.
- Funcionalidade nova entra primeiro no `site.md` como módulo (§14) e só depois vira etapa aqui.

## Convenções de versionamento

| Item           | Regra                                                                                                                                                                                                                                         |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Versão        | SemVer.`web` e `api` sempre com a **mesma tag** (site.md §10). `engine_version` e `prompt_version` são versionados à parte dentro da API e gravados em cada análise                                                         |
| Tags por marco | `v0.0.1` bootstrap · `v0.1.0` Fase 0 no ar · `v0.2.0` Bloco 1 (pipeline + páginas de ativo) · `v0.3.0` Bloco 2 (portal de mercado) · `v0.4.0` Bloco 3 (carteira/B3) · `v1.0.0` app aberto · `v1.1.0+` entregas do v1.x · `v2.0.0` Fase 1 (B3 oficial, IR) · `v3.0.0` Fase 2 (pagamento, internacional) |
| Branches       | `main` sempre deployável. Uma branch curta por item (`feat/landing-hero`, `feat/api-cotahist`). Squash na `main`. Depois da `v0.1.0`, nunca commitar direto na `main`                                                            |
| Commits        | Conventional Commits em pt-BR:`feat:`, `fix:`, `docs:`, `chore:`, `infra:`, `data:`, `test:`. Escopo opcional: `feat(web):`, `feat(api):`                                                                                   |
| CHANGELOG      | [CHANGELOG.md](../CHANGELOG.md) no formato Keep a Changelog; `[Unreleased]` acumula entre tags e vira a seção da tag no fechamento                                                                                                         |
| Deploy         | Só por tag (`deploy.yml` dispara em `v*`). Migrations aditivas na tag; destrutivas em tag separada, após deploy                                                                                                                         |

## Calendário (metas)

| Data       | Marco                                                                | Tag        |
| ---------- | -------------------------------------------------------------------- | ---------- |
| 21/09/2026 | Fase 0 no ar; **vídeo 1** publicado                                  | `v0.1.0`   |
| 28/09/2026 | Pipeline de dados + páginas de ativo de todas as classes             | `v0.2.0`   |
| 02/10/2026 | Portal de mercado (header, `/mercado`, `/agenda`, setores); **vídeo 2** demonstra o portal e o raio-x | `v0.3.0`   |
| 06/10/2026 | Auth, carteira, importação B3                                         | `v0.4.0`   |
| 09/10/2026 | Análise por IA, conta, segurança; **vídeo 3** abre o app             | `v1.0.0`   |
| semanas 4–12 | Onze entregas do v1.x, uma tag cada                                | `v1.1.0`…`v1.11.0` |

---

## Etapa 0 — Bootstrap do repositório → `v0.0.1`

- [X] Estrutura de pastas do monorepo (site.md §3.3)
- [X] `site.md`, `brand-kit.md`, `roadmap.md` em `docs/`
- [X] Este plano, ADRs, README, CHANGELOG, `.gitignore`, `.editorconfig`, `infra/env/.env.example`
- [X] Commit inicial na `main` + tag `v0.0.1`

**Pronto quando:** árvore criada, docs no lugar, tag existe.

## Etapa 1 — Fundação técnica (sem feature)

Objetivo: `pnpm dev` e `uvicorn --reload` sobem localmente com banco, e o CI roda verde.

- [X] `corepack enable` → `pnpm-workspace.yaml` (`apps/*`), `package.json` raiz com `dev`, `lint`, `typecheck`, `test`, `build`
- [X] `apps/web`: Next.js 15+ App Router, TS strict, Tailwind, ESLint. Pastas `app/`, `components/`, `lib/`, `content/`, `drizzle/`, `public/`. Route groups `(site)`, `(market)`, `(app)`, `(auth)`, `api/`. Fontes Playfair Display + Inter via `next/font/local` (arquivos no repo). `next.config.ts` com `output: "standalone"`
- [X] `apps/web/lib`: `db` (Drizzle, schema `app`), `validation` (zod), `env.ts` (env validado no boot), `api-client.ts` (token de serviço)
- [X] `apps/api`: `pyproject.toml` (FastAPI, pydantic v2, SQLAlchemy 2, Alembic para schema `market`, pandas/numpy, httpx, redis, arq, pytest, ruff, mypy). Pacote `alpherion/` com subpacotes do §3.3, `settings.py`, `routers/health.py` (`GET /v1/health`, sem versão)
- [X] Auth por token de serviço na API (`Authorization: Bearer`, escopos `analyses:write`, `imports:write`, `market:read`, `quotes:read`)
- [X] `infra/compose.dev.yml`: postgres 16 (usuários `web`→`app`, `api`/`data`→`market`, `init.sql` com GRANTs do §7.6), redis 7 com senha, mailpit
- [X] Dockerfiles: web (`node:22-slim`, non-root, standalone) e api (`python:3.12-slim`, non-root; mesma imagem roda `api` ou `data`)
- [X] `.github/workflows/ci.yml`: web (lint, typecheck, test, build) + api (ruff, mypy, pytest) + `pnpm audit`/`pip-audit`. Dependabot semanal
- [X] `apps/web/app/design` (só em dev): tokens do §5, tipografia, `color-scheme: dark`

**Pronto quando:** compose dev sobe; `pnpm dev` e `uvicorn` sobem; `/v1/health` responde; CI verde. Sem tag (fecha junto com a `v0.1.0`).

## Etapa 2 — Fase 0: landing, legais, lista, infra de produção → `v0.1.0`

Meta: no ar antes do vídeo 1 (21/09). SSG/ISR, zero cookie no site público.

### 2.1 Componentes base (`components/ui/`)

- [X] `Button`, `Input`, `Checkbox`, `Card`, `Badge`, `Table`, `Tooltip`, `Disclaimer`, `EmailCapture`, `VideoEmbed` (youtube-nocookie, carrega no clique), `Gold` (regra da palavra dourada)
- [X] Foco visível, `aria-*`, contraste AA (dourado só em texto grande)

### 2.2 Páginas (`app/(site)/`)

- [X] `/` com as 10 seções do §5, na ordem
- [X] `/raio-x` (cinco leituras com os números do vídeo 02: 38% · 0,91 · 0,96 · −34% · 0,03%)
- [X] `/sobre`, `/contato`, `/videos` (ISR sobre `content/videos.json`)
- [X] `/privacidade`, `/termos`, `/aviso-legal` em MDX (`content/legal/`) com `version` e `date` no frontmatter
- [X] `not-found.tsx`; placeholders do §13 centralizados em `content/site.ts`
- [X] Imagens da marca em `public/brand/` (copiar de `alpherion-finance-yt/brand/imagens/`)

### 2.3 Lista de e-mail

- [X] Listmonk no compose (banco próprio), double opt-in, `List-Unsubscribe` one-click
- [X] `POST /api/subscribe`: zod, rate limit Redis 10/min/IP, honeypot, chama Listmonk, grava `consents` (`document_version`, ip, user_agent, `source="landing"`)
- [X] Tabelas `consents` e `data_requests` — primeira migration Drizzle do schema `app`
- [X] `/lista/obrigado`, `/lista/confirmar?t=`, `/lista/sair?t=` (SSR; sem login, sem "tem certeza?")
- [X] Eventos Umami `subscribe_submit`, `subscribe_confirm`

### 2.4 SEO, performance, acessibilidade

- [X] `metadata` por página, `lang="pt-BR"`, OG via `next/og` (navy + palavra dourada; `lib/og.tsx`, uma imagem por rota), JSON-LD `Organization` e `VideoObject`
- [X] `sitemap.ts`, `robots.ts`, `manifest.webmanifest`
- [X] Headers do §7.3 em `next.config.ts` — **CSP sem nonce no site público** (nonce exigiria renderização dinâmica e mataria SSG/ISR; ver §7.3 revisado); nonce só no app, Etapa 5
- [X] Lighthouse ≥ 95 no CI (`@lhci/cli`, job `lighthouse`) em `/` e `/raio-x`; orçamento de JS **≤ 170 kB gzip** (§9 revisado: a base do Next 16 é ~150 kB); 100/100/100/100 localmente

### 2.5 Documentos obrigatórios (`docs/`)

- [X] `ropa.md` v1 · `runbooks/incidente.md` · `runbooks/restore.md` · `runbooks/rotacao-de-chave.md`
- [X] `fontes-de-dados.md`: termos de CVM (Dados Abertos, IPE, Fundos), Tesouro, BCB, CoinGecko **e verificação da B3** (§8.10: COTAHIST, listagem, eventos **e carteiras teóricas de índices**) → **ADR-017 (proposta)**: B3 exige licença (termos do site + Política de Consumo 2026) e o CoinGecko Demo não é comercial → preço e cripto ficam atrás de feature flag até a licença; e-mail de consulta à B3 rascunhado em `docs/fontes-de-dados/email-b3-licenca.md`
- [ ] **Bryan:** enviar o e-mail à B3, decidir a opção de lançamento do ADR-017 (A/B/C) e a fonte de cripto (CoinGecko Analyst ou exchange); registrar a resposta em `fontes-de-dados.md` e mudar o ADR para "aceita"

### 2.6 Infra de produção (`infra/`)

- [X] `compose.yml` (nginx, web, api, data, postgres, redis, umami, listmonk, uptime-kuma; **três** redes — `edge`, `internal` sem saída e `egress` para as fontes externas; só nginx publica 80/443; volume separado para `market`; volume de log do nginx para os 6 meses do Marco Civil)
- [X] `nginx/nginx.conf`, `sites/*.conf` (site, app, api, serviços, default que fecha), `snippets/` (`tls.conf`, `security-headers.conf` **só com HSTS** — o resto vem do Next, §7.3 —, `cache-market.conf`), `cloudflare/real-ip.conf`. Upstreams por variável + resolver do Docker: um serviço fora não impede o nginx de subir. Validado com `nginx -t`
- [X] `scripts/bootstrap-vps.sh`, `update-cloudflare-ips.sh` (nginx + ufw), `deploy.sh` (backup → migrações → up → healthcheck → smoke test → rollback), `backup.sh` (pg_dump → age → S3, manifesto de contagens, alerta no Telegram), `restore-test.sh` (Postgres efêmero + conferência). Todos passam no `shellcheck`
- [X] `apps/web/scripts/migrate.mjs` + cópia das migrations na imagem: o standalone não tem `drizzle-kit` (devDependency). Testado contra o Postgres de dev, mesma tabela de controle do `pnpm db:migrate`
- [X] `.github/workflows/deploy.yml` (tag `v*` → lint/typecheck/test → build → GHCR → environment `production` → ssh → `deploy.sh`)
- [ ] Manual: **checklist completo em [`docs/runbooks/deploy.md`](runbooks/deploy.md)** — Registro.br + DNSSEC · Cloudflare (proxy, TLS Full strict, Authenticated Origin Pulls, WAF, rate limit, Access nos painéis) · SPF/DKIM/DMARC (apex e `news.`) · provedor SMTP escolhido · VPS + `bootstrap-vps.sh` · Umami · Uptime Kuma · backup rodando + **um restore testado**

**Pronto quando:** `alpherion.com.br` no ar com as páginas da Fase 0; um e-mail real confirmado por double opt-in; securityheaders A+; SSL Labs A+; Lighthouse ≥ 95; `fontes-de-dados.md` com a B3 verificada. → **tag `v0.1.0`**.

## Etapa 3 — v1.0 Bloco 1: pipeline de dados + páginas de ativo → `v0.2.0` · meta 28/09

Por que primeiro: é o que os vídeos mostram e o que traz tráfego orgânico. Tudo na API; o `web` nunca lê `market` direto. Cobre **todas as classes listadas na B3** (ações, units, FIIs, ETFs, BDRs, índices) mais Tesouro e cripto — o portal da Etapa 4 só monta em cima disso.

> **Condição do ADR-017:** cotação, histórico, indicadores de preço, índices e cripto só vão a produção com licença registrada em `fontes-de-dados.md`. Até lá ficam atrás das flags `MARKET_B3_PRICES_ENABLED` e `MARKET_CRYPTO_ENABLED` (padrão `false` em produção) e **toda página e componente de mercado precisa renderizar com `price = null`** ("—" com o motivo). O pipeline e os jobs são construídos normalmente (uso em dev não é distribuição).

### 3.1 Schema `market` (SQLAlchemy + Alembic)

- [X] Tabelas do §4.3: `securities` (com `market`, `sector_slug`, `etf_index_slug`, `bdr_ratio`), `daily_quotes` (particionada por ano, 1986→ano+1), `corporate_actions`, `financial_statements`, `company_facts`, `indicators_daily`, `fii_reports`, `treasury_bonds`, `treasury_daily`, `macro_series`, `crypto_assets/daily/metrics`, `etl_runs`, `data_sources`
- [X] Tabelas novas do portal: `indices`, `index_daily`, `index_compositions`, `company_documents`, `sectors`
- [ ] `market_events` (view materializada) — entra junto com o job `market_events_rebuild` (3.3)
- [X] Índices em todo campo filtrável; busca por nome com `pg_trgm` + `unaccent` (via `market.immutable_unaccent`, porque `unaccent()` não é IMMUTABLE); `statement_timeout 5s` no usuário `api` (já no `init.sql`)
- [X] `data_sources` semeada na migration com o resultado da verificação de termos: B3 e CoinGecko **sem** `terms_checked_at` (bloqueadas, ADR-017)
- [X] Flags `MARKET_B3_PRICES_ENABLED` e `MARKET_CRYPTO_ENABLED` em `settings.py` (padrão `false`)

### 3.2 Sources + transform (cada um com teste sobre fixture pequena)

- [X] `cotahist_parser.py` (layout posicional oficial, rev. 01 de 13/04/2017: 245 bytes, preços `(11)V99`, `FATCOT` normalizado para preço unitário, filtro de mercado à vista) + `b3_cotahist.py` (download diário/anual, arquivo descartado depois) — fonte licenciada troca só o `b3_cotahist.py` (ADR-017)
- [ ] `b3_listing.py` (ações, units, **ETFs, BDRs**, FIIs) + `b3_events.py` (eventos; fallback CVM/FRE documentado)
- [ ] `b3_indices.py`: carteira teórica e fechamento dos índices (Ibovespa, IFIX, IDIV, SMLL, IBRX 100, IBRA, IFNC, IMOB, UTIL); fallback = manter a última carteira e expor a data
- [X] `cvm.py` (cadastro de cias e de FIIs, DFP/ITR, FCA, informes mensais de FII) + `cvm_statements.py` (formato longo; escala de moeda normalizada, só o exercício corrente, versão mais recente por período). **Falta o FRE** (free float) — vai junto com os indicadores que o usam
- [X] `cvm_documents.py` (IPE: metadados + link; incremental por data de entrega; **nunca baixa o documento** — há teste que conta as requisições)
- [X] `tesouro.py` (CSV do Tesouro Transparente, decimal pt-BR, slug estável por vencimento) e `bcb.py` (códigos SGS documentados num só lugar; HTML do SGS fora do ar não vira série vazia) — **fontes liberadas** (ODbL / dados abertos)
- [ ] `coingecko.py` (só dev até a fonte licenciada — ADR-017)
- [X] `adjust.py` (fator acumulado de proventos, desdobramento, grupamento e bonificação; evento sem fechamento `cum` é ignorado) e `indicators.py` (fórmulas; `null` **com motivo** quando falta entrada; `FORMULAS_VERSION` em `inputs`) + `cvm_accounts.py` (plano de contas → conceitos; depreciação por nome, porque a CVM não a padroniza). Testes contra casos calculados à mão
- [ ] `events.py`: monta `market_events` a partir de `corporate_actions`, `company_documents` e `content/agenda-macro.json`
- [X] Proteções §7.5 em `sources/http.py`: lista fechada de hosts (revalidada a cada redirect), limite de download pelo que chega (não pelo `Content-Length`), limite de descompressão e neutralização de caminho de fuga no ZIP — com testes

### 3.3 Jobs (idempotentes, lock no Redis, registram `etl_runs`)

- [ ] `cotahist_daily`, `b3_listing`, `b3_corporate_actions`, `b3_index_composition`, `cvm_companies`, `cvm_statements` (DFP anual), `cvm_fii_reports`, `cvm_documents`, `tesouro_daily`, `bcb_series`, `coingecko_prices`, `coingecko_history`, `adjust_factors`, `indicators_rebuild`, `market_events_rebuild`, `revalidate_pages`
- [ ] Agendamento por cron do host (preferido) ou `scheduler.py`
- [ ] `infra/scripts/backfill-market.sh` com `--sample` (20 ações, 10 FIIs, 5 ETFs, 5 BDRs, 3 índices, Tesouro, top 20 cripto, 3 anos, IPE de 90 dias) para dev
- [ ] `docs/runbooks/reprocessar-job.md`

### 3.4 Endpoints de mercado

- [ ] `GET /v1/market/overview` · `/v1/market/strip` · `/v1/market/movers` (métrica de lista fechada, `min_volume`) · `/v1/market/events`
- [ ] `/v1/securities` (lista + busca; `type=stock|fii|etf|bdr`; presets de ordenação; paginação ≤ 100) · `/v1/securities/{ticker}` · `/history` · `/dividends` · `/events` · `/documents` · `/financials?period=annual`
- [ ] `/v1/sectors` · `/v1/sectors/{slug}` · `/v1/indices` · `/v1/indices/{slug}` · `/composition` · `/history`
- [ ] `/v1/treasury*` · `/v1/crypto*` (+ `/correlations`) · `/v1/quotes` · `/v1/assets/search` (todas as classes + índices, agrupado por classe)
- [ ] `POST /v1/market/weekly-reading` (porta de `ferramentas/leitura-semanal.py`)
- [ ] Cache Redis (cotação 5 min; strip 5 min; movers 5 min); todo bloco de resposta com `source`, `document`, `updated_at`
- [ ] Flags `MARKET_B3_PRICES_ENABLED` / `MARKET_CRYPTO_ENABLED` na API: com `false`, campos de preço vêm `null` com `reason`; `data_sources.terms_checked_at` vazio bloqueia o job em produção (ADR-017)

### 3.5 Páginas de mercado (`app/(market)/`, ISR, container 1280)

- [ ] `components/market/`: `PriceHeader`, `HistoryChart` (leve, client-only, lazy, tabela como fallback), `IndicatorGrid` (tooltip a partir de `content/indicadores/*.mdx`), `FinancialTable`, `DividendTable` + `DividendChart`, `EventList` (eventos corporativos + próximos data-com/pagamentos), `DocumentList` (comunicados CVM: categoria, assunto, data, link), `IndexCompositionTable`, `TreasuryTable`, `CryptoTable`, `SourceBadge`, `AssetCTA`, `TickerLink`, `SameSectorList`
- [ ] Rotas: `/acoes`, `/acoes/[ticker]` (com abas Eventos e Comunicados, cadastro, mesmo setor), `/fiis`, `/fiis/[ticker]`, `/etfs`, `/etfs/[ticker]`, `/bdrs`, `/bdrs/[ticker]`, `/indices`, `/indices/[slug]`, `/tesouro`, `/tesouro/[slug]`, `/cripto`, `/cripto/[id]`
- [ ] Redirects: ticker minúsculo → maiúsculo (301); ticker na rota da classe errada → 301 para a classe certa; inexistente → 404 com busca; `www.` → apex
- [ ] `app/api/revalidate` (token) chamado pelo job `revalidate_pages`
- [ ] Sitemaps segmentados por classe (`/sitemap/acoes.xml`, `fiis`, `etfs`, `bdrs`, `indices`, `tesouro`, `cripto`) com `lastmod`; título/description por template; JSON-LD `Corporation` + `BreadcrumbList`; OG com ticker dourado + cotação; `Cache-Control: public, s-maxage=3600, stale-while-revalidate=86400`
- [ ] Seção "Dados de mercado" da landing linkando de verdade (agora com 7 links: ações, FIIs, ETFs, BDRs, índices, Tesouro, cripto)

### 3.6 Operação

- [ ] Alerta de frescor (endpoint interno lendo `etl_runs` do dia; alerta se `cotahist_daily` não rodou até 21h ou se `cvm_documents`/`b3_index_composition` falharam 2 dias seguidos) → Telegram
- [ ] `backfill-market.sh` completo rodado em produção **antes** da tag

**Pronto quando:** `/acoes/PETR4`, `/fiis/MXRF11`, `/etfs/BOVA11`, `/bdrs/AAPL34`, `/indices/ibovespa` (com composição datada), `/tesouro/…`, `/cripto/bitcoin` no ar com dados reais; comunicados da PETR4 listados com link para a CVM; todo número com `SourceBadge`; testes de parser/fórmulas verdes; jobs no cron; sitemap no Search Console. → **tag `v0.2.0`**.

## Etapa 4 — v1.0 Bloco 2: portal de mercado → `v0.3.0` · meta 02/10

O que o visitante do Status Invest espera ao abrir o site: faixa de índices, busca de ticker em qualquer página, "o que aconteceu hoje" e "o que vem esta semana". Só monta sobre os endpoints da Etapa 3; nenhuma lógica nova no `web`.

### 4.1 Header do site público

- [ ] `MarketStrip` (server component; `GET /v1/market/strip` com `revalidate: 300`; "—" quando a API não responde; a landing continua SSG/ISR e estática por 5 min)
- [ ] `GlobalSearch` (client component carregado **no foco**; `app/api/market/search` com rate limit 30/min/IP → `/v1/assets/search`; teclado e `aria-*` completos; Enter sem seleção → `/busca?q=`)
- [ ] Menu novo: Ações · FIIs · ETFs · BDRs · Índices · Tesouro · Cripto · Setores · Agenda · Raio-X · Vídeos (mobile: drawer)
- [ ] Teste: landing continua < 90 kB gzip de JS inicial e **zero cookie** (Playwright/CI verifica `document.cookie === ""` e ausência de `Set-Cookie`)

### 4.2 `/mercado` (portal)

- [ ] Faixa completa (Ibovespa, IFIX, IDIV, SMLL, PTAX, Selic, CDI 12 m, IPCA 12 m, BTC) com `SourceBadge` por item
- [ ] Blocos por classe com contadores factuais (`/v1/market/overview`) e links
- [ ] Tab **Hoje**: `MoversList` ×3 (maiores altas, maiores baixas, mais negociadas por volume financeiro) com a métrica no título e `min_volume`
- [ ] Tab **Eventos**: data-com e pagamentos do dia/semana, comunicados relevantes do dia, macro
- [ ] `GlobalSearch` em destaque; disclaimer e rodapé de fontes (§8.10)

### 4.3 `/agenda`

- [ ] `EventCalendar` semanal (padrão) e mensal; `/agenda/[ano]-[semana]` ISR; filtros por classe e tipo (proventos, comunicados, macro) na URL
- [ ] `content/agenda-macro.json` do ano (Copom, IPCA/IPCA-15, IGP-M, FOMC, vencimentos de opções e índices) com `source_url` em cada item; teste de schema
- [ ] JSON-LD `Event` por item; `noindex` em semanas passadas além de 12 meses

### 4.4 `/setores` e `/setores/[slug]`

- [ ] `SectorTree` (setor → subsetor → segmento B3; segmentos de FII)
- [ ] Página do setor: tabela ordenável (cotação, variação, liquidez, P/L, P/VP, DY 12 m, market cap; padrão liquidez; URL com estado), agregados factuais, JSON-LD `ItemList`
- [ ] `SameSectorList` nas páginas de ativo linkando para o setor

### 4.5 `/busca?q=` e presets

- [ ] Resultado agrupado por classe (SSR, `noindex`)
- [ ] Presets de ordenação em `/acoes` e `/fiis` por URL (`?sort=&dir=`) com título neutro ("Maior dividend yield 12 m"); `noindex` com parâmetros; **nunca** "melhores/baratas/oportunidades" (teste de lint de conteúdo sobre `content/` e títulos)

### 4.6 SEO e operação

- [ ] Sitemaps: `/sitemap/setores.xml`, `/sitemap/agenda.xml`; `/mercado` e `/agenda` revalidadas pelo `revalidate_pages` após `market_events_rebuild`
- [ ] Umami: eventos `search_open`, `search_select`, `agenda_filter`
- [ ] **Vídeo 2 (02/10)** demonstra o portal e o raio-x (ambiente de produção, carteira ilustrativa)

**Pronto quando:** header com faixa e busca em todas as páginas do site público; `/mercado`, `/agenda`, `/setores/[slug]` e `/busca` no ar com dados reais; teste de zero cookie e orçamento de JS verdes; Lighthouse ≥ 95 em `/mercado`. → **tag `v0.3.0`**.

## Etapa 5 — v1.0 Bloco 3: auth, carteira, movimentações, importação B3 → `v0.4.0` · meta 06/10

### 5.0 Auth (antecipada: a carteira exige sessão)

- [ ] Better Auth + adapter Drizzle (`users`, `sessions`, `accounts`, `verification_tokens`); magic link (uso único, 15 min, hash) via SMTP + Google OAuth (PKCE); cookie `HttpOnly Secure SameSite=Lax`, 30 dias sliding
- [ ] `/entrar` com checkbox Termos+Privacidade **não pré-marcado** gravando `consents` com a versão do MDX · `/entrar/verificar`
- [ ] Middleware em `(app)/`; `/` do app redireciona conforme existência de carteira; redirects `/entrar`, `/cadastro`, `/carteira` do domínio público → app
- [ ] `audit_log` append-only (GRANT sem UPDATE/DELETE) com `login`/`logout`

### 5.1 Schema `app` carteira (Drizzle, migration aditiva)

- [ ] `portfolios`, `transactions`, `income_events`, `position_adjustments`, `import_batches`, `assets` (com `factor_map` vindo do `FATORES` de `raio-x-carteira.py` + setor B3 por padrão; `asset_class` cobre `etf_br` e `bdr` desde já)
- [ ] `lib/crypto.ts` AES-256-GCM com `key_version` para as colunas cifradas do §7.4
- [ ] `lib/positions.ts`: derivação em memória (PM pelo método da Receita + ajustes)

### 5.2 Importadores na API

- [ ] `importers/b3/posicao.py`, `negociacao.py`, `proventos.py`, `importers/csv.py`: openpyxl `read_only`, sem macros, limites de linhas/células/tamanho descomprimido, checagem de conteúdo, **descarte de CPF/nome antes de qualquer log**, `external_key` = hash (ativo, data, tipo, qtd, preço)
- [ ] Fixtures anonimizadas em `tests/fixtures/b3/` (incluindo linhas de ETF e BDR)
- [ ] `POST /v1/imports/b3/preview`, `POST /v1/imports/csv/preview`, `POST /v1/portfolios/valuation`

### 5.3 Telas (`app/(app)/carteira/`)

- [ ] `/carteira/nova` (2 passos) · `/carteira/importar` (CSV; `public/csv-modelo.csv`) · `/carteira/importar/b3` (passo a passo com prints; aviso de descarte de CPF/nome **antes** do upload; 1–3 arquivos ≤ 5 MB; prévia; avisos por linha; dedupe por hash de arquivo e `external_key`)
- [ ] `/carteira` (PM, atual, resultado, peso; **Analisar** desabilitado até a Etapa 6) · `/carteira/movimentacoes` · `/carteira/proventos` (yield on cost como fato)
- [ ] Busca de ativo no app reaproveita `GlobalSearch` (mesmo componente, mesma API)
- [ ] Route handlers `app/api/portfolio/*`, `app/api/imports/*` filtrando **sempre** por `user_id` da sessão
- [ ] Evento Umami `b3_import`

**Pronto quando:** usuário real entra por magic link, importa os 3 arquivos da Área do Investidor, vê posições com PM correto (fixture conhecida); reenvio não duplica; teste IDOR passa. → **tag `v0.4.0`**.

## Etapa 6 — v1.0 Bloco 4: engine, análise por IA, conta, segurança, lançamento → `v1.0.0` · 09/10

### 6.1 Engine (`alpherion/engine/`)

- [ ] Portar `ferramentas/raio-x-carteira.py` em `concentration.py`, `correlation.py`, `exposure.py`, `drawdown.py`, `liquidity.py`, `cost.py`, lendo `market.daily_quotes` (ajustado), `macro_series` (Selic real), `crypto_daily`
- [ ] `tests/test_engine_golden.py` com a carteira do vídeo 02 → **38% / 0,91 / 0,96 / −34,4%** (tolerância documentada: a fonte muda de Yahoo para COTAHIST/CoinGecko)
- [ ] `engine_version` em `settings`

### 6.2 Narrativa (`alpherion/narrative/`)

- [ ] `prompts/` versionados por data · `client.py` (Claude API; modelo mais econômico que passe no guard — consultar docs ao implementar) · `schemas.py` (pydantic; extras descartados)
- [ ] `guard.py`: regex pt-BR com flexões → regenera 1x → fallback genérico por leitura, `narrative_filtered=true`; `tests/test_guard.py`
- [ ] Pseudonimização (§6.2); timeout LLM 15 s, análise 30 s; custo diário no Redis + alerta Telegram

### 6.3 `POST /v1/analyses`

- [ ] Contrato exato do §2.3; `readings` determinístico; `cost` só com movimentações com preço; `disclaimer` sempre presente

### 6.4 Web

- [ ] `app/api/analyses` (rate limit 3/dia/usuário via env; ≤ 100 posições); grava `analyses` (`input_snapshot` cifrado, tokens, custo)
- [ ] `/analise/[id]`: `ReadingCard` ×5, `CorrelationMatrix` (narrativa como alternativa textual), `DrawdownChart`, texto do Alpherion, disclaimer fixo, "o que isso não é" · `/analises` · botão **Analisar** ativo
- [ ] Carteira manual (`position_adjustments`: `quantity` **ou** `value_brl`)
- [ ] Teste de UI: nenhuma tela de análise renderiza sem o `disclaimer` do backend · evento `analysis_run`

### 6.5 Conta (`/conta`)

- [ ] E-mail, nome opcional, sessões ativas (revogar), **exportar JSON**, **excluir conta** (`delete_requested_at` → job apaga em 7 dias), consentimentos e revogação, `data_requests`
- [ ] `access_log` (ou export do nginx) com purge em 6 meses; `audit_log` completo (§4.4)
- [ ] Rate limits em subscribe, login, análise, importação, export, busca; export CSV com escape de `= + - @`

### 6.6 Testes de fechamento

- [ ] IDOR · disclaimer obrigatório · guard · parsers · fórmulas · `positions` derivadas · zero cookie no site público · lint de conteúdo (sem "melhores/recomendado/preço justo") — tudo no `ci.yml`
- [ ] Checklist OWASP Top 10 no PR de release

### 6.7 Lançamento

- [ ] Checklist pré-deploy do §10 (CI verde, migrações revisadas, `.env` na VPS, backup manual, securityheaders/SSL Labs, `etl_runs` verdes)
- [ ] Fluxo de 3 minutos (entrar → importar B3 → Analisar → ler) cronometrado
- [ ] Smoke test `/`, `/mercado`, `/agenda`, `/acoes/PETR4`, `/indices/ibovespa`, `/setores/petroleo-gas-e-biocombustiveis`, `/entrar`, `/v1/health`
- [ ] Placeholders do §13 preenchidos; `docs/ropa.md` atualizado com importação e análise

**Pronto quando:** o vídeo 3 (09/10) demonstra o portal e o fluxo completo em produção. → **tag `v1.0.0`**.

## Etapa 7 — v1.x (semanas 4–12) → `v1.1.0` … `v1.11.0`

Uma tag por entrega, nesta ordem (alternando SEO/dado e retenção/carteira). Cada item entra no `site.md` já especificado (§2, §4, §14).

1. [ ] **Screener completo** em `/acoes`, `/fiis`, `/etfs`, `/bdrs`: filtros de lista fechada (setor, liquidez, P/L, P/VP, DY, ROE, dív. líq./EBITDA, market cap; FII: segmento, P/VP, DY, patrimônio), URL com estado, `noindex` com parâmetros, `Screener` component, `GET /v1/securities` com filtros → `v1.1.0`
2. [ ] **`/carteira/calendario`** (`POST /v1/portfolios/income-calendar`: proventos anunciados × quantidade na data-com, comunicados e eventos dos ativos) + **`/favoritos`** (`WatchStar` nas páginas públicas com `localStorage`; `watchlist_items` no app; sincronização no primeiro login com aviso) → `v1.2.0`
3. [ ] **ITR trimestral + DFC** + toggle em `FinancialTable`; CAGR 5a; `GET …/indicators/history` + gráfico de indicadores (P/L, P/VP, DY históricos) → `v1.3.0`
4. [ ] **`/carteira/evolucao`** (`POST /v1/portfolios/evolution`) + **`/carteira/rentabilidade`** (`POST /v1/portfolios/performance`: TWR por cotização, por classe e ativo, × CDI/Ibovespa/IFIX/IPCA) → `v1.4.0`
5. [ ] **`/indicadores`** e `/indicadores/[slug]` (glossário completo; tooltips passam a linkar) → `v1.5.0`
6. [ ] **`/conta/alertas`** (`alerts`; job do `web` `app/api/jobs/alerts` disparado por cron com token, lendo `/v1/quotes` e `/v1/market/events`; e-mail transacional com link de desativação; limite por usuário; rate limit) → `v1.6.0`
7. [ ] **`/comparar`** + `GET /v1/compare` (ações, FIIs, ETFs, BDRs; fundos após o item 9) → `v1.7.0`
8. [ ] **Informes de FII** (vacância, imóveis) + `GET /v1/fiis/{ticker}/reports` → `v1.8.0`
9. [ ] **Fundos de investimento (CVM)**: `funds`, `fund_daily` (particionada), sources `cvm_funds.py`, jobs `cvm_funds`/`cvm_funds_daily`, `GET /v1/funds*`, `/fundos`, `/fundos/[slug]`, busca global e `/v1/assets/search` com fundos, sitemap → `v1.9.0`
10. [ ] **`/leitura`**, `/leitura/[slug]` (MDX semanal) e `/manifesto` → `v1.10.0`
11. [ ] **`analysis_feedback`** → `v1.11.0`

## Etapas seguintes (entram como módulos pelo §14 do site.md)

- **Fase 1 → `v2.0.0`**: integração oficial B3 (`b3_connections`, `/conta/integracoes`), exchanges read-only, nota de corretagem, **imposto de renda** (`/carteira/ir`, `POST /v1/portfolios/tax`, `tax_periods`, regras por classe versionadas em `tax_rules_version` — ações/isenção 20 mil, day trade, FII, ETF, BDR, cripto/isenção 35 mil —, prejuízo a compensar, DARF, relatório anual; disclaimer "não é consultoria tributária"), alertas por Telegram, 2FA, bot Telegram sobre a mesma API
- **Fase 2 → `v3.0.0`**: pagamento (Pix/cartão/boleto, checkout hospedado), `/planos`, NFS-e, CDC (§8.6), paywall (relatório com IA, IR, alertas, histórico longo, comparador, rentabilidade detalhada), **internacional** (stocks, REITs) com provedor licenciado — **ADR-019** decide o provedor; `securities.market='us'`, câmbio PTAX; `/internacional*` só existe depois do contrato
- **Fase 3**: research assinado (CNPI), segunda versão do aviso legal

---

## Riscos assumidos

| Risco                                                        | Como o plano lida                                                                                                                                       |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Prazo: Fase 0 em 1 dia e v1.0 em 19 dias, uma pessoa          | A ordem dos blocos não muda; `v0.1.0` sai primeiro de qualquer forma; `v0.2.0` e `v0.3.0` são publicáveis sozinhos (o portal já é produto antes do app) |
| Termos da B3 exigem licença para cotações e carteiras teóricas (verificado em 21/09 — ADR-017); CoinGecko Demo não é comercial | Preço e cripto atrás de feature flag até a licença; páginas publicáveis sem preço; consulta à B3 enviada; custo fixo previsto (B3 ≥ R$ 320/mês; cripto ≈ US$ 129/mês). O canal de acesso (arquivos, UP2DATA, distribuidor) troca sem mudar o schema |
| Endpoints não documentados da B3 (listagem, eventos, carteira teórica) mudam sem aviso | Fallback por fonte (CVM para cadastro; última carteira com data para índices); alerta de frescor cobre 2 dias seguidos de falha |
| Volume do IPE e (v1.x) dos informes de fundos                 | Carga incremental por data; partição por ano; `--sample` limita a 90 dias em dev                                                                        |
| Header dinâmico (faixa + busca) pode quebrar a landing estática ou o zero cookie | `MarketStrip` é server component com cache de 5 min e fallback "—"; busca carrega no foco; testes de zero cookie e de orçamento de JS no CI |
| Rankings e presets viram "recomendação implícita"            | Métrica sempre no título; padrão neutro; lint de conteúdo no CI; ADR-018 lista o que nunca entra                                                        |
| Golden test do engine: números do vídeo 02 vieram do Yahoo | Documentar tolerância em vez de forçar igualdade                                                                                                      |
| Backfill em produção leva horas e dezenas de GB            | Volume`market` provisionado na Etapa 2.6, não na 3                                                                                                   |
| IR (Fase 1): regras mudam por ano e por classe               | `tax_rules_version` gravado em cada apuração; disclaimer próprio; só com histórico completo de movimentações                                             |
| Internacional (Fase 2): custo mensal antes de receita        | Só com contrato e paywall; ADR-019 registra provedor, custo e direito de exibição                                                                       |
| Ferramental local: sem`pnpm` e `gh`                      | `corepack enable` na Etapa 1; `gh` opcional                                                                                                         |
