# Alpherion Finance — Roadmap

> Última atualização: 17/09/2026
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

## 3. Sprint de lançamento — 14 dias

Formato do canal: **tela + voz** no início, rosto entra depois. Cada vídeo com compartilhamento de tela vira demo do produto — conteúdo, prova de valor e tutorial no mesmo take.

### Dias 1–2 · Marca

- [X] Nome fechado
- [X] Logo, paleta, tipografia
- [X] **Travar todos os handles no mesmo dia**: YouTube, X, Telegram, Instagram, TikTok — nome idêntico, inclusive os que não vai usar agora
- [X] Domínio

### Dias 3–4 · Canal e roteiros

- [ ] Canal criado, banner, descrição com CTA para o site
- [X] Roteiros dos 3 primeiros vídeos (ver [youtube/roteiros/](../youtube/roteiros/)):
  - **V1 — formato âncora:** leitura semanal de mercado feita pelo agente. Recorrente, ~70% automatizável, cria hábito de audiência.
  - **V2 — produto:** a análise de carteira funcionando.
  - **V3 — tese/opinião:** dá cara ao projeto.

### Dias 5–7 · Gravação e landing

- [ ] Gravar V1 e V2 na mesma sessão (**sempre gravar em lote**)
- [ ] Landing no ar: captura de e-mail + prévia da análise
- [ ] Já dá para citar o site nos vídeos

### Dia 8 · Publica V1

- [ ] CTA: entrar na lista

### Dias 9–13 · App

- [ ] Next.js na VPS, Postgres, auth
- [ ] API do Alpherion como serviço de análise
- [ ] V2 publica no dia 11

### Dia 14 · App aberto

- [ ] V3 é a demo: usando o produto recém-aberto

---

## 4. Escopo do v1 do app (o que cabe em 7 dias)

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

> **Nota de 19/09/2026:** o escopo do v1 foi ampliado. Entram **páginas de ativos com cotação, histórico, proventos e indicadores** (ações, FIIs, Tesouro, cripto — fontes oficiais: CVM, B3, Tesouro, BCB, CoinGecko) e **importação da carteira a partir dos arquivos da Área do Investidor da B3** (o CEI não existe mais; integração oficial da B3 fica para a Fase 1). A regra passa a ser: *conteúdo, cadastro, carteira (incl. B3), análise e dados de mercado*. Detalhe, ordem de execução e divisão v1.0 / v1.x em [site.md §11](site.md#11-fases-alinhadas-ao-roadmap-com-a-nota-de-19092026).

---

## 5. Fases seguintes

### Fase 1 · meses 1–4 — Consolidador de verdade

~~Não competir com Status Invest em dado e gráfico — eles têm 8 anos de vantagem.~~ **Revisado em 19/09/2026:** competir em dado **e** em leitura. O dado (páginas de ativos com fonte oficial e atribuída) é a porta de entrada orgânica; o diferencial defensável continua sendo **"o Alpherion lê a *sua* carteira"**: análise automática de concentração, correlação, exposição a fator, rebalanceamento. Ver [site.md §11](site.md#11-fases-alinhadas-ao-roadmap-com-a-nota-de-19092026) e ADR 14.

- Cripto entra por API de exchange/wallet (fácil)
- B3 entra pela **integração oficial da B3** (usuário autoriza na Área do Investidor; exige contrato com a B3) — a importação dos arquivos da Área do Investidor já está no v1
- Nota de corretagem e CSV como complemento
- Free generoso, paywall no relatório com IA

### Fase 2 · meses 3–9 — CNPI e research pago

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
- **Dados:** free tier até doer; migrar quando houver receita
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
| Custo de market data escalar antes da receita                   | Free tier até doer                                          |

---

## 8. Métricas por fase

- **Fase 0:** e-mails capturados, inscritos, retenção média dos vídeos
- **Fase 1:** carteiras conectadas, análises geradas/usuário, retorno em 7 dias
- **Fase 2:** conversão free → pago, churn mensal
- **Fase 3:** clientes de consultoria, receita por cliente
