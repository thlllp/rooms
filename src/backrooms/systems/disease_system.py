"""Per-turn disease contraction. Standing on a ZoneEffect.CONTAMINATED tile
(Level 1.11's pooled water, see world/tile_types.FLOODED_FLOOR) each turn risks
contracting the Hydrolitis Plague -- a small chance, lowered by the player's
endurance. The plague itself is just recorded on AfflictionsComponent for now;
its mechanical effects will be built on top of that later.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backrooms.constants import Color
from backrooms.entity.components.attributes import BASELINE_ATTRIBUTE, attribute_value
from backrooms.world.tile_types import ZoneEffect

if TYPE_CHECKING:
    from backrooms.engine import Engine

HYDROLITIS_PLAGUE = "Hydrolitis Plague"

# Per-turn contraction chance at baseline endurance. It scales inversely with
# endurance (BASELINE / endurance), so a tougher character shrugs the water off
# more often -- at baseline (5) it's this value, at double endurance it halves,
# at half endurance it doubles.
BASE_CONTRACT_CHANCE = 0.08


def process_diseases(engine: "Engine") -> None:
    player = engine.player
    if player.afflictions is None:
        return
    if not engine.game_map.has_zone_effect(player.x, player.y, ZoneEffect.CONTAMINATED):
        return
    if player.afflictions.has(HYDROLITIS_PLAGUE):
        return

    endurance = attribute_value(player, "endurance")
    chance = BASE_CONTRACT_CHANCE * (BASELINE_ATTRIBUTE / max(1, endurance))
    if engine.rng.random() < chance and player.afflictions.add(HYDROLITIS_PLAGUE):
        engine.message_log.add_message(
            "The foul water works into your skin -- you've caught the Hydrolitis Plague.",
            color=Color.HAZARD,
        )
