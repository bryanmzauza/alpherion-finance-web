"""Rotas dos ativos listados (site.md §2.3).

Três regras valem em todas elas:

- **Escopo `market:read`.** A API não conhece usuários; o token identifica o serviço.
- **A trava do ADR-017 é aplicada na saída**, por `flags.Gate`, e não em cada consulta:
  rota nova herda o comportamento certo sem ninguém precisar lembrar.
- **Ordenação de lista fechada.** Campo fora de `repository.SORTABLE` é 422, com a lista
  do que é aceito. Não existe ordenação "recomendada": o padrão é liquidez, que é neutra.

Nenhuma rota aqui devolve juízo de valor — nem nota, nem classificação, nem "barata".
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from alpherion.auth import Caller, require_scopes
from alpherion.db.session import get_session
from alpherion.market import cache, market_data, repository, schemas
from alpherion.market.flags import Gate
from alpherion.settings import Settings, get_settings

router = APIRouter(tags=["market"], dependencies=[Depends(require_scopes("market:read"))])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
CallerDep = Annotated[Caller, Depends(require_scopes("market:read"))]

SecurityType = Literal["stock", "unit", "fii", "fiagro", "etf", "bdr"]
Range = Literal["1m", "6m", "1a", "5a", "max"]


def get_gate(settings: Annotated[Settings, Depends(get_settings)]) -> Gate:
    return Gate(settings)


GateDep = Annotated[Gate, Depends(get_gate)]


def _check_sort(sort: str) -> None:
    if sort not in repository.SORTABLE:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"ordenação inválida. Aceitas: {', '.join(sorted(repository.SORTABLE))}",
        )


@router.get("/assets/search", response_model=schemas.AssetSearchResult)
async def search_assets(
    session: SessionDep,
    gate: GateDep,
    q: Annotated[str, Query(min_length=2, max_length=60)],
    limit: Annotated[int, Query(ge=1, le=20)] = 6,
) -> schemas.AssetSearchResult:
    """Busca global (§2.3): ações, FIIs, ETFs, BDRs, índices, Tesouro e cripto, por classe.

    `limit` é por grupo. Ticker exato vem primeiro dentro do grupo de papéis.
    """
    result = await market_data.search_assets(session, q, per_group=limit)
    groups = [
        group.model_copy(
            update={"items": gate.apply_all(group.items, crypto=group.asset_class == "crypto")}
        )
        for group in result.groups
    ]
    return result.model_copy(update={"groups": groups})


@router.get("/securities", response_model=schemas.Page[schemas.SecuritySummary])
async def list_securities(
    session: SessionDep,
    gate: GateDep,
    type: SecurityType | None = None,  # noqa: A002 - é o nome do parâmetro no contrato
    sector: str | None = None,
    sort: str = repository.DEFAULT_SORT,
    dir: Literal["asc", "desc"] = "desc",  # noqa: A002
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=repository.MAX_PAGE_SIZE)] = 50,
    min_volume: Decimal | None = None,
) -> schemas.Page[schemas.SecuritySummary]:
    """Lista de papéis, ordenada pelo critério que o cliente escolher."""
    _check_sort(sort)
    result = await repository.list_securities(
        session,
        type_=type,
        sector_slug=sector,
        sort=sort,
        descending=dir == "desc",
        page=page,
        page_size=page_size,
        min_volume=min_volume,
    )
    return result.model_copy(update={"items": gate.apply_all(result.items)})


@router.get("/securities/{ticker}", response_model=schemas.SecurityDetail)
async def get_security(session: SessionDep, gate: GateDep, ticker: str) -> schemas.SecurityDetail:
    """Perfil, cabeçalho de preço e indicadores — cada bloco com a sua própria fonte."""
    code = ticker.strip().upper()

    async def load() -> schemas.SecurityDetail:
        detail = await repository.get_security(session, code)
        if detail is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"papel não encontrado: {ticker}")
        # O que vai para o cache é o que foi servido: a chave já carrega o estado das
        # flags, então um cache aquecido não sobrevive a uma mudança de licença.
        return detail.model_copy(
            update={
                "price": gate.apply(detail.price),
                "indicators": gate.apply(detail.indicators),
            }
        )

    return await cache.cached("security", code, model=schemas.SecurityDetail, loader=load)


@router.get("/securities/{ticker}/history", response_model=list[schemas.Quote])
async def get_history(
    session: SessionDep,
    gate: GateDep,
    ticker: str,
    range: Range = "1a",  # noqa: A002 - nome do parâmetro no contrato
    adjusted: bool = True,
) -> list[schemas.Quote]:
    """Histórico diário. Ajustado por proventos e eventos, salvo se `adjusted=false`."""

    async def load() -> list[schemas.Quote]:
        return gate.apply_all(
            await repository.history(session, ticker, range_=range, adjusted=adjusted)
        )

    return await cache.cached_list(
        "list", ticker.upper(), range, adjusted, model=schemas.Quote, loader=load
    )


@router.get("/securities/{ticker}/dividends", response_model=list[schemas.CorporateEvent])
async def get_dividends(session: SessionDep, ticker: str) -> list[schemas.CorporateEvent]:
    """Proventos e eventos societários **anunciados**, do mais recente para o mais antigo."""
    return await repository.dividends(session, ticker)


@router.get("/securities/{ticker}/events", response_model=list[schemas.CorporateEvent])
async def get_events(
    session: SessionDep, ticker: str, from_: Annotated[date | None, Query(alias="from")] = None
) -> list[schemas.CorporateEvent]:
    """Data-com e pagamentos anunciados daqui para a frente. Fato com data, não previsão."""
    return await repository.upcoming_events(session, ticker, since=from_)


@router.get("/securities/{ticker}/documents", response_model=schemas.Page[schemas.Document])
async def get_documents(
    session: SessionDep,
    ticker: str,
    category: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=repository.MAX_PAGE_SIZE)] = 50,
) -> schemas.Page[schemas.Document]:
    """Comunicados entregues à CVM: categoria, assunto, data e link. Sem resumo (§8.3)."""
    return await repository.documents(
        session, ticker, category=category, page=page, page_size=page_size
    )


@router.get("/securities/{ticker}/financials", response_model=schemas.Financials)
async def get_financials(
    session: SessionDep,
    ticker: str,
    period: Literal["annual", "quarterly"] = "annual",
) -> schemas.Financials:
    """DRE, balanço e fluxo de caixa do período mais recente publicado."""
    result = await repository.financials(session, ticker, period_type=period)
    if result is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"sem demonstrações {period} para {ticker.upper()}",
        )
    return result
