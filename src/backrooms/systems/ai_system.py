from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backrooms.engine import Engine


def process_ai(engine: "Engine") -> None:
    for entity in list(engine.game_map.entities):
        if entity.ai is not None and entity is not engine.player:
            entity.ai.perform(engine)
