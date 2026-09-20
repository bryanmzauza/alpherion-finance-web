// Conteúdo e placeholders do site (site.md §13). Este é o ÚNICO lugar com
// [RAZÃO SOCIAL], [CNPJ], [ENDEREÇO] e [URL DO CANAL]: preencher antes de publicar.

export const SITE_NAME = "Alpherion Finance";
export const SITE_TAGLINE = "Dados. Insights. Patrimônio.";
export const SITE_DESCRIPTION =
  "O Alpherion lê a sua carteira — cripto, ações, FIIs, renda fixa — e devolve cinco leituras de risco, em segundos, em português. Não diz o que comprar.";

export const LEGAL_ENTITY = {
  razaoSocial: "[RAZÃO SOCIAL]",
  cnpj: "[CNPJ]",
  endereco: "[ENDEREÇO]",
  cidadeUf: "[CIDADE/UF]",
};

export const EMAILS = {
  contato: "contato@alpherion.com.br",
  privacidade: "privacidade@alpherion.com.br",
  dados: "dados@alpherion.com.br",
};

export const YOUTUBE_CHANNEL_URL = "[URL DO CANAL]";

export const AUTHOR = {
  name: "Bryan Munaretto Zauza",
  // Só fatos confirmados (roteiro 03). Complementar aqui, nunca inventar.
  bio: [
    "Engenheiro químico formado na UFRGS — a formação de quem olha sistemas inteiros, não peças isoladas.",
    "Faz a Leitura de Mercado, o Raio-X de Carteira e a Tese no canal do Alpherion Finance no YouTube.",
    "Não é analista (Res. CVM 20) nem consultor (Res. CVM 19) credenciado pela CVM; está estudando para o CNPI. Até lá: ação é educacional, cripto é opinião, carteira é diagnóstico.",
  ],
};

export type Reading = {
  slug: "concentracao" | "correlacao" | "exposicao" | "drawdown" | "liquidez";
  name: string;
  question: string;
  definition: string;
  /** Número da carteira ilustrativa do vídeo 02 (referência 18/09/2026). */
  value: string;
  valueLabel: string;
  status: "risk" | "warn" | "ok";
};

export const READINGS: Reading[] = [
  {
    slug: "concentracao",
    name: "Concentração",
    question: "Você está concentrado?",
    definition: "Quanto da carteira depende de poucos ativos.",
    value: "38%",
    valueLabel: "em um único ativo",
    status: "risk",
  },
  {
    slug: "correlacao",
    name: "Correlação",
    question: "Seus ativos andam juntos?",
    definition: "O quanto dois ativos sobem e caem ao mesmo tempo (1 = iguais, 0 = sem relação).",
    value: "0,91",
    valueLabel: "entre os dois maiores ativos",
    status: "risk",
  },
  {
    slug: "exposicao",
    name: "Exposição",
    question: "A que você está exposto sem saber?",
    definition: "As forças que mexem em vários ativos de uma vez: dólar, juros, commodities, o humor do mercado cripto.",
    value: "0,96",
    valueLabel: "de correlação da carteira com o Bitcoin",
    status: "risk",
  },
  {
    slug: "drawdown",
    name: "Drawdown",
    question: "Quanto ela já caiu — e cairia de novo?",
    definition: "A maior queda do topo ao fundo que a composição atual já viu.",
    value: "−34%",
    valueLabel: "do topo ao fundo, em oito meses",
    status: "warn",
  },
  {
    slug: "liquidez",
    name: "Liquidez",
    question: "Em quanto tempo você consegue sair?",
    definition: "Quanto tempo leva para transformar cada posição em dinheiro sem derrubar o preço.",
    value: "0,03%",
    valueLabel: "do volume diário na posição menos líquida",
    status: "ok",
  },
];

export const DOES_AND_DOESNT = {
  does: [
    "Lê a carteira que você já tem: cripto, ações, FIIs, renda fixa.",
    "Devolve cinco leituras de risco com número, em português.",
    "Mostra a fonte de cada dado.",
    "Deixa você apagar tudo quando quiser.",
  ],
  doesnt: [
    "Não é recomendação de investimento.",
    "Não considera seu perfil nem seus objetivos.",
    "Não indica compra ou venda de nenhum ativo.",
    "Não promete retorno.",
  ],
};

export type Quadro = {
  slug: "leitura" | "raio-x" | "tese";
  name: string;
  day: string;
  promise: string;
};

export const QUADROS: Quadro[] = [
  {
    slug: "leitura",
    name: "Leitura de Mercado",
    day: "Segunda",
    promise: "O que importou na semana em cripto e no Brasil, o que mudou no risco e o que vem na agenda. Leitura, não recomendação.",
  },
  {
    slug: "raio-x",
    name: "Raio-X de Carteira",
    day: "Quarta",
    promise: "Um conceito por vídeo, calculado numa carteira real, com o termo explicado e o resultado lido em voz alta.",
  },
  {
    slug: "tese",
    name: "Tese",
    day: "Sexta",
    promise: "Uma opinião com dado atrás. Cripto: opinião. Ações e FIIs: educação. Toda tese termina com uma pergunta para a sua carteira.",
  },
];

export const FAQ: { q: string; a: string }[] = [
  { q: "É grátis?", a: "Sim. Entrar na lista é grátis e a análise de carteira será gratuita para quem está na lista." },
  {
    q: "Preciso conectar a corretora?",
    a: "Não. Você importa os arquivos que a própria B3 gera na Área do Investidor (posição, negociações e proventos), envia um CSV ou digita as posições. Nenhuma senha de corretora é pedida — nunca.",
  },
  {
    q: "Vocês guardam a minha carteira?",
    a: "Sim, cifrada no nosso banco de dados, para você não precisar digitar de novo. Você apaga tudo quando quiser, na sua conta.",
  },
  {
    q: "Vocês guardam o meu arquivo da B3?",
    a: "Não. O arquivo é lido na hora e descartado; CPF e nome são ignorados na leitura. Fica só um identificador do arquivo para não importar duas vezes.",
  },
  {
    q: "Isso é recomendação de investimento?",
    a: "Não. O Alpherion mostra o que você tem — concentração, correlação, exposição, drawdown, liquidez. Não diz o que comprar ou vender e não considera o seu perfil.",
  },
  { q: "Quando abre?", a: "Quem está na lista sabe primeiro." },
  {
    q: "De onde vêm os dados?",
    a: "De fontes oficiais e públicas: CVM, B3, Tesouro Nacional, Banco Central e CoinGecko. Todo número no site mostra a fonte e a data.",
  },
];

export const DATA_SOURCES = ["CVM", "B3", "Tesouro Nacional", "Banco Central do Brasil", "CoinGecko"];

/** Carteira ilustrativa do vídeo 02 (preços de 18/09/2026). Fictícia, mas realista. */
export const SAMPLE_PORTFOLIO = {
  total: "R$ 120.000",
  referenceDate: "18/09/2026",
  positions: [
    { asset: "BTC", klass: "Cripto", weight: "38%" },
    { asset: "Tesouro Selic", klass: "Renda fixa", weight: "12%" },
    { asset: "ETH", klass: "Cripto", weight: "8%" },
    { asset: "PETR4", klass: "Ação", weight: "8%" },
    { asset: "VALE3", klass: "Ação", weight: "7%" },
    { asset: "ITUB4", klass: "Ação", weight: "6%" },
    { asset: "USDC", klass: "Stablecoin", weight: "5%" },
    { asset: "MXRF11", klass: "FII", weight: "5%" },
    { asset: "SOL", klass: "Cripto", weight: "4%" },
    { asset: "WEGE3", klass: "Ação", weight: "4%" },
    { asset: "HGLG11", klass: "FII", weight: "3%" },
  ],
};
