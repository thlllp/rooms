"""Flavor dialogue for peaceful NPCs -- see actions.TalkAction. Same
"pool of lines, pick one" pattern as rendering/ui.py's TILE_DESCRIPTIONS,
just per-entity instead of per-tile: nothing branches on player choice yet,
this is the simple slice of the interaction framework to build on.
"""

from __future__ import annotations

import random

from backrooms.entity.components.base_component import BaseComponent


class DialogueComponent(BaseComponent):
    def __init__(self, lines: tuple[str, ...]) -> None:
        self.lines = lines

    def pick_line(self, rng: random.Random) -> str:
        return rng.choice(self.lines)
