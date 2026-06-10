"""
main.py - Entry point da Barra de Uso de IA.

Cria o QApplication, carrega o icone e sobe a SystemTray (que cuida do refresh
periodico). Segue o padrao do PomodoroTimer: app sem janela principal, vivo no
loop de eventos do Qt enquanto a bandeja existir.
"""

from __future__ import annotations

import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS  # type: ignore[attr-defined]
else:
    BASE_DIR = str(Path(__file__).resolve().parent)

sys.path.insert(0, BASE_DIR)

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from ui.tray import SystemTray


def _asset_path(name: str) -> Path:
    return Path(BASE_DIR) / "assets" / name


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("BarraUsoIA")
    app.setOrganizationName("BarraUsoIA")

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(
            None,
            "Barra de Uso de IA",
            "Bandeja do sistema indisponivel neste ambiente.",
        )
        return 1

    icon_file = _asset_path("icon.png")
    app_icon = QIcon(str(icon_file)) if icon_file.exists() else QIcon()
    app.setWindowIcon(app_icon)

    tray = SystemTray(app_icon)
    tray.start()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
