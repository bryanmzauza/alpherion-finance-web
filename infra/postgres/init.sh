#!/bin/bash
# Roda uma vez, na criação do volume (docker-entrypoint-initdb.d). O SQL fica fora dessa
# pasta de propósito: o entrypoint executaria o .sql de novo, sem as variáveis. Cria os usuários por
# serviço e os schemas com os GRANTs do site.md §7.6. Senhas vêm do .env.
set -euo pipefail

: "${PG_WEB_USER:=web}" "${PG_API_USER:=api}" "${PG_DATA_USER:=data}"
: "${PG_WEB_PASSWORD:?}" "${PG_API_PASSWORD:?}" "${PG_DATA_PASSWORD:?}"
: "${LISTMONK_DB_PASSWORD:?}" "${UMAMI_DB_PASSWORD:?}"

psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v web_user="$PG_WEB_USER" -v web_password="$PG_WEB_PASSWORD" \
  -v api_user="$PG_API_USER" -v api_password="$PG_API_PASSWORD" \
  -v data_user="$PG_DATA_USER" -v data_password="$PG_DATA_PASSWORD" \
  -v listmonk_password="$LISTMONK_DB_PASSWORD" -v umami_password="$UMAMI_DB_PASSWORD" \
  -f /opt/alpherion/init.sql
