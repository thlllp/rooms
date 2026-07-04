from __future__ import annotations

import tcod
import tcod.event

import backrooms.data.registrations  # noqa: F401  (side effect: populates LEVEL_REGISTRY)
from backrooms.constants import (
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TILE_HEIGHT,
    TILE_WIDTH,
    TILESET_PATH,
    Color,
    WINDOW_TITLE,
)
from backrooms.engine import Engine
from backrooms.entity.components.light_source import LightSourceComponent
from backrooms.entity.components.sanity import SanityComponent
from backrooms.entity.entity import Entity, RenderOrder
from backrooms.input_handlers import EventHandler
from backrooms.rendering.renderer import render_all


def main() -> None:
    player = Entity(
        0,
        0,
        char="@",
        color=Color.PLAYER,
        name="Player",
        blocks_movement=True,
        render_order=RenderOrder.PLAYER,
        sanity=SanityComponent(max_sanity=100),
        light_source=LightSourceComponent(max_fuel=300.0, radius=6, burn_rate=1.0),
    )
    engine = Engine(player=player)
    event_handler = EventHandler(actor=player)

    tileset = tcod.tileset.load_truetype_font(str(TILESET_PATH), TILE_WIDTH, TILE_HEIGHT)
    with tcod.context.new(
        columns=SCREEN_WIDTH,
        rows=SCREEN_HEIGHT,
        tileset=tileset,
        title=WINDOW_TITLE,
    ) as context:
        console = context.new_console(order="F")
        while True:
            render_all(console, engine)
            context.present(console)

            for event in tcod.event.wait():
                action = event_handler.dispatch(event)
                if action is None:
                    continue
                action.perform(engine)
                engine.advance_turn()


if __name__ == "__main__":
    main()
