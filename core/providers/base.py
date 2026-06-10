"""
base.py - Contrato comum dos providers de uso + helpers HTTP/parse.

Cada provider implementa `fetch(token) -> UsageSnapshot`. A parte de rede
(urllib, stdlib - sem dependencia nova) e o parsing defensivo ficam aqui para
nao duplicar entre Claude e Codex.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Optional, Protocol

from core import config
from core.models import UsageSnapshot, UsageState

logger = logging.getLogger("barra_uso_ia.providers")


class UsageProvider(Protocol):
    """Interface que tray/scheduler consomem sem conhecer o provider concreto."""

    name: str

    def fetch(self, token: str) -> UsageSnapshot:
        ...


def http_get_json(
    url: str,
    token: str,
    *,
    timeout: int = config.HTTP_TIMEOUT_SECONDS,
    extra_headers: Optional[dict[str, str]] = None,
) -> tuple[Optional[dict], Optional[UsageState]]:
    """Faz GET autenticado e devolve (payload, None) em sucesso ou
    (None, UsageState) classificando a falha.

    Seguranca: nunca loga headers, token ou corpo; apenas url e status/erro.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "barra-uso-ia/1.0",
    }
    if extra_headers:
        headers.update(extra_headers)

    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            logger.warning("Resposta inesperada (nao-objeto) de %s", url)
            return None, UsageState.PARSE_ERROR
        return data, None
    except urllib.error.HTTPError as exc:
        logger.warning("HTTP %s ao consultar %s", exc.code, url)
        if exc.code in (401, 403):
            return None, UsageState.AUTH_ERROR
        return None, UsageState.NETWORK_ERROR
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning("Erro de rede ao consultar %s: %s", url, type(exc).__name__)
        return None, UsageState.NETWORK_ERROR
    except json.JSONDecodeError:
        logger.warning("JSON invalido na resposta de %s", url)
        return None, UsageState.PARSE_ERROR


def first_number(data: dict, keys: tuple[str, ...]) -> Optional[float]:
    """Primeiro valor numerico dentre as chaves candidatas."""
    for key in keys:
        value = data.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return float(value)
    return None


def coerce_datetime(raw: Any) -> Optional[datetime]:
    """Interpreta epoch (s/ms) ou ISO-8601; None se nao reconhecer."""
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        value = float(raw)
        if value > 1e12:
            value /= 1000.0
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(raw, str) and raw.strip():
        try:
            return datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    return None
