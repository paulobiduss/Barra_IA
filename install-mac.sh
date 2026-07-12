#!/usr/bin/env bash
# ============================================================
# install-mac.sh - Instalador de um comando (macOS)
#
# Faz tudo de uma vez:
#   1. Cria/usa um virtualenv em .venv e instala as dependencias
#   2. Gera o app com build.sh (dist/BarraUsoIA.app)
#   3. Copia o .app para /Applications
#
# Uso:  bash install-mac.sh
# ============================================================
set -euo pipefail

APP_NAME="BarraUsoIA"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "============================================================"
echo " Barra de Uso de IA - Instalacao no macOS"
echo "============================================================"
echo

# --- Verificacoes -------------------------------------------------------
if [[ "$(uname)" != "Darwin" ]]; then
  echo "ERRO: este instalador so roda no macOS (uname != Darwin)."
  exit 1
fi

PYTHON_CMD=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD="python"
fi
if [[ -z "$PYTHON_CMD" ]]; then
  echo "ERRO: Python nao encontrado. Instale o Python 3.11+ (https://www.python.org)."
  exit 1
fi

# Exige Python 3.11+.
if ! "$PYTHON_CMD" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
  echo "ERRO: Python 3.11+ e necessario. Versao atual: $($PYTHON_CMD --version 2>&1)"
  exit 1
fi
echo "Python: $($PYTHON_CMD --version 2>&1)"

# --- 1. venv + dependencias --------------------------------------------
echo
echo "[1/3] Preparando ambiente e instalando dependencias..."
if [[ ! -d ".venv" ]]; then
  "$PYTHON_CMD" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements.txt

# --- 2. build -----------------------------------------------------------
echo
echo "[2/3] Gerando o app (.app)..."
bash build.sh

APP_PATH="dist/${APP_NAME}.app"
if [[ ! -d "$APP_PATH" ]]; then
  echo "ERRO: $APP_PATH nao foi gerado. Veja a saida do build acima."
  exit 1
fi

# --- 3. Instalar em /Applications --------------------------------------
echo
echo "[3/3] Instalando em /Applications..."
DEST="/Applications/${APP_NAME}.app"
if [[ -d "$DEST" ]]; then
  echo "Aviso: $DEST ja existe e sera substituido."
  rm -rf "$DEST"
fi
cp -R "$APP_PATH" /Applications/

deactivate || true

echo
echo "============================================================"
echo " Instalacao concluida!"
echo "============================================================"
echo "App instalado em: $DEST"
echo "Para abrir agora:  open -a \"$APP_NAME\""
echo "O icone aparece na barra de menu (sem icone no Dock)."
echo
echo "Requer que 'claude' e/ou 'codex' estejam autenticados"
echo "(claude login / codex login). No macOS o token do Claude"
echo "e lido do Keychain automaticamente quando nao ha arquivo."
echo
