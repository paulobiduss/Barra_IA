"""
codex_provider.py - Uso do Codex via endpoint backend (nao documentado).

GET https://chatgpt.com/backend-api/wham/usage  (Authorization: Bearer <token>)

Schema real (validado empiricamente em 2026-06-10): nao ha valores absolutos
de "used"/"limit", apenas percentuais por janela em `rate_limit`:

    {
      "rate_limit": {
        "primary_window": {"used_percent": 12, "reset_at": 1781113799, ...},
        "secondary_window": {"used_percent": 2, "reset_at": 1781264790, ...}
      },
      ...
    }

`primary_window` (janela curta, ~5h) vira o percentual/reset principal;
`secondary_window` (janela semanal) vira uma nota informativa.
"""

from __future__ import annotations

from datetime import datetime, timezone

from core import config
from core.models import UsageSnapshot, UsageState
from core.providers.base import coerce_datetime, first_number, http_get_json


def _parse_error() -> UsageSnapshot:
    return UsageSnapshot(
        provider=config.PROVIDER_CODEX,
        state=UsageState.PARSE_ERROR,
        message="formato de resposta inesperado",
        fetched_at=datetime.now(tz=timezone.utc),
    )


def parse_codex_usage(data: dict) -> UsageSnapshot:
    """Converte o payload do endpoint em UsageSnapshot, de forma tolerante."""
    rate_limit = data.get("rate_limit")
    if not isinstance(rate_limit, dict):
        return _parse_error()

    primary = rate_limit.get("primary_window")
    if not isinstance(primary, dict):
        return _parse_error()

    percent = first_number(primary, ("used_percent",))
    if percent is None:
        return _parse_error()

    reset_at = coerce_datetime(primary.get("reset_at"))

    message = None
    secondary = rate_limit.get("secondary_window")
    if isinstance(secondary, dict):
        secondary_percent = first_number(secondary, ("used_percent",))
        if secondary_percent is not None:
            message = f"(semana: {secondary_percent:g}%)"

    return UsageSnapshot(
        provider=config.PROVIDER_CODEX,
        state=UsageState.OK,
        percent=percent,
        reset_at=reset_at,
        message=message,
        fetched_at=datetime.now(tz=timezone.utc),
    )


class CodexUsageProvider:
    name = config.PROVIDER_CODEX

    def __init__(self, url: str = config.CODEX_USAGE_URL):
        self._url = url

    def fetch(self, token: str) -> UsageSnapshot:
        data, error = http_get_json(self._url, token)
        if error is not None:
            return UsageSnapshot(
                provider=self.name,
                state=error,
                message=_message_for(error),
            )
        assert data is not None  # error None => data presente
        return parse_codex_usage(data)


def _message_for(state: UsageState) -> str:
    if state is UsageState.AUTH_ERROR:
        return "token rejeitado - rode 'codex login'"
    if state is UsageState.NETWORK_ERROR:
        return "sem conexao"
    return "formato de resposta inesperado"
