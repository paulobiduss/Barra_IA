"""
claude_provider.py - Uso do Claude via endpoint OAuth (nao documentado).

GET https://api.anthropic.com/api/oauth/usage  (Authorization: Bearer <token>)

O schema real deve ser validado empiricamente; por isso o parser tolera
multiplos nomes de campo e nunca quebra a UI.
"""

from __future__ import annotations

from core import config
from core.models import UsageSnapshot, UsageState
from core.providers.base import build_snapshot, http_get_json


def parse_claude_usage(data: dict) -> UsageSnapshot:
    """Converte o payload do endpoint em UsageSnapshot, de forma tolerante."""
    return build_snapshot(
        config.PROVIDER_CLAUDE,
        data,
        used_keys=("used", "used_credits", "usage", "amount_used"),
        limit_keys=("limit", "total", "credit_limit", "quota"),
        percent_keys=("percent", "percentage", "utilization", "used_percent"),
        reset_keys=("reset_at", "resets_at", "reset", "renews_at", "period_end"),
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
