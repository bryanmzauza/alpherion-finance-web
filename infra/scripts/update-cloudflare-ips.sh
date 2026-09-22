#!/usr/bin/env bash
# Atualiza (a) as faixas de IP da Cloudflare no nginx (`set_real_ip_from`) e (b) as regras
# do ufw que permitem 80/443 só da Cloudflare — site.md §7.2.
#
#   infra/scripts/update-cloudflare-ips.sh [--no-ufw] [--no-reload]
#
# Cron semanal (a Cloudflare muda as faixas raramente, mas muda):
#   0 4 * * 1 /opt/alpherion/infra/scripts/update-cloudflare-ips.sh >> /var/log/alpherion-cf-ips.log 2>&1
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="$REPO_DIR/infra/nginx/cloudflare/real-ip.conf"
TMP="$(mktemp)"
trap 'rm -f "$TMP" "$TMP.v4" "$TMP.v6"' EXIT

DO_UFW=1
DO_RELOAD=1
for arg in "$@"; do
  case "$arg" in
    --no-ufw) DO_UFW=0 ;;
    --no-reload) DO_RELOAD=0 ;;
    *) echo "argumento desconhecido: $arg" >&2; exit 2 ;;
  esac
done

echo "==> baixando faixas da Cloudflare"
curl -fsS --max-time 20 https://www.cloudflare.com/ips-v4 -o "$TMP.v4"
curl -fsS --max-time 20 https://www.cloudflare.com/ips-v6 -o "$TMP.v6"

# Sanidade: a lista tem ~15 faixas v4 e ~7 v6. Menos que isso é resposta truncada/erro.
v4_count=$(grep -cE '^[0-9]+\.' "$TMP.v4" || true)
v6_count=$(grep -c ':' "$TMP.v6" || true)
if [ "$v4_count" -lt 10 ] || [ "$v6_count" -lt 4 ]; then
  echo "ERRO: resposta suspeita (v4=$v4_count, v6=$v6_count). Mantendo o arquivo atual." >&2
  exit 1
fi

{
  echo "# Gerado por infra/scripts/update-cloudflare-ips.sh em $(date -Is). Não editar à mão."
  echo "real_ip_header CF-Connecting-IP;"
  echo "real_ip_recursive on;"
  while read -r cidr; do [ -n "$cidr" ] && echo "set_real_ip_from $cidr;"; done < "$TMP.v4"
  while read -r cidr; do [ -n "$cidr" ] && echo "set_real_ip_from $cidr;"; done < "$TMP.v6"
} > "$TMP"

if cmp -s "$TMP" "$OUT"; then
  echo "==> faixas inalteradas"
else
  cp "$TMP" "$OUT"
  echo "==> $OUT atualizado ($v4_count faixas v4, $v6_count v6)"
  if [ "$DO_RELOAD" = 1 ] && docker compose -f "$REPO_DIR/infra/compose.yml" ps nginx >/dev/null 2>&1; then
    docker compose -f "$REPO_DIR/infra/compose.yml" exec -T nginx nginx -t
    docker compose -f "$REPO_DIR/infra/compose.yml" exec -T nginx nginx -s reload
    echo "==> nginx recarregado"
  fi
fi

if [ "$DO_UFW" = 1 ] && command -v ufw >/dev/null 2>&1; then
  echo "==> atualizando ufw (80/443 só da Cloudflare)"
  # Remove as regras antigas com o comentário nosso, sem tocar em SSH.
  while ufw status numbered | grep -q 'cloudflare'; do
    n=$(ufw status numbered | grep -m1 'cloudflare' | sed -E 's/^\[ *([0-9]+)\].*/\1/')
    ufw --force delete "$n"
  done
  while read -r cidr; do
    [ -n "$cidr" ] || continue
    ufw allow proto tcp from "$cidr" to any port 80,443 comment 'cloudflare'
  done < <(cat "$TMP.v4" "$TMP.v6")
  ufw --force reload
  echo "==> ufw atualizado"
fi
