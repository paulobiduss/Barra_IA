"""
models.py - Estruturas de dados compartilhadas (sem dependencia de UI).

Objetivo Macro:
    Definir os contratos de dados que circulam entre credentials -> providers
    -> formatters -> tray, de forma que cada camada nao precise conhecer os
    detalhes da outra.

Fluxo Logico:
    1. Origem: leitura de credenciais (AuthState) e respostas de uso (UsageState).
    2. Transformacao: providers produzem UsageSnapshot a partir do payload.
    3. Destino: formatters/tray consomem UsageSnapshot para montar tooltip/menu.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class AuthState(str, Enum):
    """Estado da credencial local lida em disco."""

    MISSING = "missing"          # arquivo de credenciais nao existe
    INVALID_FILE = "invalid_file"  # arquivo existe mas JSON invalido / campo faltando
    EXPIRED = "expired"          # token presente porem expirado
    READY = "ready"             # token presente e (aparentemente) valido


class UsageState(str, Enum):
    """Resultado da tentativa de obter o uso junto ao endpoint remoto."""

    OK = "ok"                    # snapshot valido
    NOT_LOADED = "not_loaded"    # ainda nao consultado
    AUTH_ERROR = "auth_error"    # 401/403 - token rejeitado pelo servidor
    NETWORK_ERROR = "network_error"  # timeout / DNS / conexao
    PARSE_ERROR = "parse_error"  # resposta em formato inesperado


@dataclass(frozen=True)
class AuthResult:
    """Resultado da leitura defensiva de um arquivo de credenciais.

    Nunca contem o token em logs; `token` so e usado em memoria para a chamada
    HTTP subsequente.
    """

    provider: str
    state: AuthState
    token: Optional[str] = None
    expires_at: Optional[datetime] = None

    @property
    def is_ready(self) -> bool:
        return self.state is AuthState.READY and bool(self.token)


@dataclass(frozen=True)
class UsageSnapshot:
    """Foto do uso de um provider em um instante.

    `used`/`limit` sao opcionais porque endpoints nao documentados podem nao
    devolver ambos; a UI lida com ausencia exibindo o que houver.
    """

    provider: str
    state: UsageState
    used: Optional[float] = None
    limit: Optional[float] = None
    percent: Optional[float] = None
    reset_at: Optional[datetime] = None
    message: Optional[str] = None
    fetched_at: Optional[datetime] = None

    @property
    def is_ok(self) -> bool:
        return self.state is UsageState.OK
