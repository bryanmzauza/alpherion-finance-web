# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Versionamento: [SemVer](https://semver.org/lang/pt-BR/). `web` e `api` compartilham a mesma tag.

## [Unreleased]

### Alterado
- Plano de desenvolvimento **v2.0** — paridade funcional com o Status Invest ([ADR-018](docs/adr/ADR-018-paridade-status-invest.md)): v1.0 adiado de 25/09 para **09/10/2026** e dividido em quatro tags (`v0.2.0` pipeline + páginas, `v0.3.0` portal, `v0.4.0` carteira/B3, `v1.0.0` análise). `docs/site.md` ganha o portal de mercado (header com faixa e busca global, `/mercado` Hoje/Eventos, `/agenda`, `/setores`, `/busca`), ETFs, BDRs, índices com composição e comunicados CVM (v1.0); calendário da carteira, favoritos, rentabilidade TWR, alertas e fundos de investimento (v1.x); imposto de renda (Fase 1); internacional com provedor licenciado (Fase 2, ADR-019 pendente). Fontes, tabelas, endpoints e módulos (§14) correspondentes. Roadmap sincronizado com a fonte (`alpherion-finance-yt`).

### Adicionado
- Estrutura do monorepo (`apps/`, `infra/`, `docs/`, `.github/`).
- `docs/site.md` (especificação), `docs/brand-kit.md`, `docs/roadmap.md` (cópia de referência).
- `docs/plano-de-desenvolvimento.md` v1.0 com etapas, checklists e tags por marco.
- `docs/adr/` com as 14 decisões do site.md e as ADRs 15 (monorepo) e 16 (Better Auth).
- `infra/env/.env.example`, `.gitignore`, `.editorconfig`, `README.md`.
- Etapa 1 — fundação técnica (sem feature):
  - Workspace pnpm (`pnpm-workspace.yaml`, scripts `dev`/`lint`/`typecheck`/`test`/`build` na raiz).
  - `apps/web`: Next.js 16 (App Router, TS strict, Tailwind v4 com os tokens do §5, `output: "standalone"`), fontes Playfair Display e Inter locais (`next/font/local`, OFL), route groups `(site)`/`(market)`/`(app)`/`(auth)`/`api`, `lib/env.ts` (zod, validado no boot via `instrumentation.ts`), `lib/db` (Drizzle, schema `app`), `lib/api-client.ts` (token de serviço), `lib/validation`, `/design` só em dev, testes com Vitest.
  - `apps/api`: FastAPI com `settings.py` (pydantic-settings), auth por token de serviço com escopos (`auth.py`), `GET /v1/health` (público, sem versão, checa Postgres e Redis), SQLAlchemy 2 + Alembic no schema `market` (revisão base vazia), subpacotes do §3.3, testes (pytest), ruff e mypy strict.
  - `infra/compose.dev.yml` (Postgres 16 com usuários `web`/`api`/`data` e GRANTs do §7.6 via `infra/postgres/init.{sh,sql}`, Redis 7 com senha, Mailpit), Dockerfiles non-root para web (`node:22-slim`, standalone) e api (`python:3.12-slim`, mesma imagem para `api` e `data`).
  - `.github/workflows/ci.yml` (web: lint/typecheck/test/build · api: ruff/mypy/pytest · `pnpm audit`/`pip-audit`) e Dependabot semanal.
- Etapa 2.1–2.2 — componentes base e páginas da Fase 0:
  - `components/ui/` (`Button`, `Input`, `Checkbox`, `Card`, `Badge`, `Table`, `Tooltip`, `Disclaimer`, `EmailCapture`, `VideoEmbed`, `Gold`) e `components/site/` (`Header`, `Footer`, `Section`, `Faq`, `ReadingCard`, `ReadingPreview`, `VideoCard`/`QuadroCard`, `LegalPage`, `SkipLink`); galeria em `/design` (dev).
  - Páginas `/`, `/raio-x`, `/sobre`, `/contato`, `/videos`, `/privacidade`, `/termos`, `/aviso-legal` e 404. Conteúdo e placeholders (§13) centralizados em `content/site.ts`; vídeos em `content/videos.json` (cards dos quadros até haver `youtubeId`).
  - Textos legais em MDX (`content/legal/*.mdx`, `version` 1.0) — **rascunhos para revisão jurídica**. Imagens da marca em `public/brand/`, ícones gerados do monograma.
- Etapa 2.3 — lista de e-mail:
  - Primeira migration Drizzle do schema `app` (`consents`, `data_requests`; tabela de controle em `app.__drizzle_migrations`).
  - `POST /api/subscribe` (zod, honeypot, verificação de Origin, rate limit 10/min/IP no Redis) → Listmonk (assinante não confirmado + e-mail de confirmação pela API transacional) → prova em `consents` (hash do e-mail, versão da política, IP, user-agent, `source=landing`).
  - `/lista/obrigado`, `/lista/confirmar?t=`, `/lista/sair?t=` (descadastro em 1 clique). Eventos Umami `subscribe_submit`/`subscribe_confirm`; `Analytics` só quando `UMAMI_*` configurado.
  - Listmonk e Umami (perfil `analytics`) no `compose.dev.yml` com bancos próprios; `infra/scripts/listmonk-setup.py` (lista, usuário de API, templates, settings); `docs/runbooks/listmonk.md`.
