# Plano de desenvolvimento — Alpherion Finance

> Versão do plano: **1.0** · Data: 19/09/2026 · Responsável: Bryan
> Especificação de referência: [site.md](site.md) · Estratégia: [roadmap.md](roadmap.md) · Decisões: [adr/](adr/README.md)
> Regra: a **ordem** das etapas é fixa (§11 do site.md). As datas são metas; se escorregarem, a ordem não muda.

## Histórico do plano

| Versão | Data | Mudança |
| --- | --- | --- |
| 1.0 | 19/09/2026 | Plano inicial a partir do site.md. Decisões: monorepo, SemVer com tags por marco, Better Auth. Auth antecipada para o início do Bloco 2 (a carteira exige sessão) |

## Como este plano é mantido

- Cada etapa tem entregas em checklist, critério de **pronto** e a **tag** que fecha o marco.
- Marcar os checkboxes aqui mesmo, no commit da entrega.
- Mudança de escopo ou de ordem → incrementa a versão do plano, entra no histórico acima, commit `docs(plano): …`.
- Funcionalidade nova entra primeiro no `site.md` como módulo (§14) e só depois vira etapa aqui.

## Convenções de versionamento

| Item | Regra |
| --- | --- |
| Versão | SemVer. `web` e `api` sempre com a **mesma tag** (site.md §10). `engine_version` e `prompt_version` são versionados à parte dentro da API e gravados em cada análise |
| Tags por marco | `v0.0.1` bootstrap · `v0.1.0` Fase 0 no ar · `v0.2.0` Bloco 1 (dados) · `v0.3.0` Bloco 2 (carteira/B3) · `v1.0.0` app aberto · `v1.1.0+` entregas do v1.x · `v2.0.0` Fase 1 (B3 oficial) · `v3.0.0` Fase 2 (pagamento) |
| Branches | `main` sempre deployável. Uma branch curta por item (`feat/landing-hero`, `feat/api-cotahist`). Squash na `main`. Depois da `v0.1.0`, nunca commitar direto na `main` |
| Commits | Conventional Commits em pt-BR: `feat:`, `fix:`, `docs:`, `chore:`, `infra:`, `data:`, `test:`. Escopo opcional: `feat(web):`, `feat(api):` |
| CHANGELOG | [CHANGELOG.md](../CHANGELOG.md) no formato Keep a Changelog; `[Unreleased]` acumula entre tags e vira a seção da tag no fechamento |
| Deploy | Só por tag (`deploy.yml` dispara em `v*`). Migrations aditivas na tag; destrutivas em tag separada, após deploy |

---

## Etapa 0 — Bootstrap do repositório → `v0.0.1`

- [x] Estrutura de pastas do monorepo (site.md §3.3)
- [x] `site.md`, `brand-kit.md`, `roadmap.md` em `docs/`
- [x] Este plano, ADRs, README, CHANGELOG, `.gitignore`, `.editorconfig`, `infra/env/.env.example`
- [ ] Commit inicial na `main` + tag `v0.0.1`

**Pronto quando:** árvore criada, docs no lugar, tag existe.

## Etapa 1 — Fundação técnica (sem feature)

Objetivo: `pnpm dev` e `uvicorn --reload` sobem localmente com banco, e o CI roda verde.

- [ ] `corepack enable` → `pnpm-workspace.yaml` (`apps/*`), `package.json` raiz com `dev`, `lint`, `typecheck`, `test`, `build`
- [ ] `apps/web`: Next.js 15 App Router, TS strict, Tailwind, ESLint. Pastas `app/`, `components/`, `lib/`, `content/`, `drizzle/`, `public/`. Route groups `(site)`, `(market)`, `(app)`, `(auth)`, `api/`. Fontes Playfair Display + Inter via `next/font/local` (arquivos no repo). `next.config.ts` com `output: "standalone"`
- [ ] `apps/web/lib`: `db` (Drizzle, schema `app`), `validation` (zod), `env.ts` (env validado no boot), `api-client.ts` (token de serviço)
- [ ] `apps/api`: `pyproject.toml` (FastAPI, pydantic v2, SQLAlchemy 2, Alembic para schema `market`, pandas/numpy, httpx, redis, arq, pytest, ruff, mypy). Pacote `alpherion/` com subpacotes do §3.3, `settings.py`, `routers/health.py` (`GET /v1/health`, sem versão)
- [ ] Auth por token de serviço na API (`Authorization: Bearer`, escopos `analyses:write`, `imports:write`, `market:read`, `quotes:read`)
- [ ] `infra/compose.dev.yml`: postgres 16 (usuários `web`→`app`, `api`/`data`→`market`, `init.sql` com GRANTs do §7.6), redis 7 com senha, mailpit
- [ ] Dockerfiles: web (`node:22-slim`, non-root, standalone) e api (`python:3.12-slim`, non-root; mesma imagem roda `api` ou `data`)
- [ ] `.github/workflows/ci.yml`: web (lint, typecheck, test, build) + api (ruff, mypy, pytest) + `pnpm audit`/`pip-audit`. Dependabot semanal
- [ ] `apps/web/app/design` (só em dev): tokens do §5, tipografia, `color-scheme: dark`

**Pronto quando:** compose dev sobe; `pnpm dev` e `uvicorn` sobem; `/v1/health` responde; CI verde. Sem tag (fecha junto com a `v0.1.0`).

## Etapa 2 — Fase 0: landing, legais, lista, infra de produção → `v0.1.0`

Meta: no ar antes do vídeo 1 (21/09). SSG/ISR, zero cookie no site público.

### 2.1 Componentes base (`components/ui/`)
- [ ] `Button`, `Input`, `Checkbox`, `Card`, `Badge`, `Table`, `Tooltip`, `Disclaimer`, `EmailCapture`, `VideoEmbed` (youtube-nocookie, carrega no clique), `Gold` (regra da palavra dourada)
- [ ] Foco visível, `aria-*`, contraste AA (dourado só em texto grande)

### 2.2 Páginas (`app/(site)/`)
- [ ] `/` com as 10 seções do §5, na ordem
- [ ] `/raio-x` (cinco leituras com os números do vídeo 02: 38% · 0,91 · 0,96 · −34% · 0,03%)
- [ ] `/sobre`, `/contato`, `/videos` (ISR sobre `content/videos.json`)
- [ ] `/privacidade`, `/termos`, `/aviso-legal` em MDX (`content/legal/`) com `version` e `date` no frontmatter
- [ ] `not-found.tsx`; placeholders do §13 centralizados em `content/site.ts`
- [ ] Imagens da marca em `public/brand/` (copiar de `alpherion-finance-yt/brand/imagens/`)

### 2.3 Lista de e-mail
- [ ] Listmonk no compose (banco próprio), double opt-in, `List-Unsubscribe` one-click
- [ ] `POST /api/subscribe`: zod, rate limit Redis 10/min/IP, honeypot, chama Listmonk, grava `consents` (`document_version`, ip, user_agent, `source="landing"`)
- [ ] Tabelas `consents` e `data_requests` — primeira migration Drizzle do schema `app`
- [ ] `/lista/obrigado`, `/lista/confirmar?t=`, `/lista/sair?t=` (SSR; sem login, sem "tem certeza?")
- [ ] Eventos Umami `subscribe_submit`, `subscribe_confirm`

### 2.4 SEO, performance, acessibilidade
- [ ] `metadata` por página, `lang="pt-BR"`, OG via `next/og` (navy + palavra dourada), JSON-LD `Organization` e `VideoObject`
- [ ] `sitemap.ts`, `robots.ts`, `manifest.webmanifest`
- [ ] CSP com nonce (middleware) + headers do §7.3
- [ ] Lighthouse ≥ 95 no CI (`@lhci/cli`) em `/` e `/raio-x`; JS inicial < 90 kB gzip

### 2.5 Documentos obrigatórios (`docs/`)
- [ ] `ropa.md` v1 · `runbooks/incidente.md` · `runbooks/restore.md` · `runbooks/rotacao-de-chave.md`
- [ ] `fontes-de-dados.md`: termos de CVM, Tesouro, BCB, CoinGecko **e verificação da B3** (§8.10) → decide COTAHIST vs provedor licenciado → **ADR-017**

### 2.6 Infra de produção (`infra/`)
- [ ] `compose.yml` (nginx, web, api, data, postgres, redis, umami, listmonk, uptime-kuma; redes `edge`/`internal`; só nginx publica 80/443; volume separado para `market`)
- [ ] `nginx/sites/*.conf`, `snippets/security-headers.conf`, `cloudflare-real-ip.conf`, `cache-market.conf`
- [ ] `scripts/bootstrap-vps.sh`, `update-cloudflare-ips.sh`, `deploy.sh`, `backup.sh` (pg_dump → age → S3), `restore-test.sh`
- [ ] `.github/workflows/deploy.yml` (tag `v*` → build → GHCR → ssh → `compose pull && up -d` → migrações → smoke test)
- [ ] Manual: Registro.br + DNSSEC · Cloudflare (proxy, TLS Full strict, Authenticated Origin Pulls, WAF, rate limit) · SPF/DKIM/DMARC (apex e `news.`) · provedor SMTP escolhido · Umami · Uptime Kuma em `/` · backup rodando + **um restore testado**

**Pronto quando:** `alpherion.com.br` no ar com as páginas da Fase 0; um e-mail real confirmado por double opt-in; securityheaders A+; SSL Labs A+; Lighthouse ≥ 95; `fontes-de-dados.md` com a B3 verificada. → **tag `v0.1.0`**.

## Etapa 3 — v1.0 Bloco 1: pipeline de dados + páginas de ativos → `v0.2.0`

Por que primeiro: é o que o vídeo mostra e o que traz tráfego orgânico. Tudo na API; o `web` nunca lê `market` direto.

### 3.1 Schema `market` (SQLAlchemy + Alembic)
- [ ] Tabelas do §4.3: `securities`, `daily_quotes` (particionada por ano), `corporate_actions`, `financial_statements`, `company_facts`, `indicators_daily`, `fii_reports`, `treasury_bonds`, `treasury_daily`, `macro_series`, `crypto_assets/daily/metrics`, `etl_runs`, `data_sources`
- [ ] Índices em todo campo filtrável; `statement_timeout 5s` no usuário `api`

### 3.2 Sources + transform (cada um com teste sobre fixture pequena)
- [ ] `b3_cotahist.py` + `cotahist_parser.py` (layout posicional) — ou fonte licenciada, conforme ADR-017
- [ ] `b3_events.py` (listagem + eventos; fallback CVM/FRE documentado)
- [ ] `cvm.py` (cadastro, DFP, FRE/FCA, informes de FII) + `cvm_statements.py` (formato longo; versão mais recente por período)
- [ ] `tesouro.py`, `bcb.py` (códigos SGS documentados), `coingecko.py` (chave Demo, atribuição)
- [ ] `adjust.py` (fator acumulado) e `indicators.py` (fórmulas; `null` com motivo quando falta entrada; testes contra casos à mão)
- [ ] Proteções §7.5: limite de download, zip bomb, lista fechada de hosts

### 3.3 Jobs (idempotentes, lock no Redis, registram `etl_runs`)
- [ ] `cotahist_daily`, `b3_listing`, `b3_corporate_actions`, `cvm_companies`, `cvm_statements` (DFP anual), `cvm_fii_reports`, `tesouro_daily`, `bcb_series`, `coingecko_prices`, `coingecko_history`, `adjust_factors`, `indicators_rebuild`, `revalidate_pages`
- [ ] Agendamento por cron do host (preferido) ou `scheduler.py`
- [ ] `infra/scripts/backfill-market.sh` com `--sample` (20 ações, 10 FIIs, Tesouro, top 20 cripto, 3 anos) para dev
- [ ] `docs/runbooks/reprocessar-job.md`

### 3.4 Endpoints de mercado
- [ ] `GET /v1/market/overview` · `/v1/securities` (lista + busca; filtros de lista fechada; paginação ≤ 100) · `/v1/securities/{ticker}` · `/history` · `/dividends` · `/financials?period=annual`
- [ ] `/v1/treasury*` · `/v1/crypto*` (+ `/correlations`) · `/v1/quotes` · `/v1/assets/search`
- [ ] `POST /v1/market/weekly-reading` (porta de `ferramentas/leitura-semanal.py`)
- [ ] Cache Redis (cotação 5 min); todo bloco de resposta com `source`, `document`, `updated_at`

### 3.5 Páginas de mercado (`app/(market)/`, ISR, container 1280)
- [ ] `components/market/`: `PriceHeader`, `HistoryChart` (leve, client-only, lazy, tabela como fallback), `IndicatorGrid` (tooltip a partir de `content/indicadores/*.mdx`), `FinancialTable`, `DividendTable` + `DividendChart`, `EventList`, `TreasuryTable`, `CryptoTable`, `SourceBadge`, `AssetCTA`, busca de ticker
- [ ] Rotas: `/mercado`, `/acoes`, `/acoes/[ticker]`, `/fiis`, `/fiis/[ticker]`, `/tesouro`, `/tesouro/[slug]`, `/cripto`, `/cripto/[id]`
- [ ] Redirects: ticker minúsculo → maiúsculo (301); inexistente → 404 com busca; `www.` → apex
- [ ] `app/api/revalidate` (token) chamado pelo job `revalidate_pages`
- [ ] Sitemaps segmentados com `lastmod`; título/description por template; JSON-LD `Corporation` + `BreadcrumbList`; OG com ticker dourado + cotação; `Cache-Control: public, s-maxage=3600, stale-while-revalidate=86400`
- [ ] Seção "Dados de mercado" da landing linkando de verdade

### 3.6 Operação
- [ ] Alerta de frescor (endpoint interno lendo `etl_runs` do dia; alerta se `cotahist_daily` não rodou até 21h) → Telegram
- [ ] `backfill-market.sh` completo rodado em produção **antes** da tag

**Pronto quando:** `/acoes/PETR4`, `/fiis/MXRF11`, `/tesouro/…`, `/cripto/bitcoin` no ar com dados reais; todo número com `SourceBadge`; testes de parser/fórmulas verdes; jobs no cron; sitemap no Search Console. → **tag `v0.2.0`**.

## Etapa 4 — v1.0 Bloco 2: auth, carteira, movimentações, importação B3 → `v0.3.0`

### 4.0 Auth (antecipada: a carteira exige sessão)
- [ ] Better Auth + adapter Drizzle (`users`, `sessions`, `accounts`, `verification_tokens`); magic link (uso único, 15 min, hash) via SMTP + Google OAuth (PKCE); cookie `HttpOnly Secure SameSite=Lax`, 30 dias sliding
- [ ] `/entrar` com checkbox Termos+Privacidade **não pré-marcado** gravando `consents` com a versão do MDX · `/entrar/verificar`
- [ ] Middleware em `(app)/`; `/` do app redireciona conforme existência de carteira; redirects `/entrar`, `/cadastro`, `/carteira` do domínio público → app
- [ ] `audit_log` append-only (GRANT sem UPDATE/DELETE) com `login`/`logout`

### 4.1 Schema `app` carteira (Drizzle, migration aditiva)
- [ ] `portfolios`, `transactions`, `income_events`, `position_adjustments`, `import_batches`, `assets` (com `factor_map` vindo do `FATORES` de `raio-x-carteira.py` + setor B3 por padrão)
- [ ] `lib/crypto.ts` AES-256-GCM com `key_version` para as colunas cifradas do §7.4
- [ ] `lib/positions.ts`: derivação em memória (PM pelo método da Receita + ajustes)

### 4.2 Importadores na API
- [ ] `importers/b3/posicao.py`, `negociacao.py`, `proventos.py`, `importers/csv.py`: openpyxl `read_only`, sem macros, limites de linhas/células/tamanho descomprimido, checagem de conteúdo, **descarte de CPF/nome antes de qualquer log**, `external_key` = hash (ativo, data, tipo, qtd, preço)
- [ ] Fixtures anonimizadas em `tests/fixtures/b3/`
- [ ] `POST /v1/imports/b3/preview`, `POST /v1/imports/csv/preview`, `POST /v1/portfolios/valuation`

### 4.3 Telas (`app/(app)/carteira/`)
- [ ] `/carteira/nova` (2 passos) · `/carteira/importar` (CSV; `public/csv-modelo.csv`) · `/carteira/importar/b3` (passo a passo com prints; aviso de descarte de CPF/nome **antes** do upload; 1–3 arquivos ≤ 5 MB; prévia; avisos por linha; dedupe por hash de arquivo e `external_key`)
- [ ] `/carteira` (PM, atual, resultado, peso; **Analisar** desabilitado até a Etapa 5) · `/carteira/movimentacoes` · `/carteira/proventos` (yield on cost como fato)
- [ ] Route handlers `app/api/portfolio/*`, `app/api/imports/*` filtrando **sempre** por `user_id` da sessão
- [ ] Evento Umami `b3_import`

**Pronto quando:** usuário real entra por magic link, importa os 3 arquivos da Área do Investidor, vê posições com PM correto (fixture conhecida); reenvio não duplica; teste IDOR passa. → **tag `v0.3.0`**.

## Etapa 5 — v1.0 Bloco 3: engine, análise por IA, conta, segurança, lançamento → `v1.0.0`

### 5.1 Engine (`alpherion/engine/`)
- [ ] Portar `ferramentas/raio-x-carteira.py` em `concentration.py`, `correlation.py`, `exposure.py`, `drawdown.py`, `liquidity.py`, `cost.py`, lendo `market.daily_quotes` (ajustado), `macro_series` (Selic real), `crypto_daily`
- [ ] `tests/test_engine_golden.py` com a carteira do vídeo 02 → **38% / 0,91 / 0,96 / −34,4%** (tolerância documentada: a fonte muda de Yahoo para COTAHIST/CoinGecko)
- [ ] `engine_version` em `settings`

### 5.2 Narrativa (`alpherion/narrative/`)
- [ ] `prompts/` versionados por data · `client.py` (Claude API; modelo mais econômico que passe no guard — consultar docs ao implementar) · `schemas.py` (pydantic; extras descartados)
- [ ] `guard.py`: regex pt-BR com flexões → regenera 1x → fallback genérico por leitura, `narrative_filtered=true`; `tests/test_guard.py`
- [ ] Pseudonimização (§6.2); timeout LLM 15 s, análise 30 s; custo diário no Redis + alerta Telegram

### 5.3 `POST /v1/analyses`
- [ ] Contrato exato do §2.3; `readings` determinístico; `cost` só com movimentações com preço; `disclaimer` sempre presente

### 5.4 Web
- [ ] `app/api/analyses` (rate limit 3/dia/usuário via env; ≤ 100 posições); grava `analyses` (`input_snapshot` cifrado, tokens, custo)
- [ ] `/analise/[id]`: `ReadingCard` ×5, `CorrelationMatrix` (narrativa como alternativa textual), `DrawdownChart`, texto do Alpherion, disclaimer fixo, "o que isso não é" · `/analises` · botão **Analisar** ativo
- [ ] Carteira manual (`position_adjustments`: `quantity` **ou** `value_brl`)
- [ ] Teste de UI: nenhuma tela de análise renderiza sem o `disclaimer` do backend · evento `analysis_run`

### 5.5 Conta (`/conta`)
- [ ] E-mail, nome opcional, sessões ativas (revogar), **exportar JSON**, **excluir conta** (`delete_requested_at` → job apaga em 7 dias), consentimentos e revogação, `data_requests`
- [ ] `access_log` (ou export do nginx) com purge em 6 meses; `audit_log` completo (§4.4)
- [ ] Rate limits em subscribe, login, análise, importação, export; export CSV com escape de `= + - @`

### 5.6 Testes de fechamento
- [ ] IDOR · disclaimer obrigatório · guard · parsers · fórmulas · `positions` derivadas — tudo no `ci.yml`
- [ ] Checklist OWASP Top 10 no PR de release

### 5.7 Lançamento
- [ ] Checklist pré-deploy do §10 (CI verde, migrações revisadas, `.env` na VPS, backup manual, securityheaders/SSL Labs, `etl_runs` verdes)
- [ ] Fluxo de 3 minutos (entrar → importar B3 → Analisar → ler) cronometrado
- [ ] Smoke test `/`, `/entrar`, `/acoes/PETR4`, `/v1/health`
- [ ] Placeholders do §13 preenchidos; `docs/ropa.md` atualizado com importação e análise

**Pronto quando:** o vídeo 3 (25/09) demonstra o fluxo completo em produção. → **tag `v1.0.0`**.

## Etapa 6 — v1.x (semanas 3–8) → `v1.1.0` … `v1.8.0`

Uma tag por entrega, nesta ordem:

1. [ ] `/acoes` e `/fiis` com screener completo (filtros, URL com estado, `noindex` com parâmetros) → `v1.1.0`
2. [ ] ITR trimestral + DFC + toggle em `FinancialTable`; CAGR 5a; `GET …/indicators/history` → `v1.2.0`
3. [ ] `/indicadores` e `/indicadores/[slug]` (glossário completo; tooltips passam a linkar) → `v1.3.0`
4. [ ] `/comparar` + `GET /v1/compare` → `v1.4.0`
5. [ ] Informes de FII (vacância, imóveis) + `GET /v1/fiis/{ticker}/reports` → `v1.5.0`
6. [ ] `/carteira/evolucao` + `POST /v1/portfolios/evolution` → `v1.6.0`
7. [ ] `/leitura`, `/leitura/[slug]` (MDX semanal) e `/manifesto` → `v1.7.0`
8. [ ] `analysis_feedback` → `v1.8.0`

## Etapas seguintes (entram como módulos pelo §14 do site.md)

- **Fase 1 → `v2.0.0`**: integração oficial B3 (`b3_connections`, `/conta/integracoes`), exchanges read-only, nota de corretagem, 2FA, bot Telegram sobre a mesma API
- **Fase 2 → `v3.0.0`**: pagamento (Pix/cartão/boleto, checkout hospedado), `/planos`, NFS-e, CDC (§8.6), paywall
- **Fase 3**: research assinado (CNPI), segunda versão do aviso legal

---

## Riscos assumidos

| Risco | Como o plano lida |
| --- | --- |
| Prazo: Fase 0 em 2 dias e v1.0 em 6 dias, uma pessoa | A ordem dos blocos não muda; `v0.1.0` sai primeiro de qualquer forma |
| Termos da B3 (§8.10) podem exigir licença para cotações | Decisão na Etapa 2.5 (ADR-017), **antes** de codar o parser; se preciso, `cotahist_daily` vira job sobre provedor licenciado sem mudar o schema |
| Golden test do engine: números do vídeo 02 vieram do Yahoo | Documentar tolerância em vez de forçar igualdade |
| Backfill em produção leva horas e dezenas de GB | Volume `market` provisionado na Etapa 2.6, não na 3 |
| Ferramental local: sem `pnpm` e `gh` | `corepack enable` na Etapa 1; `gh` opcional |
