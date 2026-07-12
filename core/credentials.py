"""
credentials.py - Leitura READ-ONLY das credenciais OAuth locais.

Objetivo Macro:
    Ler os tokens gravados pelos CLIs (`claude login` / `codex login`) sem
    nunca escrever, nunca logar o token e nunca lancar excecao para a UI.

Fluxo Logico:
    1. Origem: arquivos JSON em ~/.claude e ~/.codex. No macOS, se o arquivo do
       Claude nao existir, ha fallback read-only para o Keychain do sistema.
    2. Transformacao: parsing defensivo -> AuthResult com AuthState.
    3. Destino: providers usam o token (em memoria) para a chamada de uso.

Regras de seguranca:
    - Apenas leitura. Nenhuma escrita nos arquivos nem no Keychain.
    - O conteudo do token NUNCA e logado nem colocado em mensagens de erro.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from core import config
from core.models import AuthResult, AuthState


def _coerce_expires_at(raw: Any) -> Optional[datetime]:
    """Tenta interpretar `expires_at` em formatos comuns (epoch s, epoch ms,
    ou ISO-8601). Retorna None se nao reconhecer - ausencia de expiracao nao
    deve invalidar o token."""
    if raw is None:
        return None
    # Epoch numerico (segundos ou milissegundos).
    if isinstance(raw, (int, float)):
        value = float(raw)
        # Heuristica: valores muito grandes estao em milissegundos.
        if value > 1e12:
            value /= 1000.0
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    # String ISO-8601 (aceita sufixo Z).
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _is_expired(expires_at: Optional[datetime]) -> bool:
    if expires_at is None:
        return False
    now = datetime.now(tz=expires_at.tzinfo or timezone.utc)
    return expires_at <= now


def _first_str(data: dict, keys: tuple[str, ...]) -> Optional[str]:
    """Retorna o primeiro valor string nao vazio dentre as chaves candidatas."""
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _load_json(path: Path) -> Optional[Any]:
    """Le e faz parse do JSON. Retorna None se o arquivo nao existir;
    levanta ValueError em JSON invalido (tratado pelo chamador)."""
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    return json.loads(text)


def _build_claude_result(data: dict) -> AuthResult:
    """Converte o payload (do arquivo ou do Keychain) em AuthResult.

    Schema tolerante: o token pode estar na raiz (`access_token`) ou aninhado
    em `claudeAiOauth` (formato usado por versoes recentes do CLI).
    """
    provider = config.PROVIDER_CLAUDE

    # O bloco OAuth pode estar aninhado.
    oauth = data.get("claudeAiOauth")
    source = oauth if isinstance(oauth, dict) else data

    token = _first_str(source, ("access_token", "accessToken", "token"))
    if not token:
        return AuthResult(provider, AuthState.INVALID_FILE)

    expires_at = _coerce_expires_at(
        source.get("expires_at", source.get("expiresAt"))
    )
    if _is_expired(expires_at):
        return AuthResult(provider, AuthState.EXPIRED, token=None, expires_at=expires_at)

    return AuthResult(provider, AuthState.READY, token=token, expires_at=expires_at)


def _load_claude_keychain(
    service: str = config.CLAUDE_KEYCHAIN_SERVICE,
) -> Optional[dict]:
    """Fallback READ-ONLY do macOS: le o token do Claude no Keychain.

    Retorna o dict de credenciais ou None (fora do macOS, se nao encontrar, ou
    em qualquer falha). Usa `security find-generic-password -w`, que apenas le -
    nunca escreve. O conteudo NUNCA e logado nem propagado em excecao.
    """
    if sys.platform != "darwin":
        return None
    try:
        proc = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-w"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if proc.returncode != 0:
        return None

    raw = (proc.stdout or "").strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def read_claude_credentials(
    path: Path = config.CLAUDE_CREDENTIALS_PATH,
) -> AuthResult:
    """Le ~/.claude/.credentials.json e, no macOS, cai para o Keychain se o
    arquivo nao existir.

    Ordem: arquivo primeiro (comportamento identico no Windows/Linux); se o
    arquivo estiver ausente, tenta o Keychain do macOS (`_load_claude_keychain`).
    """
    provider = config.PROVIDER_CLAUDE
    try:
        data = _load_json(path)
    except (ValueError, OSError):
        return AuthResult(provider, AuthState.INVALID_FILE)

    if data is None:
        # Arquivo ausente: no macOS o token pode estar no Keychain.
        data = _load_claude_keychain()
        if data is None:
            return AuthResult(provider, AuthState.MISSING)
    if not isinstance(data, dict):
        return AuthResult(provider, AuthState.INVALID_FILE)

    return _build_claude_result(data)


def read_codex_credentials(
    path: Path = config.CODEX_AUTH_PATH,
) -> AuthResult:
    """Le ~/.codex/auth.json (mesmo caminho em Windows/macOS/Linux).

    Schema tolerante: o token OAuth costuma estar em `tokens.access_token`, mas
    pode aparecer como `access_token`/`accessToken`/`token` na raiz conforme a
    versao. `OPENAI_API_KEY` NAO e aceito de proposito: e uma credencial de
    escopo diferente e nao deve ser enviada como Bearer ao endpoint de uso.
    """
    provider = config.PROVIDER_CODEX
    try:
        data = _load_json(path)
    except (ValueError, OSError):
        return AuthResult(provider, AuthState.INVALID_FILE)

    if data is None:
        return AuthResult(provider, AuthState.MISSING)
    if not isinstance(data, dict):
        return AuthResult(provider, AuthState.INVALID_FILE)

    tokens = data.get("tokens")
    source = tokens if isinstance(tokens, dict) else data

    # So aceitamos o token OAuth do Codex CLI. OPENAI_API_KEY e uma credencial
    # de escopo diferente e NAO deve ser enviada como Bearer ao endpoint
    # chatgpt.com/backend-api/wham/usage (vazaria uma chave mais ampla a um
    # destino inesperado e provavelmente falharia).
    token = _first_str(source, ("access_token", "accessToken", "token"))
    if not token:
        return AuthResult(provider, AuthState.INVALID_FILE)

    expires_at = _coerce_expires_at(
        source.get("expires_at", source.get("expiresAt"))
    )
    if _is_expired(expires_at):
        return AuthResult(provider, AuthState.EXPIRED, token=None, expires_at=expires_at)

    return AuthResult(provider, AuthState.READY, token=token, expires_at=expires_at)
