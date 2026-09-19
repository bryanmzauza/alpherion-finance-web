"""Auth por token de serviço (site.md §7.5).

Cada cliente (`web`, futuro bot) tem um token de 256 bits e uma lista de escopos.
A API não conhece usuários: o token identifica o *serviço* que chama, nunca a pessoa.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from alpherion.settings import Settings, get_settings


@dataclass(frozen=True)
class Caller:
    name: str
    scopes: frozenset[str]


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


def authenticate(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> Caller:
    token = _bearer_token(request)
    if token is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Token de serviço ausente",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Percorre todos os clientes sem sair cedo: comparação em tempo constante.
    found: Caller | None = None
    for name, client in settings.service_clients.items():
        if secrets.compare_digest(client.token, token):
            found = Caller(name=name, scopes=client.scopes)
    if found is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Token de serviço inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return found


def require_scopes(*required: str) -> Callable[..., Caller]:
    """Dependência: `Depends(require_scopes("market:read"))`."""

    def dependency(caller: Annotated[Caller, Depends(authenticate)]) -> Caller:
        missing = set(required) - caller.scopes
        if missing:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail=f"Escopo necessário: {', '.join(sorted(missing))}",
            )
        return caller

    return dependency
