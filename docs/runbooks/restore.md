# Runbook — restore de backup

> site.md §7.6: `pg_dump` diário de cada banco → `age` (chave pública na VPS, **privada fora**) → S3 fora da VPS; retenção 30 dias. Schema `market` só semanal (é reconstruível pelas fontes).
> Scripts (Etapa 2.6): `infra/scripts/backup.sh`, `infra/scripts/restore-test.sh`. Teste de restore **mensal** obrigatório; a data do último teste fica no fim deste arquivo.

## O que existe no bucket

```
s3://<bucket>/postgres/app/AAAA-MM-DD.sql.age        # schema app (web): usuários, consentimentos, carteiras cifradas, análises
s3://<bucket>/postgres/listmonk/AAAA-MM-DD.sql.age   # a lista — o ativo
s3://<bucket>/postgres/umami/AAAA-MM-DD.sql.age
s3://<bucket>/postgres/market/AAAA-Www.sql.age       # semanal
s3://<bucket>/env/AAAA-MM-DD.env.age                 # .env cifrado (só a chave privada abre)
```

Cada `.age` tem um `.sha256` ao lado. Sem a **chave privada do `age`** nada disso abre — ela está em dois lugares offline (§7.6); a chave pública está no `.env` (`BACKUP_AGE_PUBLIC_KEY`).

## A. Teste mensal (sem tocar em produção)

```
infra/scripts/restore-test.sh app 2026-09-20      # baixa, decifra, sobe Postgres efêmero, restaura, confere contagens
```

O script imprime `users`, `consents`, `portfolios`, `transactions`, `analyses` (app) ou `subscribers` (listmonk) e compara com o `manifest.json` gravado no backup. Sucesso = contagens batem e o container efêmero é destruído. Registrar a data abaixo.

## B. Restore real (perda de dados ou incidente)

1. **Congelar:** `docker compose stop web api data` (nginx fica: página estática de manutenção).
2. **Backup do estado atual antes de sobrescrever**, mesmo corrompido: `infra/scripts/backup.sh --tag pre-restore`.
3. Baixar e decifrar o dump escolhido (na sua máquina, onde está a chave privada):
   ```
   aws s3 cp s3://<bucket>/postgres/app/AAAA-MM-DD.sql.age .
   sha256sum -c AAAA-MM-DD.sql.age.sha256
   age -d -i ~/.age/alpherion-backup.key AAAA-MM-DD.sql.age > app.sql
   ```
4. Copiar `app.sql` para a VPS (`scp`, permissão 600) e restaurar **no schema certo, com o usuário certo**:
   ```
   docker compose exec -T postgres psql -U postgres -d alpherion -c 'DROP SCHEMA app CASCADE; CREATE SCHEMA app AUTHORIZATION web;'
   docker compose exec -T postgres psql -U postgres -d alpherion < app.sql
   docker compose exec -T postgres psql -U postgres -d alpherion -f /docker-entrypoint-initdb.d/init.sql   # reaplica GRANTs (§7.6)
   ```
   Listmonk/Umami: mesmo padrão, banco próprio (`-d listmonk`, `-d umami`).
   `market`: preferir `backfill-market.sh` (fonte da verdade são as fontes); usar o dump semanal só para ganhar tempo.
5. Migrações: `pnpm --filter web db:migrate` e `uv run alembic upgrade head` — o dump pode ser de antes da última migration.
6. Religar `api` → `web` → `data`; smoke test (`/`, `/entrar`, `/v1/health`, um login por magic link, uma análise).
7. **Dados cifrados:** movimentações/análises só abrem com a `APP_ENCRYPTION_KEY_V<n>` da época do dump. Se a chave rotacionou desde então, o `.env` restaurado precisa ter **todas** as versões (`key_version` na linha diz qual usar).
8. Comunicar usuários se houve perda de dados entre o dump e o incidente (dizer o período). LGPD: perda de dados também é incidente ([incidente.md](incidente.md)).
9. Apagar `app.sql` em claro da sua máquina e da VPS.

## C. Perda da VPS inteira

`bootstrap-vps.sh` numa VPS nova → `deploy.sh <última tag>` → `.env` decifrado do bucket (ou da sua cópia) → passos B.3–B.6 para `app`, `listmonk`, `umami` → `backfill-market.sh` → DNS/Cloudflare apontando para o IP novo → Uptime Kuma verde.

## Registro dos testes de restore

| Data | Banco | Dump | Resultado | Quem |
| --- | --- | --- | --- | --- |
| — | — | — | (primeiro teste: obrigatório antes da `v0.1.0`) | Bryan |
