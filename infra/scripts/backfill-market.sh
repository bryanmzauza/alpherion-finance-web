#!/usr/bin/env bash
# Carga inicial do schema `market` (plano §3.3).
#
#   infra/scripts/backfill-market.sh --sample     # dev: 20 ações, 10 FIIs, 5 ETFs, 5 BDRs,
#                                                 # 3 índices, Tesouro, 20 cripto, 3 anos
#   infra/scripts/backfill-market.sh --full       # produção, antes da tag v0.2.0 (horas)
#   infra/scripts/backfill-market.sh --sample --dry-run
#   infra/scripts/backfill-market.sh --full --etapa cotahist:2025
#
# A ordem das etapas e os limites de cada perfil estão em `alpherion/data/backfill.py`;
# este script só escolhe onde rodar. Interromper e rodar de novo é seguro: cada job é
# idempotente e registra `etl_runs` (docs/runbooks/reprocessar-job.md).
#
# ADR-017: as etapas de fonte bloqueada (B3, CoinGecko) aparecem como **puladas** em
# produção enquanto `data_sources.terms_checked_at` estiver vazio. Isso é esperado, e o
# resumo no fim diz o motivo de cada uma.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MODULE="alpherion.data.backfill"

if [ $# -eq 0 ]; then
  sed -n '2,15p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 2
fi

# Em produção o worker é um container; em dev, o .venv da API.
if [ -f "$REPO_DIR/infra/compose.yml" ] && docker compose -f "$REPO_DIR/infra/compose.yml" ps data --status running --quiet 2>/dev/null | grep -q .; then
  echo "==> backfill no container \`data\`"
  exec docker compose -f "$REPO_DIR/infra/compose.yml" --env-file "$REPO_DIR/.env" \
    exec -T data python -m "$MODULE" "$@"
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "ERRO: container \`data\` não está no ar e \`uv\` não está instalado." >&2
  echo "      Suba o compose de produção ou instale o uv para rodar em dev." >&2
  exit 1
fi

echo "==> backfill local (apps/api/.venv)"
cd "$REPO_DIR/apps/api"
exec uv run python -m "$MODULE" "$@"
