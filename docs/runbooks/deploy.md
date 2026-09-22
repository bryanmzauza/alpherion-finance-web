# Runbook — primeira subida e deploys

> site.md §7.2, §7.6, §10 · Infra em `infra/` (compose.yml, nginx/, scripts/) · CI/CD em `.github/workflows/deploy.yml`
> Regra: **deploy só por tag** (`v*`); `web` e `api` sempre na mesma tag.

## Parte 1 — o que é manual (uma vez)

Nada disto está em script porque depende de painel de terceiro. Marque conforme fizer.

### 1.1 Domínio e DNS

- [ ] Registro.br: `alpherion.com.br` registrado; alterar os servidores DNS para os da Cloudflare.
- [ ] Cloudflare: adicionar o site (plano Free serve), copiar os nameservers e confirmar a delegação.
- [ ] Registro.br: **ativar DNSSEC** com o DS que a Cloudflare fornece (Cloudflare → DNS → DNSSEC).
- [ ] Registros (todos com **proxy laranja**, exceto os de e-mail):
  | Tipo | Nome | Valor |
  | --- | --- | --- |
  | A | `@` | IP da VPS |
  | A | `www` | IP da VPS |
  | A | `app` | IP da VPS |
  | A | `api` | IP da VPS |
  | A | `stats` | IP da VPS |
  | A | `news` | IP da VPS |
  | A | `status` | IP da VPS |

### 1.2 TLS e borda

- [ ] Cloudflare → SSL/TLS → **Full (strict)**.
- [ ] SSL/TLS → Origin Server → **Create Certificate** (15 anos, `alpherion.com.br` e `*.alpherion.com.br`). Salvar na VPS como `/etc/ssl/alpherion/origin.pem` e `origin.key` (chmod 600) e apontar `CLOUDFLARE_ORIGIN_CERT_PATH` / `CLOUDFLARE_ORIGIN_KEY_PATH` no `.env`.
- [ ] SSL/TLS → Origin Server → **Authenticated Origin Pulls** ligado. Baixar o CA na VPS:
      `curl -fsSL https://developers.cloudflare.com/ssl/static/authenticated_origin_pull_ca.pem -o /opt/alpherion/infra/nginx/tls/cloudflare-origin-pull-ca.pem`
- [ ] SSL/TLS → Edge Certificates: Always Use HTTPS **on**; Minimum TLS **1.2**; HSTS **on** só depois de uma semana estável (o nginx já envia o header).
- [ ] Security → WAF: managed rules **on**; Bot Fight Mode **on**.
- [ ] Security → WAF → Rate limiting rules (§7.2):
      `/api/subscribe` e `/api/auth/*` → 10 req/min por IP; `/api/analyses` e `/api/imports/*` → 10/min por IP; `/v1/*` → 60/min por IP.
- [ ] Caching → Cache Rules: respeitar `Cache-Control` da origem nas rotas de mercado (`/acoes/*`, `/fiis/*`, `/etfs/*`, `/bdrs/*`, `/indices/*`, `/tesouro/*`, `/cripto/*`, `/setores/*`, `/mercado`, `/agenda`); **bypass** em `app.alpherion.com.br` e `api.alpherion.com.br`.
- [ ] Zero Trust → Access: aplicação para `stats.`, `news.` e `status.` (política: e-mail do Bryan). Enquanto não estiver pronto, descomentar o `allow <seu IP>; deny all;` em `infra/nginx/sites/40-servicos.conf`.

### 1.3 E-mail

- [ ] Provedor SMTP escolhido (Resend/Postmark/SES) e domínio verificado; preencher `SMTP_*` e `EMAIL_FROM_TRANSACTIONAL`. Registrar o DPA em `docs/dpa/`.
- [ ] DNS (sem proxy): SPF (`v=spf1 include:<provedor> -all`), DKIM (chaves do provedor), DMARC (`v=DMARC1; p=quarantine; rua=mailto:privacidade@alpherion.com.br; adkim=s; aspf=s`).
- [ ] Mesmos registros para o subdomínio `news.` se as campanhas saírem por ele.
- [ ] Testar em mail-tester.com antes do primeiro envio real (meta: 9/10 ou mais).

### 1.4 VPS

- [ ] VPS Ubuntu 24.04, **região São Paulo** se possível (§8.4: fora do Brasil vira transferência internacional na política).
- [ ] Disco: raiz + volume para o schema `market` montado em `/srv/alpherion/market` (dezenas de GB — §7.6).
- [ ] `ssh root@IP 'bash -s' < infra/scripts/bootstrap-vps.sh`
- [ ] Como `deploy`: `git clone <repo> /opt/alpherion && cd /opt/alpherion`
- [ ] `cp infra/env/.env.example .env && chmod 600 .env` e preencher **tudo** (segredos com `openssl rand -base64 32`).
- [ ] `infra/scripts/update-cloudflare-ips.sh`
- [ ] Storage de backup (S3-compatível) criado; par de chaves `age` gerado (`age-keygen -o alpherion-backup.key`): **pública** no `.env`, **privada** em dois lugares offline, nunca na VPS.

### 1.5 GitHub

- [ ] Secrets: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY` (chave dedicada de deploy), `VPS_SSH_PORT` (se não for 22).
- [ ] Variable `SITE_URL` = `https://alpherion.com.br`.
- [ ] Environment `production` com required reviewer (você) — segura o deploy até a aprovação.

## Parte 2 — primeira subida

```bash
cd /opt/alpherion
git fetch --tags
infra/scripts/deploy.sh v0.1.0          # pull → migrações → up -d → healthcheck → smoke test
docker compose -f infra/compose.yml --env-file .env ps
```

Depois, uma vez:

- [ ] `python infra/scripts/listmonk-setup.py` → colar `LISTMONK_*` no `.env` → `docker compose ... up -d web`
- [ ] Umami (`https://stats.alpherion.com.br`): criar o site, copiar o `UMAMI_WEBSITE_ID` para o `.env`, `up -d web`.
- [ ] Uptime Kuma (`https://status.alpherion.com.br`): monitores para `/`, `/raio-x`, `app.`, `api.` (via `/v1/health` interno não dá — use a home do app), notificação no Telegram.
- [ ] `infra/scripts/backup.sh` à mão e depois `infra/scripts/restore-test.sh app <data>` — **um restore testado é critério de pronto da `v0.1.0`**.
- [ ] Verificar: securityheaders.com (meta A+), ssllabs.com (meta A+), um e-mail real confirmado por double opt-in.

## Parte 3 — deploy normal

1. `CHANGELOG.md` e o checkbox do plano atualizados no commit da entrega.
2. `git tag -a v0.2.0 -m "..." && git push origin v0.2.0` (o Bryan decide quando).
3. O workflow roda lint/typecheck/test → build das imagens → GHCR → aprovação → `deploy.sh` na VPS.
4. Acompanhar: Actions → job `vps`; depois `docker compose logs -f web api`.

**Rollback:** o próprio `deploy.sh` volta para a tag anterior se o smoke test falhar. Rollback manual: `infra/scripts/deploy.sh <tag-anterior> --skip-migrations`. Migração **não** é revertida — se o problema for de migração, restaure ([restore.md](restore.md)).

**Checklist pré-deploy (§10):** CI verde · migrações revisadas (aditivas nesta tag?) · `.env` da VPS atualizado com variáveis novas · backup manual antes de migração destrutiva · securityheaders/SSL Labs após mudança no nginx · `etl_runs` do dia verdes (a partir da Etapa 3).
