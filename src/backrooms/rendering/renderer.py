from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from backrooms.constants import UI_PANEL_HEIGHT, Color
from backrooms.entity.components.hazard import SPORE_DAMAGE_KIND
from backrooms.geometry import tiles_in_chebyshev_radius
from backrooms.rendering import ui
from backrooms.systems.hallucination_system import apply_visual_distortion
from backrooms.world.tile_types import SHROUD

if TYPE_CHECKING:
    import tcod.console

    from backrooms.engine import Engine

SPORE_CORE_CHAR = "*"


def render_map(console: "tcod.console.Console", engine: "Engine") -> None:
    game_map = engine.game_map
    console.rgb[0 : game_map.width, 0 : game_map.height] = np.select(
        condlist=[game_map.visible, game_map.explored],
        choicelist=[game_map.tiles["light"], game_map.tiles["dark"]],
        default=SHROUD,
    )


def render_hazard_footprints(console: "tcod.console.Console", engine: "Engine") -> None:
    """Fills in the tiles a radius-based hazard actually affects (e.g. a
    spore cloud's full Chebyshev radius, not just its origin tile), using the
    hazard's own glyph/color. Drawn before render_entities so the entity's
    own tile -- rendered distinctly, see SPORE_CORE_CHAR -- draws on top."""
    game_map = engine.game_map
    for entity in game_map.entities:
        if entity.hazard is None or entity.hazard.kind != SPORE_DAMAGE_KIND:
            continue
        radius = entity.hazard.data.get("radius", 0)
        for dx, dy in tiles_in_chebyshev_radius(radius):
            x, y = entity.x + dx, entity.y + dy
            if game_map.in_bounds(x, y) and game_map.visible[x, y] and game_map.tiles["walkable"][x, y]:
                console.print(x, y, entity.char, fg=entity.color)


def render_entities(console: "tcod.console.Console", engine: "Engine") -> None:
    game_map = engine.game_map
    visible_entities = [e for e in game_map.entities if game_map.visible[e.x, e.y]]
    for entity in sorted(visible_entities, key=lambda e: e.render_order):
        if entity.hazard is not None and entity.hazard.kind == SPORE_DAMAGE_KIND:
            console.print(entity.x, entity.y, SPORE_CORE_CHAR, fg=Color.SPORE_CORE)
        else:
            console.print(entity.x, entity.y, entity.char, fg=entity.color)


def render_all(console: "tcod.console.Console", engine: "Engine") -> None:
    if engine.show_character_screen:
        ui.render_character_screen(console, engine)
        return
    if engine.show_inventory:
        ui.render_inventory_screen(console, engine)
        return
    if engine.show_barter:
        ui.render_barter_screen(console, engine)
        return

    render_map(console, engine)
    if engine.traveling:
        ui.render_travel_path(console, engine)
    render_hazard_footprints(console, engine)
    render_entities(console, engine)
    apply_visual_distortion(console, engine)
    ui.render_level_banner(console, engine)
    if engine.look_mode:
        ui.render_look_cursor(console, engine)
    ui.render_ui(console, engine, panel_height=UI_PANEL_HEIGHT)
