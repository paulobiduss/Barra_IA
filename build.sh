#!/usr/bin/env bash
# ============================================================
# build.sh - Gera o app da Barra de Uso de IA para macOS (.app)
# (equivalente do build.bat, porem para macOS)
#
# Produz dist/BarraUsoIA.app, configurado como agente da barra de
# menu (LSUIElement) - sem icone no Dock.
# ============================================================
set -euo pipefail

APP_NAME="BarraUsoIA"
BUNDLE_ID="com.paulobidu.barrausoia"

# Raiz do projeto = diretorio deste script.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "============================================================"
echo " Barra de Uso de IA - Build do .app (macOS)"
echo "============================================================"
echo

# --- Verificacoes -------------------------------------------------------
if [[ "$(uname)" != "Darwin" ]]; then
  echo "ERRO: este script gera um .app e so roda no macOS (uname != Darwin)."
  echo "No Windows use build.bat."
  exit 1
fi

if [[ ! -f "main.py" ]]; then
  echo "ERRO: main.py nao encontrado. Rode este script pela raiz do projeto."
  exit 1
fi

if [[ ! -f "assets/icon.png" ]]; then
  echo "ERRO: assets/icon.png nao encontrado. O icone e necessario para o build."
  exit 1
fi

# Python: preferir python3.
PYTHON_CMD=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD="python"
fi
if [[ -z "$PYTHON_CMD" ]]; then
  echo "ERRO: Python nao encontrado no PATH. Instale o Python 3.11+."
  exit 1
fi
echo "Python selecionado: $PYTHON_CMD ($($PYTHON_CMD --version 2>&1))"

if ! "$PYTHON_CMD" -m PyInstaller --version >/dev/null 2>&1; then
  echo "ERRO: PyInstaller nao esta instalado neste Python."
  echo "Execute: $PYTHON_CMD -m pip install -r requirements.txt"
  exit 1
fi

# --- Icone .icns --------------------------------------------------------
# PyInstaller no macOS espera um .icns. Se nao existir, geramos a partir do
# icon.png com as ferramentas nativas (sips + iconutil).
ICON_ICNS="assets/icon.icns"
if [[ ! -f "$ICON_ICNS" ]]; then
  echo "[icone] Gerando $ICON_ICNS a partir de assets/icon.png..."
  ICONSET="$(mktemp -d)/icon.iconset"
  mkdir -p "$ICONSET"
  for size in 16 32 128 256 512; do
    sips -z "$size" "$size" assets/icon.png \
      --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
    double=$((size * 2))
    sips -z "$double" "$double" assets/icon.png \
      --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
  done
  iconutil -c icns "$ICONSET" -o "$ICON_ICNS"
  rm -rf "$(dirname "$ICONSET")"
fi

# --- Limpeza ------------------------------------------------------------
echo "[1/3] Limpando artefatos anteriores..."
rm -rf build dist "${APP_NAME}.spec"

# --- PyInstaller --------------------------------------------------------
echo "[2/3] Rodando PyInstaller..."
"$PYTHON_CMD" -m PyInstaller -y \
  --clean \
  --windowed \
  --onedir \
  --name "$APP_NAME" \
  --icon "$ICON_ICNS" \
  --osx-bundle-identifier "$BUNDLE_ID" \
  --add-data "assets:assets" \
  --hidden-import PyQt6.QtCore \
  --hidden-import PyQt6.QtGui \
  --hidden-import PyQt6.QtWidgets \
  --hidden-import PyQt6.sip \
  main.py

APP_PATH="dist/${APP_NAME}.app"
if [[ ! -d "$APP_PATH" ]]; then
  echo "ERRO: build terminou, mas $APP_PATH nao foi encontrado."
  exit 1
fi

# --- Barra de menu sem Dock (LSUIElement) -------------------------------
echo "[3/3] Configurando como agente da barra de menu (sem Dock)..."
PLIST="$APP_PATH/Contents/Info.plist"
# 'Add' falha se a chave ja existir; nesse caso usamos 'Set'.
/usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$PLIST" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Set :LSUIElement true" "$PLIST"

echo
echo "Build concluido com sucesso."
echo
echo "App: $APP_PATH"
echo "Para instalar: mova o .app para /Applications, por exemplo:"
echo "  cp -R \"$APP_PATH\" /Applications/"
echo "Depois abra pelo Finder ou com: open -a \"$APP_NAME\""
echo "O icone aparece na barra de menu (sem icone no Dock)."
echo
