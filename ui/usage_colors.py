"""
usage_colors.py - Mapeamento de percentual de consumo -> cor da barra.

Camada pura (so depende de QColor, sem QApplication): facil de testar e
reutilizar. Quatro faixas inspiradas na UI do Claude Desktop: verde para baixo
consumo, amarelo/laranja para alerta progressivo, vermelho para limite quase
atingido.
"""

from __future__ import annotations

from PyQt6.QtGui import QColor


# Limiares (em %) que separam as faixas de cor.
THRESHOLD_YELLOW = 50.0
THRESHOLD_ORANGE = 80.0
THRESHOLD_RED = 95.0

# Paleta. Track escuro funciona em tema claro e escuro do Windows.
GREEN = "#3FB950"
YELLOW = "#D29922"
ORANGE = "#FB8500"
RED = "#F85149"
TRACK = "#2D2D30"


def color_for_percent(pct: float | None) -> QColor:
    """Retorna a cor do fill por faixa.

    `None` recai em verde (sem dado de consumo conhecido = nao alerta). Valores
    fora de [0, 100] sao tratados pelo clamp natural dos thresholds: negativos
    caem em verde; acima de 100 caem em vermelho.
    """
    if pct is None:
        return QColor(GREEN)
    if pct < THRESHOLD_YELLOW:
        return QColor(GREEN)
    if pct < THRESHOLD_ORANGE:
        return QColor(YELLOW)
    if pct < THRESHOLD_RED:
        return QColor(ORANGE)
    return QColor(RED)
