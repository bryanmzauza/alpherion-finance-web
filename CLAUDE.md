# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Estado atual

Monorepo do Alpherion Finance (site `alpherion.com.br`, app `app.alpherion.com.br`, API `api.alpherion.com.br`). **Ainda não há feature de produto** — Etapa 0 (estrutura + docs) e Etapa 1 (fundação técnica: workspace, `apps/web`, `apps/api`, compose dev, CI) estão feitas. Antes de criar qualquer coisa, leia nesta ordem:

1. `docs/plano-de-desenvolvimento.md` — a ordem de execução é fixa; trabalhe na etapa aberta, marque os checkboxes no commit da entrega.
2. `docs/site.md` — especificação completa (rotas §2, arquitetura §3, modelo de dados §4, design §5, IA §6, segurança §7, conformidade §8). Referencie seções por `§`.
3. `docs/adr/README.md` — decisões já tomadas; não reabra sem um ADR novo.

Se o `site.md` e o `docs/roadmap.md` conflitarem, o roadmap manda (exceto onde ele remete ao site.md por nota datada). O roadmap aqui é cópia; a fonte é `../alpherion-finance-yt/docs/roadmap.md`.

Idioma do repositório: **pt-BR** em docs, commits, UI e narrativa. Código (identificadores) em inglês.

## Comandos

Um único `.env` na **raiz** (`cp infra/env/.env.example .env`); web, api e compose leem dele. Rodar da raiz do repo.

```
docker compose --env-file .env -f infra/compose.dev.yml up -d   # postgres 16 (schemas app/market), redis, mailpit
pnpm install && pnpm dev                                 # apps/web (Next.js 16, App Router) em :3000; /design só em dev
pnpm lint && pnpm typecheck && pnpm test && pnpm build   # raiz do workspace (typecheck roda `next typegen` antes do tsc)
cd apps/api && uv sync                                   # cria .venv com Python 3.12
cd apps/api && uv run uvicorn alpherion.main:app --reload --port 8001   # API; --reload é obrigatório no Windows (ver abaixo)
cd apps/api && uv run alembic upgrade head               # migra o schema market (usuário `data`, DATA_DATABASE_URL)
cd apps/api && uv run pytest tests/test_engine_golden.py -k concentration   # um teste
cd apps/api && uv run ruff check . && uv run ruff format --check . && uv run mypy .
cd apps/api && uv run python -m alpherion.data.jobs.<job>   # rodar um job do worker à mão (Etapa 3)
infra/scripts/backfill-market.sh --sample                # subconjunto do schema market para dev (Etapa 3)
docker build -f apps/web/Dockerfile .  ·  docker build apps/api   # imagens (web usa a raiz como contexto)
```

Particularidades da máquina do Bryan (Windows): outro projeto ocupa as portas 5432 e 8000, por isso o `.env` local usa Postgres em `5433` e a API em `8001`; usar `127.0.0.1` (não `localhost`) nas URLs do `.env`, porque o Docker só publica em IPv4; o psycopg assíncrono não roda no `ProactorEventLoop`, e o uvicorn só usa o `SelectorEventLoop` com `--reload`. `pnpm` foi instalado com `npm i -g pnpm` (o `corepack enable` exige shell de administrador); `uv` via winget.

## Arquitetura (o que não dá para ver olhando um arquivo só)

Três processos, dois schemas, uma fronteira de privacidade:

- **`apps/web` (Next.js)** é dono do schema Postgres **`app`** (usuários, sessões, consentimentos, carteiras, movimentações, análises) via Drizzle. Serve o site público (SSG/ISR), as páginas de mercado (ISR) e o app autenticado (route groups `(site)`, `(market)`, `(app)`, `(auth)`).
- **`apps/api` (FastAPI)** é dona do schema **`market`** (cotações, demonstrações, indicadores, Tesouro, cripto) via SQLAlchemy/Alembic, do engine de risco (pandas) e da única chamada à Claude API. **Não conhece usuários**: recebe posições, devolve leituras. Auth por token de serviço com escopos, um por cliente.
- **`data` (worker)** é a mesma imagem da API rodando jobs agendados idempotentes (`alpherion/data/jobs/`) sobre fontes oficiais (CVM, B3 COTAHIST, Tesouro Transparente, BCB SGS, CoinGecko). Só escreve em `market`; não enxerga `app`.

Regras estruturais que decorrem disso:

- `web` **nunca** lê o schema `market` no banco — sempre pela API (`lib/api-client.ts`). Lógica nova de cálculo ou de dado entra na API, nunca no `web` ("uma API só": o bot do Telegram vai consumir a mesma API).
- O LLM só recebe `readings` (números agregados, pseudonimizados). Nunca calcula nada, nunca recebe e-mail/nome/`user_id`/quantidades/preços médios (§6.2). A narrativa passa por `guard.py`; falha de LLM nunca derruba a análise (fallback genérico, `narrative_filtered=true`).
- `POST /v1/analyses` tem contrato fixo em §2.3; `readings` é determinístico; `disclaimer` sempre presente e o front não pode omitir (há teste de UI para isso).
- Posições são **derivadas** de `transactions` + `position_adjustments` em memória no serviço (`lib/positions.ts`), não no banco — porque as colunas financeiras são cifradas na aplicação (AES-256-GCM, `key_version`).
- Arquivos importados (CSV, Área do Investidor da B3) são parseados na API em memória e **descartados**; só o `sha256` fica em `import_batches`. O parser da B3 descarta CPF/nome antes de qualquer log.
- Todo acesso a `portfolios`/`transactions`/`analyses`/`import_batches` filtra por `user_id` da sessão; há teste IDOR.

O engine (`alpherion/engine/`) é um porte de `../alpherion-finance-yt/ferramentas/raio-x-carteira.py`; o golden test é a carteira do vídeo 02 (38% / 0,91 / 0,96 / −34,4%, com tolerância documentada). `ferramentas/mercado.py` (Yahoo) **não** vai para o produto (ADR 5).

## Regras de produto que afetam qualquer código

- **Diagnóstico ≠ recomendação.** Nenhuma tela, texto, e-mail ou saída de IA indica compra/venda. Sem "melhores ações", nota, score, ranking editorial, preço-alvo, "barata/cara". Screener ordena pelo critério do usuário; padrão neutro (liquidez).
- **Todo número de mercado tem `SourceBadge`** (fonte, documento/período, data). Valor ausente mostra "—" com o motivo no tooltip, nunca zero.
- Sem "em construção", countdown, "beta em breve" ou botão de recurso que não existe (o "Conectar B3" oficial só aparece com contrato).
- Sem promessa de retorno. Termo técnico definido na primeira vez (tooltip → `/indicadores`).
- Site público: **zero cookie** (Umami cookieless, fontes locais, YouTube via `youtube-nocookie` carregado no clique). App: só o cookie de sessão. Sem banner.
- Design: tema escuro único; tokens em §5 (`--navy #0B192C`, `--gold #C5A059`, `--ice #F8F9FA`); Playfair Display para H1–H2, Inter para o resto; **no máximo uma palavra dourada por título**; números tabulares em tabelas.
- Placeholders legais (`[RAZÃO SOCIAL]`, `[CNPJ]`, `[ENDEREÇO]`) ficam num único lugar (`content/site.ts`); textos legais em MDX com `version` no frontmatter, e o app grava essa versão no aceite.

## Versionamento e fluxo

- **Nunca faça `git commit`, `git tag` ou `git push` sem o usuário pedir explicitamente** — mesmo que o plano ou a etapa preveja um commit. Deixe as mudanças no working tree, mostre o `git status` e sugira a mensagem de commit; o usuário decide quando versionar.
- SemVer, **uma tag para `web` e `api`**; deploy só por tag (`v*`). Marcos: `v0.1.0` Fase 0 · `v0.2.0` dados · `v0.3.0` carteira/B3 · `v1.0.0` app aberto.
- Conventional Commits em pt-BR (`feat(web):`, `feat(api):`, `data:`, `infra:`, `docs(plano):`). Branch curta por item; depois da `v0.1.0`, nada direto na `main`.
- `CHANGELOG.md` (`[Unreleased]`) e o checkbox correspondente no plano são atualizados no mesmo commit da entrega. Mudança de escopo/ordem = nova versão do plano.
- Migrations sempre aditivas na tag; destrutivas em tag separada. Cada serviço migra só o seu schema.
- Segredos só em `.env` (ignorado); `infra/env/.env.example` lista todas as variáveis sem valor — adicione lá qualquer variável nova.
