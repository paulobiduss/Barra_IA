"""
formatters.py - UsageSnapshot -> texto para tooltip e itens de menu.

Camada pura (sem Qt): facil de testar e reutilizar. Decide como apresentar
numeros, percentuais, tempo ate o reset e mensagens de erro/estado.
"""

from __future__ import annotations

from datetime import datetime, timezone

from core.models import UsageSnapshot, UsageState


def _fmt_number(value: float) -> str:
    """Inteiro sem casas; demais com ate 1 casa."""
    if float(value).is_integer():
        return f"{int(value)}"
    return f"{value:.1f}"


def _fmt_bar(percent: float, width: int = 5) -> str:
    """Barra visual de consumo em blocos Unicode (ex.: '[#####.....]').

    Usa blocos cheios/vazios para representar o percentual; clampa em [0,100]
    para suportar provedores que ocasionalmente devolvem valores fora do
    intervalo (ex.: estouro momentaneo de cota).
    """
    pct = max(0.0, min(100.0, float(percent)))
    filled = int(round(pct / 100.0 * width))
    return "[" + ("━" * filled) + ("─" * (width - filled)) + "]"


def _fmt_reset(reset_at: datetime) -> str:
    """Tempo restante ate o reset, em formato curto (ex.: 'reset em 3h')."""
    now = datetime.now(tz=reset_at.tzinfo or timezone.utc)
    delta = reset_at - now
    total_minutes = int(delta.total_seconds() // 60)
    if total_minutes <= 0:
        return "reset agora"
    hours, minutes = divmod(total_minutes, 60)
    if hours >= 24:
        days = hours // 24
        return f"reset em {days}d"
    if hours > 0:
        return f"reset em {hours}h"
    return f"reset em {minutes}min"


def format_usage_line(snapshot: UsageSnapshot) -> str:
    """Linha unica para um provider, ex.:
    'Claude: 120/500 (24%) - reset em 3h' ou 'Claude: sem conexao'.
    """
    if snapshot.state is not UsageState.OK:
        return f"{snapshot.provider}: {snapshot.message or snapshot.state.value}"

    parts: list[str] = []
    if snapshot.percent is not None:
        parts.append(_fmt_bar(snapshot.percent))
    if snapshot.used is not None and snapshot.limit is not None:
        parts.append(f"{_fmt_number(snapshot.used)}/{_fmt_number(snapshot.limit)}")
    elif snapshot.used is not None:
        parts.append(_fmt_number(snapshot.used))

    if snapshot.percent is not None:
        parts.append(f"({_fmt_number(snapshot.percent)}%)")

    detail = " ".join(parts) if parts else "uso indisponivel"

    if snapshot.reset_at is not None:
        detail = f"{detail} - {_fmt_reset(snapshot.reset_at)}"

    # Snapshots OK normalmente nao tem message; quando tem (ex.: dado de cache
    # reaproveitado em falha temporaria), anexamos a nota.
    if snapshot.message:
        detail = f"{detail} {snapshot.message}"

    return f"{snapshot.provider}: {detail}"


# Aliases publicos para reuso pelo widget grafico do menu (ui/usage_menu_item.py).
# Mantemos os nomes privados em uso interno e nos testes existentes.
fmt_number = _fmt_number
fmt_reset = _fmt_reset


def format_tooltip(snapshots: list[UsageSnapshot]) -> str:
    """Tooltip multilinha com o titulo do app e uma linha por provider."""
    lines = ["Barra de Uso de IA"]
    lines.extend(format_usage_line(s) for s in snapshots)
    return "\n".join(lines)
