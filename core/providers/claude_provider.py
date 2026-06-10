"""
claude_provider.py - Uso do Claude via endpoint OAuth (nao documentado).

GET https://api.anthropic.com/api/oauth/usage  (Authorization: Bearer <token>)

Schema real (validado empiricamente em 2026-06-10): nao ha valores absolutos
de "used"/"limit", apenas percentuais por janela:

    {
      "five_hour": {"utilization": 65.0, "resets_at": "2026-06-10T16:50:00Z"},
      "seven_day": {"utilization": 7.0, "resets_at": "2026-06-12T15:00:00Z"},
      ...
    }

`five_hour` (janela curta) vira o percentual/reset principal; `seven_day`
(janela semanal) vira uma nota informativa.
"""

from __future__ import annotations

from datetime import datetime, timezone

from core import config
from core.models import UsageSnapshot, UsageState
from core.providers.base import coerce_datetime, first_number, http_get_json


def _parse_error() -> UsageSnapshot:
    return UsageSnapshot(
        provider=config.PROVIDER_CLAUDE,
        state=UsageState.PARSE_ERROR,
        message="formato de resposta inesperado",
        fetched_at=datetime.now(tz=timezone.utc),
    )


def parse_claude_usage(data: dict) -> UsageSnapshot:
    """Converte o payload do endpoint em UsageSnapshot, de forma tolerante."""
    five_hour = data.get("five_hour")
    if not isinstance(five_hour, dict):
        return _parse_error()

    percent = first_number(five_hour, ("utilization",))
    if percent is None:
        return _parse_error()

    reset_at = coerce_datetime(five_hour.get("resets_at"))

    message = None
    seven_day = data.get("seven_day")
    if isinstance(seven_day, dict):
        seven_day_percent = first_number(seven_day, ("utilization",))
        if seven_day_percent is not None:
            message = f"(semana: {seven_day_percent:g}%)"

    return UsageSnapshot(
        provider=config.PROVIDER_CLAUDE,
        state=UsageState.OK,
        percent=percent,
        reset_at=reset_at,
        message=message,
        fetched_at=datetime.now(tz=timezone.utc),
    )


class ClaudeUsageProvider:
    name = config.PROVIDER_CLAUDE

    def __init__(self, url: str = config.CLAUDE_USAGE_URL):
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
        return parse_claude_usage(data)


def _message_for(state: UsageState) -> str:
    if state is UsageState.AUTH_ERROR:
        return "token rejeitado - rode 'claude login'"
    if state is UsageState.NETWORK_ERROR:
        return "sem conexao"
    return "formato de resposta inesperado"
