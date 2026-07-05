"""Peaceful NPC-to-NPC flavor interactions -- purely cosmetic (a log
message, nothing mechanical), gated entirely on LevelDefinition.isolation:
on an isolated level (the default -- see level_registry.LevelDefinition)
two dialogue-bearing NPCs never interact no matter how close they end up,
matching the Backrooms lore that the early levels never let two displaced
people actually find each other.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backrooms.constants import Color
from backrooms.geometry import chebyshev_distance
from backrooms.world.level_registry import LEVEL_REGISTRY

if TYPE_CHECKING:
    from backrooms.engine import Engine

INTERACTION_RADIUS = 2
INTERACTION_CHANCE = 0.05

INTERACTION_LINES = (
    "Two survivors trade a few quiet words you can't make out.",
    "You catch two figures nodding to each other before drifting apart.",
    "A stranger presses something into another's hands and moves on.",
)


def process_npc_social(engine: "Engine") -> None:
    if LEVEL_REGISTRY[engine.current_level_id].isolation:
        return

    colonists = [e for e in engine.game_map.entities if e.dialogue is not None]
    for i, a in enumerate(colonists):
        for b in colonists[i + 1 :]:
            if chebyshev_distance(a.x, a.y, b.x, b.y) > INTERACTION_RADIUS:
                continue
            if engine.rng.random() < INTERACTION_CHANCE:
                engine.message_log.add_message(engine.rng.choice(INTERACTION_LINES), color=Color.GREY)
                return  # at most one flavor line per turn
