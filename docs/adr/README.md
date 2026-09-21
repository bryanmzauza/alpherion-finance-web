# Decisões de arquitetura (ADRs)

Registro curto de cada decisão: o que foi decidido, o que foi descartado e por quê. As 14 primeiras vêm do [site.md §12](../site.md#12-decisões-registradas-adrs-curtos); a partir da 15, cada decisão nova ganha um arquivo próprio nesta pasta (`ADR-NNN-titulo.md`) e uma linha aqui.

| # | Decisão | Alternativa descartada | Por quê |
| --- | --- | --- | --- |
| 1 | Engine e pipeline em Python (FastAPI + worker) separados do Next | Tudo em Next/TS | Reaproveita pandas e garante que vídeo e produto dão o mesmo número; "uma API só" para o bot |
| 2 | Auth self-hosted (biblioteca) | Clerk/Auth0 | Dados de login no Brasil, sem custo por MAU, sem mais um suboperador na política |
| 3 | Listmonk self-hosted | Mailchimp/Beehiiv | A lista é o ativo; exportável, sem limite de contatos, LGPD mais simples |
| 4 | Umami sem cookie | GA4 | Sem banner, sem transferência de dado de navegação, suficiente para as métricas da fase |
| 5 | Yahoo Finance fora do produto | Usar como nos scripts | Sem termos de uso para produto; CVM/B3/Tesouro/BCB/CoinGecko são oficiais ou licenciados |
| 6 | Narrativa nunca bloqueia a análise | Falhar se o LLM falhar | Os números são o produto; a narrativa é tradução. Fallback genérico mantém o SLA e a conformidade |
| 7 | Sem senha no v1 | E-mail + senha | Menos superfície (sem hash, sem reset, sem credential stuffing); magic link já basta para o fluxo |
| 8 | Movimentações e posições cifradas na aplicação | Só cifra de disco | Dump de banco não expõe carteira; custo baixo de implementar |
| 9 | Sem banner de cookies | Banner "para garantir" | Não há cookie não essencial; banner sem necessidade é ruído e reduz conversão |
| 10 | Pipeline próprio sobre fontes oficiais e gratuitas | Provedor pago (brapi PRO, Fintz) | Custo zero de dado, controle das fórmulas, atribuição direta à fonte. Fallback licenciado só se os termos da B3 exigirem (§8.10) |
| 11 | Importação de arquivos da Área do Investidor no v1; integração oficial da B3 na Fase 1; **nunca raspagem com credencial** | Pedir login da B3 ao usuário | Funciona hoje sem contrato; zero credencial de terceiro; a integração oficial exige contrato que a Fase 1 comporta |
| 12 | Posições derivadas de movimentações (+ ajustes manuais) | Posição como dado primário | Preço médio, proventos e evolução exigem histórico; a posição manual continua existindo como ajuste |
| 13 | API passa a ter schema próprio (`market`) | API stateless sem tabelas | O dado de mercado é da API por definição; `web` continua sem acesso direto ao schema |
| 14 | Competir em dado **e** em leitura | "Não competir com Status Invest em dado" | Páginas de ativo trazem tráfego orgânico independente do canal; o diferencial continua sendo a leitura, mas o dado é a porta |
| 15 | [Monorepo único para web, api, infra e docs](ADR-015-monorepo.md) | Um repositório por serviço | Uma tag versiona web e api juntos; spec, infra e código evoluem no mesmo PR |
| 16 | [Better Auth como biblioteca de autenticação](ADR-016-better-auth.md) | Auth.js v5 | Magic link e Google nativos, adapter Drizzle, gestão de sessões que `/conta` precisa |
| 17 | _(pendente — Etapa 2.5)_ Fonte das cotações: COTAHIST ou provedor licenciado | — | Depende da verificação dos termos da B3 (`docs/fontes-de-dados.md`) |
| 18 | [Paridade funcional com o Status Invest em dado público e ferramentas de carteira](ADR-018-paridade-status-invest.md) | Manter o escopo de 19/09; home como portal; lançar em 25/09 pela metade | Tráfego orgânico e visita diária sem depender do canal; raio-x continua o diferencial; lista fixa do que nunca entra (nota, "melhores", preço justo, notícias). v1.0 adiado para 09/10/2026 |
| 19 | _(pendente — Fase 2)_ Provedor licenciado para dados internacionais (stocks, REITs) | — | Não há fonte oficial gratuita; entra só com contrato de exibição e receita para pagá-lo |
