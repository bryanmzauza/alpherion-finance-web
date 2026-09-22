#!/usr/bin/env bash
# Teste de restore (site.md §7.6: mensal, obrigatório). Sobe um Postgres efêmero,
# restaura o dump escolhido e compara as contagens com o manifesto do backup.
# NÃO toca em produção. Rode na sua máquina, onde está a chave privada do age.
#
#   infra/scripts/restore-test.sh app 2026-09-20
#   infra/scripts/restore-test.sh listmonk 2026-09-20
#   AGE_KEY=~/.age/alpherion-backup.key infra/scripts/restore-test.sh app 2026-09-20
#
# Registre o resultado na tabela de docs/runbooks/restore.md.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC1091
set -a; . "$REPO_DIR/.env"; set +a

WHAT="${1:?uso: restore-test.sh <app|listmonk|umami|market> <AAAA-MM-DD>}"
DATE="${2:?informe a data do backup (AAAA-MM-DD ou AAAA-Www para market)}"
AGE_KEY="${AGE_KEY:-$HOME/.age/alpherion-backup.key}"
[ -f "$AGE_KEY" ] || { echo "chave privada do age não encontrada em $AGE_KEY" >&2; exit 1; }

WORK="$(mktemp -d)"
CONTAINER="alpherion-restore-test-$$"
cleanup() { docker rm -f "$CONTAINER" >/dev/null 2>&1 || true; rm -rf "$WORK"; }
trap cleanup EXIT

export AWS_ACCESS_KEY_ID="$BACKUP_S3_ACCESS_KEY" AWS_SECRET_ACCESS_KEY="$BACKUP_S3_SECRET_KEY"
S3="aws s3 --endpoint-url $BACKUP_S3_ENDPOINT"
REMOTE="postgres/$WHAT/$DATE.sql.age"

echo "==> baixando $REMOTE"
$S3 cp "s3://$BACKUP_S3_BUCKET/$REMOTE" "$WORK/dump.sql.age" --only-show-errors
$S3 cp "s3://$BACKUP_S3_BUCKET/$REMOTE.sha256" "$WORK/dump.sql.age.sha256" --only-show-errors
echo "==> conferindo integridade"
echo "$(cat "$WORK/dump.sql.age.sha256")  $WORK/dump.sql.age" | sha256sum -c -

echo "==> decifrando"
age -d -i "$AGE_KEY" -o "$WORK/dump.sql" "$WORK/dump.sql.age"

echo "==> subindo Postgres efêmero"
docker run -d --name "$CONTAINER" -e POSTGRES_PASSWORD=test -e POSTGRES_DB=restoretest postgres:16-alpine >/dev/null
for _ in $(seq 1 30); do
  docker exec "$CONTAINER" pg_isready -U postgres -d restoretest >/dev/null 2>&1 && break
  sleep 1
done

echo "==> restaurando"
# Os dumps de schema (app/market) trazem CREATE SCHEMA; os de banco (listmonk/umami) não.
docker exec -i "$CONTAINER" psql -v ON_ERROR_STOP=1 -U postgres -d restoretest < "$WORK/dump.sql" >/dev/null
rm -f "$WORK/dump.sql" # nada em claro a mais que o necessário

echo "==> contagens"
$S3 cp "s3://$BACKUP_S3_BUCKET/manifest/$DATE.json" "$WORK/manifest.json" --only-show-errors 2>/dev/null || echo "{}" > "$WORK/manifest.json"
status=0
check() { # check <rótulo no manifesto> <consulta>
  local label="$1" sql="$2" got want
  got=$(docker exec "$CONTAINER" psql -U postgres -d restoretest -tAc "$sql" 2>/dev/null || echo "erro")
  want=$(jq -r --arg k "$label" '.[$k] // "—"' "$WORK/manifest.json")
  printf "    %-26s restaurado=%-8s manifesto=%s\n" "$label" "$got" "$want"
  if [ "$want" != "—" ] && [ "$want" != "null" ] && [ "$got" != "$want" ]; then status=1; fi
}

case "$WHAT" in
  app)
    for t in users consents data_requests portfolios transactions analyses; do
      check "app.$t" "SELECT count(*) FROM app.$t"
    done ;;
  listmonk) check "listmonk.subscribers" "SELECT count(*) FROM subscribers" ;;
  market)   check "market.daily_quotes" "SELECT count(*) FROM market.daily_quotes" ;;
  umami)    check "umami.website_event" "SELECT count(*) FROM website_event" ;;
esac

if [ "$status" = 0 ]; then
  echo "==> RESTORE OK ($WHAT, $DATE). Anote em docs/runbooks/restore.md."
else
  echo "==> DIVERGÊNCIA entre o restaurado e o manifesto — investigar antes de confiar neste backup." >&2
fi
exit "$status"
