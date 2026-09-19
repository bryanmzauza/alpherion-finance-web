# Alpherion Finance — site, app e API

Monorepo do `alpherion.com.br`: site público (landing, conteúdo, páginas de ativos), app (`app.alpherion.com.br`: carteira, importação B3, análise de risco) e a API única (`api.alpherion.com.br`: dados de mercado, engine de risco, narrativa por IA).

**Comece por aqui:**

1. [docs/plano-de-desenvolvimento.md](docs/plano-de-desenvolvimento.md) — o que fazer, em que ordem, e qual tag fecha cada marco.
2. [docs/site.md](docs/site.md) — a especificação completa (rotas, API, modelo de dados, segurança, conformidade).
3. [docs/roadmap.md](docs/roadmap.md) — estratégia e fases (fonte canônica no repo do canal).
4. [docs/adr/](docs/adr/README.md) — decisões de arquitetura.

## Mapa do repositório

```
apps/web/      Next.js 15 — site público + app (schema `app` via Drizzle)
apps/api/      FastAPI + worker `data` — API do Alpherion (schema `market` via SQLAlchemy/Alembic)
infra/         compose (prod/dev), nginx, scripts de VPS/deploy/backup, .env.example
docs/          spec, plano, ADRs, runbooks, ROPA, DPAs, fontes de dados
.github/       CI (lint, test, build) e deploy por tag
```

Regras que valem para todo código deste repo (detalhe no site.md):

- **Diagnóstico ≠ recomendação.** Nenhuma tela, texto ou saída de IA indica compra/venda. Disclaimer em toda página de carteira ou mercado.
- **Todo número de mercado tem fonte e data** (`SourceBadge`). Sem nota, score ou ranking editorial.
- **O `web` nunca lê o schema `market` direto** — passa pela API. A API nunca vê e-mail, nome ou `user_id`.
- **Arquivos importados não são armazenados.** CPF e nome dos arquivos da B3 são descartados no parser.

## Versionamento

SemVer, uma tag para `web` e `api`. Marcos: `v0.1.0` Fase 0 no ar · `v0.2.0` dados de mercado · `v0.3.0` carteira/B3 · `v1.0.0` app aberto. Conventional Commits em pt-BR. Deploy só por tag. Detalhe em [docs/plano-de-desenvolvimento.md](docs/plano-de-desenvolvimento.md#convenções-de-versionamento).

## Rodando localmente

Ainda não há código de produto (Etapa 0). A Etapa 1 do plano cria `pnpm-workspace.yaml`, `apps/web`, `apps/api` e `infra/compose.dev.yml`; quando existir, o fluxo será:

```
cp infra/env/.env.example .env            # preencher
docker compose -f infra/compose.dev.yml up -d
pnpm install && pnpm dev                  # web
cd apps/api && uv run uvicorn alpherion.main:app --reload   # api
```

Pré-requisitos: Node 22 (20 funciona), pnpm (`corepack enable`), Python 3.12+, Docker.
