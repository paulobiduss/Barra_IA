"""
usage_service.py - Orquestra credenciais + provider em um unico UsageSnapshot.

Junta a leitura da credencial local (AuthState) com a chamada ao provider,
traduzindo estados de auth em snapshots que a UI sabe exibir. Mantem a tray e
o scheduler ignorantes dos detalhes de cada provider.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Iterable

from core.models import AuthResult, AuthState, UsageSnapshot, UsageState
from core.providers.base import UsageProvider

# Um "job" e o par (leitor de credencial, provider). O leitor e adiado
# (callable) para que a leitura de disco tambem aconteca fora do thread da UI.
UsageJob = tuple[Callable[[], AuthResult], UsageProvider]


def _auth_message(state: AuthState, provider: str) -> str:
    login = "claude login" if provider.lower().startswith("claude") else "codex login"
    if state is AuthState.MISSING:
        return f"credenciais ausentes - rode '{login}'"
    if state is AuthState.INVALID_FILE:
        return "arquivo de credenciais invalido"
    if state is AuthState.EXPIRED:
        return f"token expirado - rode '{login}'"
    return "estado de auth desconhecido"


def collect_usage(auth: AuthResult, provider: UsageProvider) -> UsageSnapshot:
    """Retorna o snapshot de uso, ou um snapshot de erro derivado do estado de
    auth quando a credencial nao esta pronta. Nunca lanca excecao."""
    if not auth.is_ready or auth.token is None:
        return UsageSnapshot(
            provider=provider.name,
            state=UsageState.AUTH_ERROR,
            message=_auth_message(auth.state, provider.name),
            fetched_at=datetime.now(tz=timezone.utc),
        )
    return provider.fetch(auth.token)


def collect_all(jobs: Iterable[UsageJob]) -> list[UsageSnapshot]:
    """Le credenciais e coleta o uso de cada job, em ordem. Parte bloqueante
    (disco + rede) isolada da UI para poder rodar em worker thread. Nunca lanca:
    falha de um job vira AUTH_ERROR para aquele provider, sem afetar os demais."""
    snapshots: list[UsageSnapshot] = []
    for reader, provider in jobs:
        try:
            auth = reader()
            snapshots.append(collect_usage(auth, provider))
        except Exception:  # rede/disco inesperado: nunca derruba a coleta toda
            snapshots.append(
                UsageSnapshot(
                    provider=provider.name,
                    state=UsageState.NETWORK_ERROR,
                    message="falha inesperada na coleta",
                    fetched_at=datetime.now(tz=timezone.utc),
                )
            )
    return snapshots
