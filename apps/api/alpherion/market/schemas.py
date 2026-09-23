"""Contratos das respostas de mercado (site.md §2.3, §3.5).

Duas convenções valem para **toda** resposta desta área, e o front depende delas:

1. **Todo bloco de número traz a sua origem** (`source`): a fonte, o documento ou
   período, e quando foi atualizado. É o que alimenta o `SourceBadge` — a regra do
   produto é "nenhum número de mercado sem fonte" (§5), e ela só se sustenta se a
   resposta carregar a origem junto com o valor.
2. **Ausência vem com motivo.** Campo `null` nunca é zero, e `missing_reasons` diz por
   quê — "empresa não publicou DFP 2025", "cotação indisponível (fonte não licenciada)".
   A página mostra "—" e põe o motivo no tooltip. É a mesma convenção de
   `indicators_daily.missing_reasons`, de ponta a ponta.

Nenhum campo aqui expressa juízo de valor: não há nota, score, classificação, "barata"
nem preço-alvo (§8.3, ADR-018). Listas ordenadas trazem a métrica usada no próprio
contrato (`metric`), para que o título da página possa dizer por que aquela ordem.
"""

from __future__ import annotations

# `datetime` entra como módulo, não pelos nomes: um campo chamado `date` (e há vários)
# sombrearia o tipo `date` dentro da classe, e a anotação passaria a valer `None`.
import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, Field


class SourceRef(BaseModel):
    """Origem de um bloco de dados — vira o `SourceBadge` na página."""

    #: Nome curto da fonte, como em `market.data_sources` ("cvm", "b3", "tesouro").
    source: str
    #: Atribuição exigida pela licença ("Fonte: CVM").
    attribution: str
    #: Documento ou período de referência ("DFP 2025", "pregão de 18/09/2026").
    document: str | None = None
    #: Quando o dado entrou no nosso banco (não quando a fonte o publicou).
    updated_at: dt.datetime | None = None


class Block(BaseModel):
    """Base de todo bloco: origem obrigatória e motivo de cada ausência."""

    source: SourceRef
    #: {"pe": "lucro 12 m negativo"} — vira o tooltip do "—".
    missing_reasons: dict[str, str] = Field(default_factory=dict)


class Page[T](BaseModel):
    """Paginação simples. O limite máximo é da rota (≤ 100, §2.3)."""

    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        return max(1, -(-self.total // self.page_size))


class Quote(BaseModel):
    """Cotação de um dia. Sem licença da B3, os preços vêm `null` (ADR-017)."""

    date: dt.date
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    close: Decimal | None = None
    close_adjusted: Decimal | None = None
    volume: Decimal | None = None


class PriceHeader(Block):
    """Cabeçalho da página do ativo: cotação e variação, com fonte e data."""

    ticker: str
    price: Decimal | None = None
    change_day: Decimal | None = None
    change_percent_day: Decimal | None = None
    low_52w: Decimal | None = None
    high_52w: Decimal | None = None
    volume: Decimal | None = None
    quote_date: dt.date | None = None


class SecuritySummary(BaseModel):
    """Linha de lista (`/acoes`, `/fiis`, `/setores/{slug}`, busca).

    Os indicadores vêm junto porque a tabela do setor os mostra lado a lado (§2.1) —
    e porque ordenar por uma coluna que não aparece na tabela esconde do leitor o
    critério da ordem. Todos dependem do preço e passam pela trava do ADR-017.
    """

    ticker: str
    type: str
    company_name: str
    trade_name: str | None = None
    sector_slug: str | None = None
    price: Decimal | None = None
    change_percent_day: Decimal | None = None
    volume: Decimal | None = None
    pe: Decimal | None = None
    pvp: Decimal | None = None
    dy_12m: Decimal | None = None
    roe: Decimal | None = None
    market_cap: Decimal | None = None
    #: Motivo de cada `null` — a trava de licença preenche; a linha mostra "—" com ele.
    missing_reasons: dict[str, str] = Field(default_factory=dict)


class SecurityProfile(Block):
    """Cadastro do papel: o que a página mostra fora dos números de mercado."""

    ticker: str
    type: str
    company_name: str
    trade_name: str | None = None
    cnpj: str | None = None
    cvm_code: int | None = None
    isin: str | None = None
    sector: str | None = None
    subsector: str | None = None
    segment: str | None = None
    sector_slug: str | None = None
    listing_segment: str | None = None
    etf_index_slug: str | None = None
    bdr_ratio: str | None = None
    status: str


class Indicators(Block):
    """Indicadores do dia. Todo campo é opcional — e o motivo de cada `null` está no bloco."""

    date: dt.date | None = None
    pe: Decimal | None = None
    pb: Decimal | None = None
    pvp: Decimal | None = None
    ev_ebitda: Decimal | None = None
    ev_ebit: Decimal | None = None
    psr: Decimal | None = None
    dy_12m: Decimal | None = None
    payout: Decimal | None = None
    market_cap: Decimal | None = None
    roe: Decimal | None = None
    roic: Decimal | None = None
    roa: Decimal | None = None
    gross_margin: Decimal | None = None
    ebitda_margin: Decimal | None = None
    net_margin: Decimal | None = None
    net_debt_ebitda: Decimal | None = None
    net_debt_equity: Decimal | None = None
    current_ratio: Decimal | None = None
    revenue_cagr_5y: Decimal | None = None
    earnings_cagr_5y: Decimal | None = None
    eps: Decimal | None = None
    bvps: Decimal | None = None


class SecurityDetail(BaseModel):
    """`GET /v1/securities/{ticker}`: perfil, cabeçalho de preço e indicadores.

    Cada bloco traz a **sua** fonte: o cadastro vem da B3, o indicador da CVM e a
    cotação do COTAHIST, em datas diferentes. Uma fonte só para a página inteira daria
    ao leitor a impressão de que tudo foi atualizado junto.
    """

    profile: SecurityProfile
    price: PriceHeader
    indicators: Indicators


class CorporateEvent(BaseModel):
    """Provento ou evento societário anunciado."""

    kind: str
    ex_date: dt.date | None = None
    record_date: dt.date | None = None
    payment_date: dt.date | None = None
    value_per_share: Decimal | None = None
    ratio: str | None = None
    source: str


class Document(BaseModel):
    """Comunicado entregue à CVM: categoria, assunto, data e **link** — sem resumo (§8.3)."""

    protocol: str
    category: str
    type: str | None = None
    subject: str | None = None
    delivered_at: dt.date
    reference_date: dt.date | None = None
    url: str


class StatementLine(BaseModel):
    """Uma conta da demonstração, no formato longo da CVM."""

    account_code: str
    account_name: str
    value: Decimal | None = None


class Financials(Block):
    """DRE, balanço e fluxo de caixa de um período."""

    period_end: dt.date
    period_type: str
    consolidated: bool
    statements: dict[str, list[StatementLine]]


class MarketEvent(BaseModel):
    """Item da agenda: fato com data e origem."""

    id: str
    kind: str
    date: dt.date
    ticker: str | None = None
    #: Classe do papel ("stock", "fii"…), para o filtro por classe da `/agenda`. `null`
    #: em evento macro, que não é de papel nenhum.
    security_type: str | None = None
    title: str
    payload: dict[str, object] | None = None
    source: str


class EventCount(BaseModel):
    """Quantos eventos de um tipo caem num dia — a vista mensal da agenda.

    O mês inteiro passa do teto de itens de uma resposta (proventos de todo o mercado
    mais comunicados), então a vista mensal mostra contagens e linka para a semana.
    Contagem é fato; o que ela não faz é escolher quais itens "importam".
    """

    date: dt.date
    kind: str
    count: int


class StripItem(Block):
    """Um item da faixa do header."""

    key: str
    label: str
    value: Decimal | None = None
    change_percent: Decimal | None = None
    unit: str | None = None


class Mover(BaseModel):
    """Papel numa lista do dia. A métrica que ordenou vem em `MoversList.metric`."""

    ticker: str
    #: Classe do papel, para o link ir direto à página certa.
    type: str | None = None
    company_name: str
    price: Decimal | None = None
    change_percent: Decimal | None = None
    volume: Decimal | None = None
    missing_reasons: dict[str, str] = Field(default_factory=dict)


class MoversList(Block):
    """Lista ordenada por **uma** métrica declarada — fato ordenado, não recomendação."""

    #: "change" ou "volume": vai no título da seção ("Maiores altas por variação do dia").
    metric: str
    direction: str
    min_volume: Decimal | None = None
    items: list[Mover]


class SectorNode(BaseModel):
    """Um nó da árvore de setores (segmento B3 ou segmento de FII)."""

    slug: str
    name: str
    kind: str
    sector: str | None = None
    subsector: str | None = None
    #: Contagem factual de papéis ativos — "23 empresas", sem adjetivo.
    securities_count: int


class SectorDetail(Block):
    """`/v1/sectors/{slug}`: o nó da árvore e os agregados factuais do setor.

    "23 empresas, R$ 410 bi de valor de mercado somado" — soma e contagem, nunca média
    de múltiplo nem "setor barato". O valor de mercado depende do preço e passa pela
    trava do ADR-017 como qualquer outro.
    """

    slug: str
    name: str
    kind: str
    sector: str | None = None
    subsector: str | None = None
    securities_count: int
    #: Soma do valor de mercado dos papéis do setor no último pregão.
    market_cap: Decimal | None = None
    #: Quantos papéis entraram na soma (os que têm valor de mercado no dia).
    market_cap_count: int = 0


class IndexSummary(BaseModel):
    slug: str
    b3_code: str
    name: str


class IndexDetail(Block):
    """Índice com o último fechamento. A carteira vem em `/composition`."""

    slug: str
    b3_code: str
    name: str
    description: str | None = None
    rebalance_note: str | None = None
    value: Decimal | None = None
    change_percent: Decimal | None = None
    date: dt.date | None = None


class IndexMember(BaseModel):
    ticker: str
    company_name: str | None = None
    #: Participação em fração (0,0812 = 8,12%).
    weight: Decimal | None = None
    theoretical_qty: Decimal | None = None


class IndexCompositionResult(Block):
    """Carteira teórica — **a data é parte do dado** e a página tem de mostrá-la."""

    slug: str
    reference_date: dt.date
    members: list[IndexMember]


class IndexPoint(BaseModel):
    date: dt.date
    value: Decimal | None = None
    change_percent: Decimal | None = None


class TreasuryBondItem(Block):
    """Título do Tesouro com taxa e preço do dia. Fonte ODbL: não depende da B3."""

    slug: str
    name: str
    index_type: str
    maturity: dt.date
    coupon: bool
    date: dt.date | None = None
    buy_rate: Decimal | None = None
    sell_rate: Decimal | None = None
    buy_price: Decimal | None = None
    sell_price: Decimal | None = None


class TreasuryPoint(BaseModel):
    date: dt.date
    buy_rate: Decimal | None = None
    sell_rate: Decimal | None = None
    buy_price: Decimal | None = None
    sell_price: Decimal | None = None


class CryptoItem(Block):
    """Criptoativo com o snapshot mais recente (ADR-017: travado até a fonte licenciada)."""

    id: str
    symbol: str
    name: str
    rank: int | None = None
    price: Decimal | None = None
    change_24h: Decimal | None = None
    market_cap: Decimal | None = None
    volume_24h: Decimal | None = None


class CryptoPoint(BaseModel):
    date: dt.date
    price: Decimal | None = None
    volume: Decimal | None = None


class QuoteItem(Block):
    """Cotação atual de um papel, para o app valorizar a carteira."""

    ticker: str
    price: Decimal | None = None
    date: dt.date | None = None


class AssetHit(BaseModel):
    """Um resultado da busca global. `href` não vem daqui: o caminho é do `web`."""

    #: "stock", "unit", "fii", "fiagro", "etf", "bdr", "index", "treasury" ou "crypto".
    type: str
    #: Ticker, slug do índice ou do título, id do cripto.
    code: str
    name: str
    price: Decimal | None = None
    change_percent: Decimal | None = None
    missing_reasons: dict[str, str] = Field(default_factory=dict)


class AssetSearchGroup(BaseModel):
    """Resultados de uma classe. A ordem dos grupos é fixa (`ASSET_CLASSES`)."""

    asset_class: str
    items: list[AssetHit]


class AssetSearchResult(BaseModel):
    """`/v1/assets/search`: resultado agrupado por classe (§2.3)."""

    query: str
    groups: list[AssetSearchGroup]


class MarketOverview(BaseModel):
    """`/v1/market/overview`: o que o portal mostra de uma vez.

    Contadores são **factuais** ("412 empresas listadas"), nunca qualificados. As listas
    do dia trazem a métrica que as ordenou, e cada bloco tem a sua fonte.
    """

    strip: list[StripItem]
    counters: dict[str, int]
    gainers: MoversList
    losers: MoversList
    most_traded: MoversList
    events: list[MarketEvent]


class WeeklyChange(BaseModel):
    """Um ativo no snapshot da Leitura de Mercado."""

    key: str
    label: str
    price: Decimal | None = None
    change_7d: float | None = None
    change_30d: float | None = None
    change_ytd: float | None = None
    low_52w: Decimal | None = None
    high_52w: Decimal | None = None


class WeeklyCorrelation(BaseModel):
    pair: list[str]
    #: Janela em pregões → correlação de Pearson dos retornos diários.
    windows: dict[int, float | None]


class WeeklyVolatility(BaseModel):
    key: str
    #: Janela em pregões → desvio-padrão anualizado dos retornos.
    windows: dict[int, float | None]


class WeeklyReading(Block):
    """`POST /v1/market/weekly-reading` — os números do vídeo de segunda (§2.3).

    Endpoint **interno**: o mesmo cálculo de `ferramentas/leitura-semanal.py`, mas sobre
    as nossas tabelas. É o que garante que o número do vídeo e o número do site sejam o
    mesmo número.
    """

    reference_date: dt.date
    snapshot: list[WeeklyChange]
    correlations: list[WeeklyCorrelation]
    volatilities: list[WeeklyVolatility]
