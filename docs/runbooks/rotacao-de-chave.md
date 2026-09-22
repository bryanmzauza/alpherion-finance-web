# Runbook — rotação de chaves e segredos

> site.md §7.4: segredos só no `.env` (600) da VPS; tokens de serviço com 256 bits, um por cliente, rotacionáveis; cifra AES-256-GCM com `key_version` por linha.
> Quando: suspeita de vazamento (imediato — ver [incidente.md](incidente.md)); saída de alguém com acesso; **anual** para tudo; a cada mudança de provedor.

Gerar valores: `openssl rand -base64 32` (256 bits). Nunca colar segredo em chat, issue, commit ou log. Depois de qualquer rotação: `docker compose up -d` dos serviços afetados, smoke test, e anotar a data na tabela do fim.

## Segredos e o que cada rotação exige

| Segredo (`.env`) | Quem usa | Como rotacionar | Efeito colateral |
| --- | --- | --- | --- |
| `API_SERVICE_TOKENS` (api) + `API_SERVICE_TOKEN_WEB` (web) | web → api | Gerar token novo; **adicionar** o novo ao JSON de `API_SERVICE_TOKENS` mantendo o antigo; subir `api`; trocar `API_SERVICE_TOKEN_WEB`; subir `web`; remover o antigo do JSON; subir `api` | Zero downtime se feito nessa ordem |
| `REVALIDATE_TOKEN` | data → web (`/api/revalidate`) | Trocar nos dois; subir `web` e `data` | Revalidações falham no intervalo (páginas ficam com ISR antigo, sem erro) |
| `BETTER_AUTH_SECRET` | web (assinatura de sessão/tokens) | Trocar; subir `web` | **Todas as sessões caem**; magic links pendentes invalidam. Avisar se for planejado |
| `GOOGLE_CLIENT_SECRET` | web | Gerar novo no console do Google; trocar; subir `web`; apagar o antigo no console | Login Google indisponível entre os passos |
| `APP_ENCRYPTION_KEY_V<n>` | web (movimentações, proventos, ajustes, snapshots, tokens B3) | **Nunca sobrescrever.** Adicionar `APP_ENCRYPTION_KEY_V<n+1>`, mudar `APP_ENCRYPTION_KEY_VERSION=<n+1>`, subir `web` (linhas novas usam a nova chave); rodar o job de recifra (`pnpm --filter web crypto:rotate`, Etapa 5) que lê cada linha com a chave da sua `key_version` e regrava com a atual; só depois remover `V<n>` | Sem recifra, a chave antiga é obrigatória para sempre; o backup precisa das duas |
| `PG_*_PASSWORD`, `POSTGRES_SUPERUSER_PASSWORD` | web/api/data/listmonk/umami | `ALTER USER web PASSWORD '…'` no Postgres; trocar no `.env` (`DATABASE_URL`, `MARKET_DATABASE_URL`, `DATA_DATABASE_URL`); subir o serviço | Serviço cai entre `ALTER` e `up`; fazer um por vez |
| `REDIS_PASSWORD` / `REDIS_URL` | web, api, data | Trocar no `.env`; `docker compose up -d redis web api data` | Rate limits e cache zeram (Redis reinicia); locks de jobs somem — não rotacionar durante um job |
| `LISTMONK_API_TOKEN` | web → Listmonk | Painel do Listmonk → Users → usuário de API → novo token; trocar; subir `web` | Inscrições retornam 502 no intervalo |
| `LISTMONK_ADMIN_PASSWORD`, `UMAMI_APP_SECRET`, `*_DB_PASSWORD` | infra | Painel/`ALTER USER`; trocar; subir | Umami: trocar `APP_SECRET` invalida logins do painel |
| `SMTP_PASSWORD` | Listmonk, web | Nova credencial no provedor; trocar; subir; apagar a antiga | E-mails na fila falham no intervalo (Listmonk reenvia) |
| `ANTHROPIC_API_KEY`, `COINGECKO_API_KEY`, `TELEGRAM_BOT_TOKEN` | api / data | Gerar nova no provedor; trocar; subir; revogar a antiga | Análises (fallback genérico) / jobs falham no intervalo |
| `BACKUP_S3_*` | backup.sh | Nova chave no storage; trocar; rodar `backup.sh` à mão; revogar a antiga | — |
| Chave `age` do backup (`BACKUP_AGE_PUBLIC_KEY`) | backup.sh | Gerar par novo (`age-keygen`); guardar a privada nos dois lugares offline; trocar a pública; **manter a privada antiga** até expirar a retenção (30 dias) | Backups antigos só abrem com a chave antiga |
| Certificado de origem Cloudflare (`CLOUDFLARE_ORIGIN_*`) | nginx | Gerar no painel (15 anos); trocar arquivos; `nginx -s reload` | — |
| Chave SSH de deploy (GitHub Actions) | deploy.yml | Novo par; adicionar a pública em `authorized_keys`; trocar o secret no GitHub; remover a antiga | Deploy falha entre os passos |

## Ordem em caso de vazamento total do `.env`

1. `BETTER_AUTH_SECRET` e `API_SERVICE_TOKENS` (corta acesso ao app e à API).
2. Senhas do Postgres e Redis.
3. Chaves de terceiros (SMTP, Anthropic, CoinGecko, Telegram, S3) — revogar nos provedores **primeiro**.
4. `APP_ENCRYPTION_KEY`: nova versão + recifra completa (o dado cifrado com a chave vazada é considerado exposto se o banco também vazou — avaliar no incidente).
5. `age`: par novo; os backups antigos passam a ser tratados como expostos se a privada vazou (ela não deveria estar na VPS).

## Registro

| Data | Segredo | Motivo | Quem |
| --- | --- | --- | --- |
| — | — | — | — |
