"""
codex_provider.py - Uso do Codex via endpoint backend (nao documentado).

GET https://chatgpt.com/backend-api/wham/usage  (Authorization: Bearer <token>)

O schema real deve ser validado empiricamente; o parser tolera multiplos nomes
de campo e nunca quebra a UI.
"""

from __future__ import annotations

from core import config
from core.models import UsageSnapshot, UsageState
from core.providers.base import build_snapshot, http_get_json


def parse_codex_usage(data: dict) -> UsageSnapshot:
    """Converte o payload do endpoint em UsageSnapshot, de forma tolerante."""
    return build_snapshot(
        config.PROVIDER_CODEX,
        data,
        used_keys=("used", "used_tokens", "usage", "amount_used"),
        limit_keys=("limit", "total", "hard_limit", "quota"),
        percent_keys=("percent", "percentage", "utilization", "used_percent"),
        reset_keys=("reset_at", "resets_at", "reset", "renews_at", "period_end"),
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
