# ADR-015 — Monorepo único para web, api, infra e docs

- Data: 19/09/2026
- Status: aceita

## Contexto

O site.md §3.3 descreve a árvore `apps/web`, `apps/api`, `infra/`, `docs/` e o §10 exige que `web` e `api` sejam publicados **sempre com a mesma tag**. O repositório `alpherion-finance-web` nasceu vazio e precisava de uma decisão sobre o que ele contém.

## Decisão

Este repositório é o monorepo completo. Contém o Next.js (site público + app), a API FastAPI com o worker `data`, a infraestrutura (compose, nginx, scripts) e a documentação (spec, ADRs, runbooks, ROPA).

## Alternativa descartada

Um repositório por serviço (`web`, `api`, `infra`). Descartado porque a versão de `web` e `api` é uma só por definição, a especificação é uma só, e uma pessoa mantendo três repositórios multiplica PRs, CI e chance de divergência entre spec e código.

## Consequências

- Uma tag `vX.Y.Z` gera as duas imagens (`web`, `api`) e dispara um único deploy.
- `pnpm` workspace para o lado Node; `pyproject.toml` em `apps/api` para o lado Python. CI roda os dois.
- O nome do repositório (`-web`) ficou mais estreito do que o conteúdo; renomear é opcional e não muda nada aqui.
