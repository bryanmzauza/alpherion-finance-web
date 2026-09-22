# ADR-017 — Fonte das cotações da B3: licença antes de publicar

- Data: 21/09/2026
- Status: **proposta** — aguarda (1) resposta da B3 à consulta de enquadramento e (2) decisão do Bryan sobre o lançamento
- Complementa: ADR-005 (Yahoo fora do produto), ADR-010 (pipeline próprio sobre fontes oficiais e gratuitas), ADR-018 (paridade com o Status Invest)
- Base: [fontes-de-dados.md](../fontes-de-dados.md) (verificação de 21/09/2026, cópias dos documentos em `docs/fontes-de-dados/`)

## Contexto

O ADR-010 assumiu "custo zero de dado" com fontes oficiais e gratuitas, e o §8.10 mandou verificar os termos da B3 antes de publicar cotações. A verificação mostrou que **download público não é licença**:

- Os termos de uso do site b3.com.br vedam "a utilização dos dados contidos neste website para fins comerciais salvo mediante autorização prévia e por escrito da B3", e os índices (inclusive carteiras teóricas) são propriedade intelectual exclusiva da B3.
- A Política de Consumo de Market Data 2026 trata o histórico como "Market Data Histórico B3", de titularidade da B3; a exibição em site aberto exige Licença de Distribuição em Atraso (Snapshot: R$ 320/mês por dataset em 2026); o armazenamento do histórico para construir produto (indicadores, engine de risco) exige contrato de Produtizador, avaliado caso a caso.
- O mesmo vale, por outro motivo, para o CoinGecko: o plano Demo não permite uso comercial.

Isso afeta: cotação, histórico, volume, market cap, P/L, P/VP, EV/EBITDA, PSR, DY, `/indices`, tabs Hoje de `/mercado`, `MarketStrip` (Ibovespa/IFIX), `/cripto` e o engine (séries de preço e cripto). **Não afeta:** demonstrações, cadastro, comunicados, informes de FII, fundos, Tesouro, BCB, agenda, indicadores sem preço.

## Decisão (proposta)

1. **Nenhum dado de preço da B3 nem cripto do CoinGecko Demo vai para produção sem licença registrada em `fontes-de-dados.md`.** Feature flags `MARKET_B3_PRICES_ENABLED` e `MARKET_CRYPTO_ENABLED` (padrão `false` em produção) escondem cotação, gráfico, indicadores de preço, `/indices`, `/cripto` e a classe cripto no engine; as páginas continuam publicáveis com o que vem da CVM/Tesouro/BCB e mostram "—" com o motivo onde faltar preço.
2. **Consulta formal à B3 hoje** ([e-mail rascunhado](../fontes-de-dados/email-b3-licenca.md)), pedindo enquadramento (Atraso Snapshot × Produtizador), condição para histórico e engine, e meio de acesso. Orçamento previsto: R$ 320/mês (Atraso Snapshot) + eventual condição de Produtizador. Assinatura eletrônica do Termo de Adesão assim que confirmado.
3. **Cripto:** contratar CoinGecko Analyst (≈ US$ 129/mês) **ou** trocar por API pública de exchange com termos que permitam exibição — decidir junto com o item 2; até lá, Demo só em dev.
4. **O pipeline continua sendo construído com o COTAHIST e a carteira teórica** (Etapa 3), porque uso em desenvolvimento não é distribuição, o formato dos arquivos é o mesmo que um licenciado recebe, e a fonte fica atrás de uma interface (`sources/b3_*.py`) que aceita trocar o canal de acesso (arquivos do site, UP2DATA, distribuidor) sem mudar o schema.
5. O ADR-010 passa a ler "fontes oficiais; gratuitas quando a licença permitir; **licença da B3 e do provedor de cripto são custo fixo do produto**".

## Opções para o lançamento de 09/10 (decisão do Bryan)

| Opção | O que acontece em 09/10 | Risco |
| --- | --- | --- |
| **A. Publicar sem preço até a B3 responder (recomendada)** | Portal e páginas de ativo saem com CVM/Tesouro/BCB/agenda/comunicados; cotação, gráficos, indicadores de preço, índices e cripto ligados por flag no dia em que a licença for registrada | Portal incompleto no vídeo 3; a resposta da B3 pode levar semanas. Zero risco jurídico |
| B. Publicar com COTAHIST e CoinGecko Demo, com atribuição, enquanto a licença é negociada | Portal completo no vídeo 3 | Uso contrário aos termos escritos da B3 e do CoinGecko; a B3 declara que "tomará as medidas cabíveis para regularizar"; exposição pública no YouTube aumenta a chance de notificação. Se vier, o caminho é o da opção A à força |
| C. Adiar o v1.0 até a licença | Nada sai até a resposta | Data indefinida; contradiz o sprint |

Recomendação: **A**, com o e-mail enviado hoje e ligação para a central de contratação (+55 11 2565-5080) na quarta-feira se não houver retorno. O que o vídeo 3 demonstra continua sendo o raio-x (que roda sobre Tesouro/BCB/CVM e sobre a carteira do usuário; cripto e ações entram no engine quando a flag ligar).

## Alternativas descartadas

- **Provedor licenciado (brapi, Fintz, Cedro) como fonte, sem contrato próprio com a B3.** Na política de 2026, quem exibe dados da B3 em site aberto é Redistribuidor e precisa de Termo de Adesão próprio; o provedor só resolve o canal de acesso, não a licença de exibição. Continua sendo uma opção de **canal** (item 4), não de licença.
- **Yahoo Finance / raspagem de sites.** ADR-005 e §8.10.
- **Ignorar e publicar (opção B) como decisão de arquitetura.** Pode ser uma decisão de negócio do Bryan, mas não entra como padrão do projeto: a regra registrada é "nenhuma fonte em produção sem status OK".

## Consequências

- Etapa 3 do plano ganha o critério "publicável sem preço": todo componente de mercado precisa renderizar com `price = null`.
- `market.data_sources` passa a ser bloqueante: job em produção só roda para fonte com `terms_checked_at` preenchido.
- Custo fixo novo no roadmap (§6 Stack): B3 (≥ R$ 320/mês) + cripto (≈ US$ 129/mês ou alternativa). Entra no `roadmap.md` na próxima sincronização.
- `[Unreleased]` do CHANGELOG e `plano-de-desenvolvimento.md` referenciam este ADR; quando a B3 responder, o status muda para "aceita" e este arquivo registra a licença, o número do contrato e a data.
