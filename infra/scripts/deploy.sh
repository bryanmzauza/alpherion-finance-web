#!/usr/bin/env bash
# Deploy na VPS (site.md §10). Chamado pelo .github/workflows/deploy.yml por SSH,
# ou à mão pelo usuário de deploy:
#
#   infra/scripts/deploy.sh v0.1.0
#   infra/scripts/deploy.sh v0.1.0 --skip-migrations   # tag só de infra
#
# Sequência: checkout da tag → pull das imagens → migrações (app e market) →
# up -d → healthcheck → smoke test. Falhou o smoke test, volta para a tag anterior.
set -euo pipefail

TAG="${1:?uso: deploy.sh <tag> [--skip-migrations]}"
shift || true
SKIP_MIGRATIONS=0
for arg in "$@"; do
  [ "$arg" = "--skip-migrations" ] && SKIP_MIGRATIONS=1
done

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_DIR"
# shellcheck disable=SC1091
set -a; . "$REPO_DIR/.env"; set +a   # SITE_URL, TELEGRAM_* e as variáveis do compose
COMPOSE=(docker compose -f infra/compose.yml --env-file .env)
STATE_FILE="$REPO_DIR/.deploy-current-tag"
PREV_TAG="$(cat "$STATE_FILE" 2>/dev/null || echo "")"

log() { echo "[$(date +%T)] $*"; }

log "==> tag $TAG (anterior: ${PREV_TAG:-nenhuma})"
git fetch --tags --quiet
git -c advice.detachedHead=false checkout --quiet "$TAG"
export IMAGE_TAG="$TAG"

log "==> baixando imagens"
"${COMPOSE[@]}" pull --quiet web api

if [ "$SKIP_MIGRATIONS" = 0 ]; then
  log "==> backup antes das migrações"
  infra/scripts/backup.sh --tag "pre-$TAG" || { log "ERRO: backup falhou, abortando deploy"; exit 1; }

  log "==> migrações do schema app (Drizzle)"
  "${COMPOSE[@]}" run --rm --no-deps -T web node apps/web/scripts/migrate.mjs \
    || { log "ERRO: migração do app falhou"; exit 1; }

  log "==> migrações do schema market (Alembic)"
  "${COMPOSE[@]}" run --rm --no-deps -T api alembic upgrade head \
    || { log "ERRO: migração do market falhou"; exit 1; }
fi

log "==> subindo serviços"
"${COMPOSE[@]}" up -d --remove-orphans

log "==> esperando healthchecks"
deadline=$(( $(date +%s) + 120 ))
while :; do
  unhealthy=$("${COMPOSE[@]}" ps --format '{{.Service}} {{.Health}}' | awk '$2!="healthy" && $2!="" {print $1}' || true)
  [ -z "$unhealthy" ] && break
  if [ "$(date +%s)" -ge "$deadline" ]; then
    log "ERRO: sem healthcheck verde em 120 s: $unhealthy"
    read -ra services <<< "$unhealthy"
    "${COMPOSE[@]}" logs --tail 50 "${services[@]}" || true
    break
  fi
  sleep 5
done

log "==> smoke test"
smoke_fail=0
check() { # check <url> <status esperado> [texto esperado]
  local url="$1" want="$2" needle="${3:-}" code
  # sem -f: queremos o código mesmo quando é 4xx/5xx
  code=$(curl -sS -m 15 -o /tmp/smoke.out -w '%{http_code}' "$url" 2>/dev/null || echo "erro")
  if [ "$code" != "$want" ]; then
    log "    FALHOU $url (HTTP ${code:-erro}, esperado $want)"; smoke_fail=1; return
  fi
  if [ -n "$needle" ] && ! grep -q "$needle" /tmp/smoke.out; then
    log "    FALHOU $url (não encontrou \"$needle\")"; smoke_fail=1; return
  fi
  log "    ok $url"
}

ROOT_URL="${SITE_URL:-https://alpherion.com.br}"
check "$ROOT_URL/" 200 "Alpherion"
check "$ROOT_URL/raio-x" 200
check "$ROOT_URL/robots.txt" 200
check "$ROOT_URL/sitemap.xml" 200
# /entrar e as páginas de ativo entram no smoke test a partir das Etapas 3 e 5.
if "${COMPOSE[@]}" exec -T api python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/v1/health',timeout=10).status==200 else 1)"; then
  log "    ok /v1/health (interno)"
else
  log "    FALHOU /v1/health"; smoke_fail=1
fi

if [ "$smoke_fail" != 0 ]; then
  log "==> SMOKE TEST FALHOU"
  if [ -n "$PREV_TAG" ]; then
    log "==> rollback para $PREV_TAG (imagens; migrações NÃO são revertidas — ver docs/runbooks/restore.md)"
    git -c advice.detachedHead=false checkout --quiet "$PREV_TAG"
    IMAGE_TAG="$PREV_TAG" "${COMPOSE[@]}" up -d
  fi
  if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_ALERT_CHAT_ID:-}" ]; then
    curl -fsS -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
      -d "chat_id=$TELEGRAM_ALERT_CHAT_ID" -d "text=🚨 Deploy $TAG falhou no smoke test${PREV_TAG:+ — rollback para $PREV_TAG}" >/dev/null || true
  fi
  exit 1
fi

echo "$TAG" > "$STATE_FILE"
log "==> deploy $TAG concluído"
docker image prune -f --filter "until=168h" >/dev/null 2>&1 || true
