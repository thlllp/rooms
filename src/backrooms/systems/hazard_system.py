from __future__ import annotations

from typing import TYPE_CHECKING

from backrooms.entity.components.light_source import tick_light_fuel

if TYPE_CHECKING:
    from backrooms.engine import Engine


def process_hazards(engine: "Engine") -> None:
    if engine.player.light_source is not None:
        tick_light_fuel(engine.player, engine)

    for entity in list(engine.game_map.entities):
        # A hazard tick earlier in this same pass may have just killed the
        # player (e.g. two overlapping spore clouds) -- stop immediately
        # rather than re-damaging/re-draining a dead player.
        if engine.game_over:
            return
        if entity.hazard is not None:
            entity.hazard.tick(engine)
