# Runbook — Listmonk (lista de e-mail)

O Listmonk é a fonte da verdade da lista (site.md §4.1). O `web` só chama a API dele na inscrição,
confirmação e descadastro, e grava a prova de consentimento em `app.consents` (hash do e-mail, versão
da política, IP, user-agent). Nenhum e-mail em claro fica no banco da aplicação.

## Fluxo

1. `POST /api/subscribe` (landing) → cria o assinante **não confirmado** na lista "Leitura de Mercado"
   → envia o e-mail de confirmação pela **API transacional** do Listmonk (template nosso, remetente
   `EMAIL_FROM_TRANSACTIONAL`, link `SITE_URL/lista/confirmar?t=<uuid do assinante>`).
   O opt-in nativo do Listmonk fica **desligado** (o template dele é de sistema e aponta para a página dele).
2. `/lista/confirmar?t=` → `PUT /api/subscribers/lists` com `status: confirmed`.
3. `/lista/sair?t=` → `action: unsubscribe`, na hora, sem confirmação. As campanhas usam esse link
   no rodapé (template padrão editado pelo script) e o header `List-Unsubscribe` one-click nativo.

## Primeira configuração (dev e produção)

```
# 1. Subir (dev: já está no compose.dev.yml; prod: infra/compose.yml). Primeiro boot instala o schema
#    com LISTMONK_ADMIN_USER / LISTMONK_ADMIN_PASSWORD.
# 2. Configurar lista, usuário de API, templates e settings:
python infra/scripts/listmonk-setup.py --smtp-mailpit   # dev (SMTP → mailpit)
python infra/scripts/listmonk-setup.py                  # prod
# 3. Colar no .env o que o script imprime: LISTMONK_LIST_ID, LISTMONK_OPTIN_TEMPLATE_ID,
#    LISTMONK_API_USER, LISTMONK_API_TOKEN (mostrado UMA vez). Reiniciar o web.
```

Em produção, ainda no painel (`https://news.alpherion.com.br/admin`):

- **Settings → SMTP**: o provedor escolhido (Resend/Postmark/SES sa-east-1), remetente de campanhas
  `leitura@news.alpherion.com.br` — diferente do transacional `no-reply@alpherion.com.br` (§8.8).
- **Settings → General**: `root_url = https://news.alpherion.com.br`; logo.
- Conferir SPF/DKIM/DMARC do apex e de `news.` antes do primeiro envio (`docs/runbooks/producao-manual.md`).
- Enviar uma campanha de teste para um e-mail próprio e verificar: rodapé com `/lista/sair`, header
  `List-Unsubscribe`, endereço físico da ME no rodapé (CAPEM).

## Operação

- **Reenviar confirmação**: o próprio formulário reenvia se o e-mail já existir (sem revelar isso).
- **Pedido de exclusão (LGPD)**: painel → Subscribers → apagar (ou blocklist, se a pessoa pediu para
  nunca mais receber). A prova de consentimento em `app.consents` fica 5 anos (§4.5) — só o hash.
- **Rotação do token de API**: apagar o usuário `web` no painel, rodar o script de novo, atualizar
  `LISTMONK_API_TOKEN` no `.env`, reiniciar o web (`docs/runbooks/rotacao-de-chave.md`).
- **Erro 502 no formulário**: Listmonk fora do ar ou variáveis `LISTMONK_*` ausentes. O log do web
  mostra `[subscribe] falha no Listmonk (status N)`; nunca o e-mail.
- **Backup**: banco `listmonk` entra no `backup.sh` diário (é o ativo do projeto).
