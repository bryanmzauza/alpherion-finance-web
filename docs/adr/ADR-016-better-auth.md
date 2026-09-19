# ADR-016 — Better Auth como biblioteca de autenticação

- Data: 19/09/2026
- Status: aceita
- Complementa: ADR-002 (auth self-hosted), ADR-007 (sem senha no v1)

## Contexto

O site.md §3.4 deixa em aberto "Better Auth (ou Auth.js v5)". Os requisitos são: magic link por e-mail (uso único, 15 min, hash no banco), Google OAuth com PKCE, sessão em cookie `HttpOnly Secure SameSite=Lax` com TTL 30 dias sliding e rotação no login, listagem e revogação de sessões em `/conta`, tabelas no Postgres via Drizzle, e 2FA (TOTP/passkey) na Fase 2.

## Decisão

Better Auth, com o adapter Drizzle sobre o schema `app`, plugins `magic-link` e provedor social Google. Sessões persistidas no banco (necessário para "sessões ativas" e revogação server-side).

## Alternativa descartada

Auth.js v5. Funciona, mas o magic link depende de um provider de e-mail acoplado, a gestão de múltiplas sessões por usuário e revogação individual exige código próprio, e 2FA/passkeys não são nativos. Better Auth cobre os três casos com plugins mantidos pelo projeto.

## Consequências

- As tabelas `users`, `sessions`, `accounts`, `verification_tokens` do §4.1 seguem o schema que o Better Auth gera; campos extras (`locale`, `plan`, `delete_requested_at`, `deleted_at`) entram como `additionalFields`.
- O aceite de Termos + Privacidade continua sendo gravado por nós em `consents` (com `document_version`) no hook de criação de conta, não pela biblioteca.
- Revisar esta decisão se a biblioteca mudar de licença ou parar de ser mantida antes da Fase 2.
