# Registro das operações de tratamento de dados pessoais (ROPA) — v1

> LGPD art. 37 · versão simplificada para agente de tratamento de pequeno porte (Res. CD/ANPD 2/2022, art. 14)
> Versão 1.0 · 21/09/2026 · Cobre a Fase 0 (site público + lista de e-mail). Atualizar a cada tratamento novo: Etapa 5 (conta, carteira, importação B3), Etapa 6 (análise por IA), v1.x (favoritos, alertas), Fase 1 (conexão B3, IR), Fase 2 (pagamento).

## Controlador e encarregado

| Item | Valor |
| --- | --- |
| Controlador | [RAZÃO SOCIAL], CNPJ [CNPJ], [ENDEREÇO] (placeholders em `apps/web/content/site.ts`) |
| Encarregado (canal de atendimento, art. 41) | Bryan Munaretto Zauza · privacidade@alpherion.com.br · resposta em até 15 dias |
| Operadores (suboperadores) da Fase 0 | Provedor da VPS [a definir — localização decide §8.4]; storage de backup [a definir]; provedor SMTP transacional [a definir]; Cloudflare (proxy/WAF — trafega IP e requisições; sede EUA, transferência internacional coberta pelo DPA da Cloudflare); Listmonk e Umami são self-hosted (não são operadores) |

## Operações de tratamento

| # | Operação | Dados pessoais | Titulares | Finalidade | Base legal (art. 7) | Retenção | Compartilhamento | Segurança (resumo) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Inscrição na lista "Leitura de Mercado" (`POST /api/subscribe`) | E-mail; IP e user-agent no momento do consentimento; versão da política aceita; data | Visitantes do site | Enviar a newsletter semanal e avisos do produto | Consentimento (I), double opt-in | Até o descadastro; prova de consentimento (`app.consents`, e-mail em hash) por 5 anos após (art. 7 VI) | Provedor SMTP (envio); ninguém mais | E-mail em claro só no Listmonk; hash SHA-256 com sal em `consents`; rate limit; sem tracking de abertura por pixel de terceiro |
| 2 | Confirmação e descadastro (`/lista/confirmar`, `/lista/sair`) | Token do assinante (UUID), e-mail (no Listmonk) | Assinantes | Comprovar opt-in; atender revogação em 1 clique (art. 18 IX) | Consentimento (I); obrigação legal (II) para a revogação | Descadastrado vai para lista de supressão (hash) para não reenviar | — | Token de uso único; sem login |
| 3 | Registros de acesso ao site (logs do nginx / `access_log`) | IP, data/hora, rota, user-agent | Visitantes | Segurança e Marco Civil art. 15 | Obrigação legal (II); legítimo interesse (IX) para segurança | 6 meses, purge automático | Cloudflare (proxy) | Sem corpo de requisição; sem PII além do IP |
| 4 | Analytics (Umami, sem cookie) | Nenhum dado pessoal direto: página, referrer, tipo de dispositivo; IP é descartado após hash diário e não é armazenado | Visitantes | Métricas do funil (e-mails, páginas, eventos `subscribe_*`) | Legítimo interesse (IX) — sem identificação do titular | Agregado, indefinido | — | Self-hosted; sem cookie; `data-do-not-track` |
| 5 | Atendimento ao titular (e-mails a privacidade@ e `app.data_requests`) | E-mail, nome se informado, conteúdo do pedido | Titulares que exercem direitos | Atender art. 18 (acesso, correção, exclusão, portabilidade, revogação) | Obrigação legal (II) | Registro do atendimento por 5 anos | — | Caixa de e-mail com 2FA; registro sem cópia de documentos |
| 6 | Contato geral e correção de dado de mercado (contato@, dados@) | E-mail, conteúdo | Quem escreve | Suporte; correção de erro no pipeline | Legítimo interesse (IX) | 12 meses | — | Idem |

## Direitos do titular — como são atendidos na Fase 0

- Confirmação e acesso: por e-mail ao encarregado; resposta com os dados de `consents` (hash → precisa do e-mail do titular para bater) e status no Listmonk.
- Correção: troca de e-mail = novo opt-in.
- Exclusão / revogação: link de descadastro (imediato) ou e-mail; o registro de consentimento é mantido em hash como prova (art. 7 VI) e isso está dito na política.
- Portabilidade: exportação do registro em JSON por e-mail.
- Oposição ao analytics: não há identificação; informado na política.

## Transferência internacional (art. 33)

Depende da localização da VPS, do backup e do SMTP (placeholders do §13). Cloudflare: transferência coberta por cláusulas contratuais padrão (DPA da Cloudflare) — registrar o link do DPA em `docs/dpa/`. Preferência: VPS e storage em São Paulo.

## Incidentes

Plano em [`runbooks/incidente.md`](runbooks/incidente.md). Comunicação à ANPD e aos titulares em até 3 dias úteis quando houver risco ou dano relevante (Res. CD/ANPD 15/2024).

## Próximas versões (o que entra e quando)

| Versão | Etapa | Tratamentos novos |
| --- | --- | --- |
| 1.1 | Etapa 5 (`v0.4.0`) | Conta (e-mail, nome opcional, sessões, IP de login), aceite de termos com prova, carteira e movimentações (cifradas), importação de arquivos da B3 (arquivo descartado; CPF/nome nunca lidos; só hash do arquivo), `audit_log` |
| 1.2 | Etapa 6 (`v1.0.0`) | Análise por IA (snapshot cifrado; ao provedor de LLM vão só números agregados e pseudonimizados — §6.2), exportação/exclusão de conta, `access_log` do app |
| 1.3 | v1.x | Favoritos com login, alertas por e-mail |
| 2.0 | Fase 1 | Conexão oficial B3 (tokens cifrados; B3 como operadora/controladora conjunta conforme contrato), IR (dados fiscais) |
| 3.0 | Fase 2 | Pagamento (dados fiscais 5 anos), CDC |
