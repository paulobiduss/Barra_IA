"""
config.py - Constantes de configuracao (caminhos, URLs, intervalos).

Centraliza valores que poderiam mudar entre versoes dos CLIs ou ambientes,
para que o restante do codigo nao tenha caminhos/URLs espalhados.
"""

from __future__ import annotations

import os
from pathlib import Path

# --- Caminhos das credenciais locais -------------------------------------
# Multiplataforma: `~` resolve para %USERPROFILE% no Windows e para o home do
# usuario no macOS/Linux, entao os mesmos caminhos servem para todos os SOs.
HOME = Path(os.path.expanduser("~"))

CLAUDE_CREDENTIALS_PATH = HOME / ".claude" / ".credentials.json"
CODEX_AUTH_PATH = HOME / ".codex" / "auth.json"

# No macOS o CLI do Claude costuma guardar o token OAuth no Keychain (e nao no
# arquivo acima). Este e o nome do servico usado para o fallback read-only via
# `security find-generic-password` (ver core/credentials.py).
CLAUDE_KEYCHAIN_SERVICE = "Claude Code-credentials"

# --- Endpoints de uso (NAO DOCUMENTADOS) ---------------------------------
# Podem mudar sem aviso; o parser e tolerante por isso (ver providers/).
CLAUDE_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
CODEX_USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"

# --- Rede ----------------------------------------------------------------
HTTP_TIMEOUT_SECONDS = 8

# --- Refresh -------------------------------------------------------------
# Intervalo do refresh periodico (ms). 10 min por padrao.
REFRESH_INTERVAL_MS = 10 * 60 * 1000
# Debounce do "Atualizar agora" para evitar spam de cliques (ms).
MANUAL_REFRESH_DEBOUNCE_MS = 3 * 1000

# --- Identificadores de provider -----------------------------------------
PROVIDER_CLAUDE = "Claude"
PROVIDER_CODEX = "Codex"
