from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backrooms.engine import Engine


def process_ai(engine: "Engine") -> None:
    for entity in list(engine.game_map.entities):
        # An entity earlier in this same pass may have just killed the
        # player (engine.kill_entity sets game_over) -- stop immediately
        # rather than letting further entities act against a dead player.
        if engine.game_over:
            return
        if entity.ai is not None and entity is not engine.player:
            entity.ai.perform(engine)
