# Runbook — reprocessar um job do pipeline

> site.md §3.5 e §8.10 · Plano §3.3. Os jobs vivem em `apps/api/alpherion/data/jobs/`, rodam na imagem da API como serviço `data` e são **idempotentes**: rodar de novo é a operação normal, não a de emergência.
> Correção de dado **nunca é feita à mão no banco** (§8.10). Erro confirmado vira correção na fonte do pipeline e reprocessamento — é isso que este runbook descreve.

## Como um job se comporta

| Situação | Status em `etl_runs` | Saída do processo |
| --- | --- | --- |
| Rodou e gravou | `success` | 0 |
| Outro processo já estava rodando (lock) | `skipped` | 0 |
| Fonte sem `terms_checked_at` em produção (ADR-017) | `skipped` | 0 |
| Fonte fora do ar, formato mudou, erro de gravação | `failed` (com `error`) | 1 |

Toda execução abre e fecha uma linha em `etl_runs` (`job`, `period`, `rows`, `error`) — inclusive quando falha. É daí que sai o alerta de frescor.

## 1. Ver o que aconteceu

```sql
-- últimas execuções, mais recentes primeiro
SELECT job, period, status, rows, started_at, finished_at, left(error, 200)
FROM market.etl_runs
ORDER BY started_at DESC
LIMIT 30;

-- um job específico, quando rodou bem pela última vez
SELECT max(started_at) FROM market.etl_runs
WHERE job = 'cotahist_daily' AND status = 'success';
```

```
docker compose logs data --since 24h | grep -i "cotahist_daily"
```

## 2. Rodar um job à mão

Sempre no serviço `data` (é ele que tem o usuário `data`, com escrita no schema `market`):

```
docker compose exec data python -m alpherion.data.jobs.cotahist_daily
docker compose exec data python -m alpherion.data.jobs.cvm_statements --ano 2024
docker compose exec data python -m alpherion.data.jobs.bcb_series
```

Em dev, da raiz do repo:

```
cd apps/api && uv run python -m alpherion.data.jobs.tesouro_daily
```

## 3. Reprocessar um período

O `period` é a unidade de trabalho do job (o pregão, o mês do informe, o ano do exercício) e é o que torna o reprocessamento previsível: **dois períodos diferentes podem rodar em paralelo, o mesmo período não** (o lock inclui o período).

| Job | Unidade | Como reprocessar |
| --- | --- | --- |
| `cotahist_daily` | um pregão | rodar com a data do pregão |
| `cvm_statements` | exercício | `--ano 2024` |
| `cvm_documents` | contínuo (data de entrega) | `--full` relê o ano inteiro; o `protocol` evita duplicata |
| `cvm_fii_reports` | ano dos informes | `--ano 2026` |
| `tesouro_daily`, `bcb_series` | janela recente | `--full` para a série inteira |
| `indicators_rebuild` | dia | recalcula a partir do que está no banco, sem baixar nada |

Nenhum deles apaga linha: o upsert sobrescreve a chave natural (ticker + data, `cvm_code` + período, `protocol`). Por isso "rodar de novo" é seguro em qualquer ordem.

## 4. Lock preso

Um worker morto deixa o lock no Redis até o TTL (4 h). Se for preciso liberar antes:

```
docker compose exec redis redis-cli --no-auth-warning -a "$REDIS_PASSWORD" keys 'alpherion:job:*'
docker compose exec redis redis-cli --no-auth-warning -a "$REDIS_PASSWORD" del 'alpherion:job:<nome>'
```

**Confirme antes que o job não está rodando** (`docker compose top data`): apagar o lock de um job vivo faz dois carregarem o mesmo período ao mesmo tempo.

## 5. Fonte bloqueada por licença (ADR-017)

`skipped` com "sem termos verificados" não é falha: é a trava do ADR-017. A fonte só roda em produção depois que a licença estiver registrada — e o desbloqueio é uma linha no banco, não um deploy:

```sql
UPDATE market.data_sources
SET terms_checked_at = CURRENT_DATE, license_note = '<documento e data>'
WHERE source = 'b3';
```

Antes disso, registrar a verificação em [`docs/fontes-de-dados.md`](../fontes-de-dados.md) e mudar o ADR-017 para "aceita". As flags `MARKET_B3_PRICES_ENABLED` / `MARKET_CRYPTO_ENABLED` continuam valendo para a **exibição**; a linha em `data_sources` libera a **carga**.

## 6. Quando a fonte mudou de formato

Sintoma: `failed` com "resposta não é JSON", "nenhum arquivo casou", "conta ausente" em massa, ou `success` com `rows` muito abaixo do normal.

1. Não mexer no banco.
2. Conferir o que a fonte está devolvendo hoje (a URL do job está no módulo de `sources/`).
3. Ajustar o parser **com um teste sobre uma fixture pequena** — o repositório não guarda arquivo real de terceiro.
4. Reprocessar o período afetado.

Endpoints da B3 são os únicos não documentados e os que mais mudam; o fallback está previsto em cada job (cadastro pelo FRE/CVM, carteira de índice mantém a última conhecida com a data à vista).

## 7. Depois de reprocessar

- `indicators_rebuild` se mexeu em demonstrações, preço ou eventos.
- `market_events_rebuild` se mexeu em proventos ou documentos.
- `revalidate_pages` para o Next regerar as páginas afetadas.
