# Runbook — resposta a incidente de segurança / dados pessoais

> site.md §7.7 · LGPD art. 48 · Res. CD/ANPD 15/2024 (comunicação em até **3 dias úteis** a partir do conhecimento)
> Quem: Bryan (encarregado e único operador). Canal: privacidade@alpherion.com.br. Registrar tudo em `docs/incidentes/AAAA-MM-DD-<slug>.md` (pasta privada, fora do repo público se o repo for aberto).

## 0. Reconhecer (minutos)

Sinais: alerta do Uptime Kuma / GlitchTip / Telegram; e-mail de terceiro; comportamento anômalo em `audit_log` (logins em massa, exports em série); pico de 5xx; `etl_runs` com erro estranho; aviso da Cloudflare (WAF) ou do provedor.

Anote **agora**: data/hora (UTC e BRT), como soube, o que viu. O relógio dos 3 dias úteis começa no conhecimento.

## 1. Conter (primeira hora)

Na ordem, pulando o que não se aplica:

1. **Cloudflare:** "Under Attack Mode" ou regra de WAF bloqueando o padrão/IP; se for comprometimento do app, regra que devolve 503 para `app.alpherion.com.br` inteiro.
2. **Sessões e tokens:**
   - Revogar todas as sessões do app: `DELETE FROM app.sessions;` (usuário `web`) — todo mundo faz login de novo por magic link.
   - Rotacionar `API_SERVICE_TOKENS` / `API_SERVICE_TOKEN_WEB`, `REVALIDATE_TOKEN`, `BETTER_AUTH_SECRET` ([rotacao-de-chave.md](rotacao-de-chave.md)).
   - Se o vazamento incluir o `.env`: rotacionar **tudo** — senhas do Postgres e Redis, chaves do Listmonk, SMTP, CoinGecko, Anthropic, Telegram, S3, `APP_ENCRYPTION_KEY_*` (nova versão; recifrar).
3. **Isolar:** `docker compose stop <serviço>` do container suspeito; não apagar o container nem o volume (evidência). Se for a VPS inteira: snapshot no painel do provedor, depois desligar.
4. **Preservar logs:** copiar para fora da VPS `docker compose logs --no-color <serviço>`, `/var/log/nginx/*`, dump de `app.audit_log` e `app.access_log` do período, `market.etl_runs`. Guardar hash SHA-256 de cada arquivo.

## 2. Avaliar (primeiras 24 h)

Responder por escrito no registro do incidente:

- **O que:** quais tabelas/arquivos/segredos. Dado pessoal? Qual (e-mail, IP, carteira cifrada, snapshot de análise)? Cifrado com que chave (`key_version`)?
- **Quem:** quantos titulares (contar em `consents`, `users`, `portfolios`); assinantes da lista (Listmonk) ou usuários do app.
- **Quando:** janela entre primeiro acesso indevido e contenção (por `audit_log`, `access_log`, nginx).
- **Como:** causa raiz provável (credencial, dependência, configuração, humano).
- **Risco ao titular:** dados cifrados sem a chave = risco baixo; e-mails em claro = risco de phishing (relevante); carteira em claro = risco relevante.

## 3. Comunicar

Comunicação obrigatória à ANPD **e** aos titulares quando o incidente "puder acarretar risco ou dano relevante" (art. 48; Res. 15/2024 lista: dados sensíveis, de menores, financeiros, em larga escala, com possibilidade de fraude…). Carteira e movimentações são dados financeiros → na dúvida, **comunicar**.

- **ANPD:** formulário no sistema da ANPD (Res. 15/2024) em até 3 dias úteis; pode ser comunicação preliminar com complemento em até 20 dias úteis. Conteúdo: natureza dos dados, titulares afetados, medidas técnicas, riscos, medidas tomadas, contato do encarregado.
- **Titulares:** e-mail em linguagem simples (via Listmonk para assinantes; transacional para usuários do app): o que aconteceu, quais dados, o que fizemos, o que a pessoa deve fazer (trocar senha de e-mail se reutilizada; desconfiar de e-mails pedindo dados; nós nunca pedimos senha). Assinado pelo Bryan, com o e-mail do encarregado.
- **Página pública** em `/aviso-de-incidente` (SSG, temporária) quando o alcance for amplo.
- Se envolver dados da B3 (Fase 1): comunicar a B3 conforme o contrato.

Sem comunicação obrigatória → mesmo assim registrar o incidente e a justificativa de "sem risco relevante" (a ANPD pode pedir).

## 4. Corrigir e restaurar

- Corrigir a causa (patch, rotação, regra) **antes** de religar.
- Se houve alteração de dados: restaurar do backup ([restore.md](restore.md)) para um ponto anterior ao incidente, comparar e reaplicar o que for legítimo.
- Religar por partes: `api` → `web` → `data`; Cloudflare de volta ao normal; observar 24 h.

## 5. Encerrar (até 7 dias)

Post-mortem sem culpa no registro: linha do tempo, causa raiz, o que funcionou, o que faltou, **ações com dono e prazo** — cada uma vira teste, regra no CI ou item no plano. Atualizar `docs/ropa.md` se o tratamento mudou.

## Contatos e links

| O quê | Onde |
| --- | --- |
| ANPD — comunicação de incidente | https://www.gov.br/anpd → "Comunicação de incidente de segurança" |
| Cloudflare | painel → Security → WAF / Under Attack |
| Provedor da VPS | [preencher] (snapshot, console) |
| Provedor SMTP | [preencher] (revogar chave) |
| GlitchTip / Uptime Kuma | [preencher URLs] |
