from __future__ import annotations

from typing import TYPE_CHECKING

from backrooms.constants import Color

if TYPE_CHECKING:
    import tcod.console

    from backrooms.engine import Engine

SANITY_BAND_COLOR = {
    "normal": Color.SANITY_BAR_FULL,
    "mild": Color.WARNING,
    "severe": Color.SANITY_BAR_LOW,
    "critical": Color.HAZARD,
}


def render_message_log(console: "tcod.console.Console", engine: "Engine", *, x: int, y: int, height: int) -> None:
    for i, (text, color) in enumerate(engine.message_log.tail(height)):
        console.print(x, y + i, text, fg=color)


def render_sanity_bar(console: "tcod.console.Console", engine: "Engine", *, x: int, y: int, width: int) -> None:
    sanity = engine.player.sanity
    if sanity is None:
        return

    ratio = max(0.0, min(1.0, sanity.current / sanity.max_sanity))
    filled_width = round(width * ratio)
    bar_color = SANITY_BAND_COLOR[sanity.band.name]

    console.draw_rect(x=x, y=y, width=width, height=1, ch=ord(" "), bg=Color.SANITY_BAR_EMPTY)
    if filled_width > 0:
        console.draw_rect(x=x, y=y, width=filled_width, height=1, ch=ord(" "), bg=bar_color)

    label = f"SANITY {int(sanity.current)}/{int(sanity.max_sanity)}"
    console.print(x + 1, y, label, fg=Color.WHITE)


def render_ui(console: "tcod.console.Console", engine: "Engine", *, panel_height: int) -> None:
    map_height = console.height - panel_height
    console.draw_rect(x=0, y=map_height, width=console.width, height=panel_height, ch=ord(" "), bg=Color.BLACK)
    render_sanity_bar(console, engine, x=1, y=map_height, width=30)
    render_message_log(console, engine, x=1, y=map_height + 2, height=panel_height - 2)
