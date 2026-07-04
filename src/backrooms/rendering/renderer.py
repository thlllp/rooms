from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from backrooms.constants import UI_PANEL_HEIGHT
from backrooms.rendering import ui
from backrooms.systems.hallucination_system import apply_visual_distortion
from backrooms.world.tile_types import SHROUD

if TYPE_CHECKING:
    import tcod.console

    from backrooms.engine import Engine


def render_map(console: "tcod.console.Console", engine: "Engine") -> None:
    game_map = engine.game_map
    console.rgb[0 : game_map.width, 0 : game_map.height] = np.select(
        condlist=[game_map.visible, game_map.explored],
        choicelist=[game_map.tiles["light"], game_map.tiles["dark"]],
        default=SHROUD,
    )


def render_entities(console: "tcod.console.Console", engine: "Engine") -> None:
    game_map = engine.game_map
    visible_entities = [e for e in game_map.entities if game_map.visible[e.x, e.y]]
    for entity in sorted(visible_entities, key=lambda e: e.render_order):
        console.print(entity.x, entity.y, entity.char, fg=entity.color)


def render_all(console: "tcod.console.Console", engine: "Engine") -> None:
    render_map(console, engine)
    render_entities(console, engine)
    apply_visual_distortion(console, engine)
    ui.render_ui(console, engine, panel_height=UI_PANEL_HEIGHT)
