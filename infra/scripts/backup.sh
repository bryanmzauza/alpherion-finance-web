#!/usr/bin/env bash
# Backup cifrado fora da VPS (site.md §7.6): pg_dump → age (chave pública) → S3.
# Diário: app (banco da aplicação), listmonk, umami, e o .env.
# Semanal (--market): o schema market, que é grande e reconstruível pelas fontes.
#
#   infra/scripts/backup.sh              # diário
#   infra/scripts/backup.sh --market     # inclui o schema market
#   infra/scripts/backup.sh --tag pre-restore   # rótulo extra no nome do arquivo
#
# Restore: docs/runbooks/restore.md. A chave PRIVADA do age nunca fica na VPS.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE="docker compose -f $REPO_DIR/infra/compose.yml --env-file $REPO_DIR/.env"
# shellcheck disable=SC1091
set -a; . "$REPO_DIR/.env"; set +a

: "${BACKUP_AGE_PUBLIC_KEY:?defina no .env}" "${BACKUP_S3_BUCKET:?}" "${BACKUP_S3_ENDPOINT:?}"
: "${POSTGRES_DB:=alpherion}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

WITH_MARKET=0
TAG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --market) WITH_MARKET=1 ;;
    --tag) TAG="-$2"; shift ;;
    *) echo "argumento desconhecido: $1" >&2; exit 2 ;;
  esac
  shift
done

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
DATE="$(date +%F)"
export AWS_ACCESS_KEY_ID="$BACKUP_S3_ACCESS_KEY" AWS_SECRET_ACCESS_KEY="$BACKUP_S3_SECRET_KEY"
S3="aws s3 --endpoint-url $BACKUP_S3_ENDPOINT"
fail=0

dump_and_ship() {
  local name="$1" file="$WORK/$2" remote="$3"
  shift 3
  echo "==> dump $name"
  if ! $COMPOSE exec -T postgres pg_dump -U postgres --no-owner --no-privileges "$@" > "$file"; then
    echo "ERRO: pg_dump de $name falhou" >&2; fail=1; return
  fi
  local rows; rows=$(wc -c < "$file")
  if [ "$rows" -lt 1024 ]; then
    echo "ERRO: dump de $name tem $rows bytes — suspeito, não vai subir" >&2; fail=1; return
  fi
  age -r "$BACKUP_AGE_PUBLIC_KEY" -o "$file.age" "$file"
  sha256sum "$file.age" | awk '{print $1}' > "$file.age.sha256"
  rm -f "$file" # nunca deixar dump em claro no disco
  echo "==> enviando $remote ($(du -h "$file.age" | cut -f1))"
  $S3 cp "$file.age" "s3://$BACKUP_S3_BUCKET/$remote" --only-show-errors || { echo "ERRO: upload de $name falhou" >&2; fail=1; return; }
  $S3 cp "$file.age.sha256" "s3://$BACKUP_S3_BUCKET/$remote.sha256" --only-show-errors || fail=1
}

# Banco da aplicação: schema `app` (usuários, consentimentos, carteiras cifradas, análises).
dump_and_ship "app" "app$TAG.sql" "postgres/app/$DATE$TAG.sql.age" -d "$POSTGRES_DB" --schema=app
# A lista é o ativo (roadmap §1).
dump_and_ship "listmonk" "listmonk$TAG.sql" "postgres/listmonk/$DATE$TAG.sql.age" -d listmonk
dump_and_ship "umami" "umami$TAG.sql" "postgres/umami/$DATE$TAG.sql.age" -d umami
if [ "$WITH_MARKET" = 1 ]; then
  dump_and_ship "market" "market$TAG.sql" "postgres/market/$(date +%G-W%V)$TAG.sql.age" -d "$POSTGRES_DB" --schema=market
fi

# O .env cifrado: sem ele o restore não abre as colunas cifradas (APP_ENCRYPTION_KEY_V*).
age -r "$BACKUP_AGE_PUBLIC_KEY" -o "$WORK/env.age" "$REPO_DIR/.env"
$S3 cp "$WORK/env.age" "s3://$BACKUP_S3_BUCKET/env/$DATE$TAG.env.age" --only-show-errors || fail=1

# Manifesto com as contagens — o restore-test.sh compara com o que restaurou.
{
  echo "{"
  echo "  \"date\": \"$DATE\","
  echo "  \"tag\": \"${TAG#-}\","
  for t in users consents data_requests portfolios transactions analyses; do
    n=$($COMPOSE exec -T postgres psql -U postgres -d "$POSTGRES_DB" -tAc \
        "SELECT count(*) FROM app.$t" 2>/dev/null || echo "null")
    echo "  \"app.$t\": $n,"
  done
  n=$($COMPOSE exec -T postgres psql -U postgres -d listmonk -tAc "SELECT count(*) FROM subscribers" 2>/dev/null || echo "null")
  echo "  \"listmonk.subscribers\": $n"
  echo "}"
} > "$WORK/manifest.json"
$S3 cp "$WORK/manifest.json" "s3://$BACKUP_S3_BUCKET/manifest/$DATE$TAG.json" --only-show-errors || fail=1

echo "==> limpando backups com mais de $RETENTION_DAYS dias"
cutoff=$(date -d "-$RETENTION_DAYS days" +%s)
$S3 ls "s3://$BACKUP_S3_BUCKET/" --recursive | while read -r d _ _ key; do
  [ -n "$key" ] || continue
  if [ "$(date -d "$d" +%s)" -lt "$cutoff" ]; then
    $S3 rm "s3://$BACKUP_S3_BUCKET/$key" --only-show-errors
  fi
done

if [ "$fail" != 0 ]; then
  echo "BACKUP COM FALHA em $(date -Is)" >&2
  if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_ALERT_CHAT_ID:-}" ]; then
    curl -fsS -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
      -d "chat_id=$TELEGRAM_ALERT_CHAT_ID" -d "text=⚠️ Backup do Alpherion falhou em $DATE — ver /var/log/alpherion/backup.log" >/dev/null || true
  fi
  exit 1
fi
echo "==> backup de $DATE concluído"
