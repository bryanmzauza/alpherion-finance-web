# Alpherion Finance — Roadmap

> Última atualização: 20/09/2026
> Responsável: brmz
> **Cópia de referência.** A fonte canônica é `alpherion-finance-yt/docs/roadmap.md`; edite lá e sincronize aqui.

---

## 1. Tese

Quatro pilares, um funil. Não são quatro produtos independentes — cada camada existe para alimentar a seguinte.

| Camada                     | Papel                        | Receita            |
| -------------------------- | ---------------------------- | ------------------ |
| YouTube                    | Aquisição                  | Nenhuma (é custo) |
| Consolidador + análise IA | Retenção e captura de dado | Freemium           |
| Research                   | Monetização recorrente     | Assinatura         |
| Consultoria                | Ticket alto, poucos clientes | Fee                |

**O ativo real não é nenhum dos quatro.** É a lista de e-mails + as carteiras conectadas. Toda decisão de produto deve ser avaliada por quanto contribui para isso.

### Matemática do alvo

- 2.000 assinantes × R$ 50/mês ≈ R$ 1,2M/ano
- 40 clientes de consultoria × R$ 2.500/mês ≈ R$ 1,2M/ano

A consultoria chega ao mesmo número com 50x menos gente — mas exige credencial e confiança, que só o conteúdo constrói. Por isso o conteúdo vem primeiro mesmo sendo o que menos escala.

---

## 2. Restrição regulatória (define a ordem das fases)

| Atividade                                                                | Exigência                                                                         | Status             |
| ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------- | ------------------ |
| Análise/sinais de**cripto**                                       | Fora do perímetro da CVM na maior parte dos casos                                 | ✅ Destravado hoje |
| **Diagnóstico** de carteira (risco, concentração, correlação) | Zona segura, com disclaimer                                                        | ✅ Destravado      |
| **Research de ações/FII**                                        | Atividade privativa de analista credenciado; relatórios assinados por credenciado | ⛔ Exige CNPI      |
| **Recomendação individualizada** / consultoria remunerada        | Res. CVM 19 — registro + graduação + certificação do Anexo A                  | ⛔ Exige registro  |

### Pontos de atenção

- **A CPA provavelmente não habilita como consultor.** O rol prático do Anexo A é CEA, CGA, CFP, CNPI ou CFA. A **CNPI resolve dois problemas de uma vez**: assina research *e* serve de certificação para o registro CVM 19. É o caminho mais curto.
- Graduação superior já atendida (Eng. Química — UFRGS).
- O registro CVM 19 é concedido automaticamente mediante protocolo dos documentos do anexo.
- Consultor **não pode** manter registro como assessor de investimento. É escolha de modelo, não dá para acumular.
- Obrigação contínua: formulário de referência à CVM até 31/03 de cada ano.

### Linha prática do produto de IA

- ✅ **Diagnóstico:** concentração, correlação entre posições, exposição por setor/fator, drawdown histórico, risco de liquidez. *"Sua carteira tem 62% em um único ativo."*
- ⛔ **Recomendação:** ordem de compra/venda de ativo específico para aquele usuário.

Calibrar o prompt do Alpherion para entregar **leitura de risco**, não **ordem de operação**. Disclaimer visível. Em cripto há muito mais folga — explorar isso.

---

## 3. Sprint de lançamento — 20 dias (20/09 → 09/10)

Formato do canal: **tela + voz** no início, rosto entra depois. Cada vídeo com compartilhamento de tela vira demo do produto — conteúdo, prova de valor e tutorial no mesmo take.

> **Nota de 20/09/2026:** o sprint passou de 14 para 20 dias para caber o **portal de dados de mercado** (ver §4). A Fase 0 e o vídeo 1 não mudam; o app abre no vídeo 3 em **09/10**.

### Dias 1–2 · Marca

- [X] Nome fechado
- [X] Logo, paleta, tipografia
- [X] **Travar todos os handles no mesmo dia**: YouTube, X, Telegram, Instagram, TikTok — nome idêntico, inclusive os que não vai usar agora
- [X] Domínio

### Dias 3–4 · Canal e roteiros

- [ ] Canal criado, banner, descrição com CTA para o site
- [X] Roteiros dos 3 primeiros vídeos (ver [youtube/roteiros/](../youtube/roteiros/)):
  - **V1 — formato âncora:** leitura semanal de mercado feita pelo agente. Recorrente, ~70% automatizável, cria hábito de audiência.
  - **V2 — produto:** o portal de dados e a análise de carteira funcionando.
  - **V3 — tese/opinião:** dá cara ao projeto.

### Dias 5–7 · Gravação e landing (até 21/09)

- [ ] Gravar V1 e V2 na mesma sessão (**sempre gravar em lote**)
- [X] Landing no ar: captura de e-mail + prévia da análise
- [ ] Já dá para citar o site nos vídeos

### Dia 8 · Publica V1 (21/09) → `v0.1.0`

- [ ] CTA: entrar na lista

### Dias 8–13 · Pipeline e páginas de ativo (até 28/09) → `v0.2.0`

- [ ] Schema `market`, jobs sobre CVM/B3/Tesouro/BCB/CoinGecko, backfill em produção
- [ ] Páginas de ações, FIIs, ETFs, BDRs, índices (com composição), Tesouro e cripto — todo número com fonte

### Dias 13–17 · Portal (até 02/10) → `v0.3.0`

- [ ] Header com faixa (Ibov, IFIX, dólar, CDI, BTC) e busca global em todo o site
- [ ] `/mercado` (Hoje / Eventos), `/agenda`, `/setores`, comunicados CVM por empresa
- [ ] **V2 publica em 02/10:** demo do portal + raio-x com carteira ilustrativa

### Dias 17–20 · App (até 09/10) → `v0.4.0`, `v1.0.0`

- [ ] Next.js na VPS, Postgres, auth
- [ ] Carteira: manual, CSV, importação dos arquivos da Área do Investidor da B3
- [ ] API do Alpherion como serviço de análise

### Dia 20 · App aberto (09/10)

- [ ] V3 é a demo: usando o produto recém-aberto

---

## 4. Escopo do v1 (app + portal)

**Dentro:**

- Cadastro e login (provedor pronto — não escrever auth)
- Adicionar posições manualmente ou por CSV
- Cotações via API gratuita (CoinGecko para cripto, brapi para B3)
- **Um botão de análise** → manda a carteira para o Alpherion → devolve o diagnóstico
- Plano grátis para todos

**Fora (é v2):**

- Integração com API de exchange
- Parse de nota de corretagem
- Gráficos elaborados
- Pagamento

### Regra dos próximos 60 dias

> Tudo que não for **conteúdo, cadastro ou análise de carteira** está fora do escopo.

> **Nota de 19/09/2026:** o escopo do v1 foi ampliado. Entram **páginas de ativos com cotação, histórico, proventos e indicadores** (ações, FIIs, Tesouro, cripto — fontes oficiais: CVM, B3, Tesouro, BCB, CoinGecko) e **importação da carteira a partir dos arquivos da Área do Investidor da B3** (o CEI não existe mais; integração oficial da B3 fica para a Fase 1).

> **Nota de 20/09/2026 (ADR-018):** o site público passa a ter **paridade funcional com o Status Invest em dado público e ferramentas de carteira**, mantendo o raio-x como diferencial. **v1.0 (09/10):** portal de mercado (busca global, faixa de índices, `/mercado` com Hoje/Eventos, `/agenda`, `/setores`), páginas de ações, FIIs, **ETFs, BDRs, índices com composição**, Tesouro e cripto, comunicados CVM por empresa, carteira/B3, análise. **v1.x (semanas 4–12):** screener completo, calendário de proventos da carteira, favoritos, ITR, evolução e rentabilidade × CDI/Ibov/IPCA, glossário, alertas, comparador, informes de FII, **fundos de investimento (CVM)**, leitura semanal. **Fase 1:** B3 oficial + **imposto de renda (DARF)**. **Fase 2:** pagamento + **internacional** (só com provedor licenciado). O que **nunca** entra: nota/score, "melhores ações", preço justo, ranking editorial, notícias. A regra passa a ser: *conteúdo, cadastro, carteira (incl. B3), análise e portal de dados*. Detalhe, ordem de execução e divisão v1.0 / v1.x em [site.md §11](site.md#11-fases-alinhadas-ao-roadmap-com-as-notas-de-1909-e-20092026); execução em `plano-de-desenvolvimento.md` (v2.0) do repositório de desenvolvimento.

---

## 5. Fases seguintes

### Fase 1 · meses 1–4 — Consolidador de verdade

~~Não competir com Status Invest em dado e gráfico — eles têm 8 anos de vantagem.~~ **Revisado em 19/09/2026:** competir em dado **e** em leitura. O dado (páginas de ativos com fonte oficial e atribuída) é a porta de entrada orgânica; o diferencial defensável continua sendo **"o Alpherion lê a *sua* carteira"**: análise automática de concentração, correlação, exposição a fator, rebalanceamento. Ver [site.md §11](site.md#11-fases-alinhadas-ao-roadmap-com-a-nota-de-19092026) e ADR 14.

- Cripto entra por API de exchange/wallet (fácil)
- B3 entra pela **integração oficial da B3** (usuário autoriza na Área do Investidor; exige contrato com a B3) — a importação dos arquivos da Área do Investidor já está no v1
- Nota de corretagem e CSV como complemento
- **Imposto de renda** (apuração mensal, DARF, relatório anual) e alertas por Telegram — o que o Status Invest cobra
- Free generoso, paywall no relatório com IA

### Fase 2 · meses 3–9 — Monetização, CNPI e research pago

- Pagamento, `/planos`, paywall (relatório com IA, IR, alertas, comparador, histórico longo)
- **Internacional** (stocks, REITs) só com provedor de dados licenciado e receita para pagá-lo (ADR-019)
- Estudar em paralelo com a Fase 1
- Provas CB + CG1 (Apimec) → credenciamento pessoa natural
- Credenciamento da PJ depois
- Assinatura de research de renda variável só **depois** do credenciamento
- Até lá: conteúdo educacional e cripto

### Fase 3 · meses 9–18 — Consultoria

- Registro CVM 19 sobre a PJ
- Modelo fee-based, poucos clientes de ticket alto
- Automatizar a produção de relatório do cliente

---

## 6. Stack e infra

- **Base:** VPS própria, nginx, Cloudflare
- **App:** Next.js + Postgres
- **Auth:** provedor pronto
- **Analytics:** Plausible ou Umami self-hosted
- **Dados:** fontes oficiais (CVM, B3, Tesouro, BCB) em pipeline próprio. **Custo fixo desde o v1.0 (verificado em 21/09/2026, ADR-017):** licença de dados da B3 (≥ R$ 320/mês) e fonte de cripto licenciada (CoinGecko Analyst ≈ US$ 129/mês ou exchange). Provedor pago para internacional só na Fase 2
- **Faturamento:** conteúdo e publicidade pela ME de serviços (consultoria só na Fase 3, em PJ registrada)

### Princípio de arquitetura

> **Uma API só.** O Alpherion serve o bot do Telegram, o site, o consolidador e o research. Se virarem quatro backends, o projeto já foi perdido.

---

## 7. Riscos

| Risco                                                           | Mitigação                                                  |
| --------------------------------------------------------------- | ------------------------------------------------------------ |
| Quatro frentes abertas, uma pessoa → quatro coisas pela metade | Sequenciar, não paralelizar. Regra dos 60 dias.             |
| YouTube não automatiza bem — é o gargalo real de tempo       | Gravação em lote, formato âncora repetível               |
| Produto encostar na fronteira regulatória                      | Diagnóstico ≠ recomendação. Disclaimer. Cripto primeiro. |
| Audiência sem captura de e-mail                                | Captura desde o vídeo 1, sem exceção                      |
| Custo de market data escalar antes da receita                   | CVM/Tesouro/BCB gratuitos; B3 e cripto são licença fixa e barata; internacional só na Fase 2 |
| Portal de dados vira o produto e a leitura fica para trás       | O raio-x é o CTA de toda página de ativo; métrica: página de ativo → conta |

---

## 8. Métricas por fase

- **Fase 0:** e-mails capturados, inscritos, retenção média dos vídeos
- **Fase 1:** carteiras conectadas, análises geradas/usuário, retorno em 7 dias, sessões recorrentes no portal (`/mercado`, `/agenda`), buscas globais, conversão página de ativo → conta
- **Fase 2:** conversão free → pago, churn mensal
- **Fase 3:** clientes de consultoria, receita por cliente
