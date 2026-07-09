"""Per-turn disease contraction. Standing on a ZoneEffect.CONTAMINATED tile
(Level 1.11's pooled water, see world/tile_types.FLOODED_FLOOR) each turn risks
contracting the Hydrolitis Plague -- a small chance, lowered by the player's
endurance and, on ordinary ankle-deep water, cancelled outright by a worn
feet-slot item's flood_resistance (see the Wading Boots/
EquippableComponent.flood_resistance). ZoneEffect.DEEP_WATER (ankle-deep
water's rarer, deeper cousin -- see tile_types.FLOODED_FLOOR_DEEP) goes over
the top of any footwear, so flood_resistance is ignored there: no current
level actually places deep water yet, but the distinction is real the moment
one does. The plague itself is just recorded on AfflictionsComponent for
now; its mechanical effects will be built on top of that later.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backrooms.constants import Color
from backrooms.entity.components.attributes import BASELINE_ATTRIBUTE, attribute_value
from backrooms.entity.components.equipment import worn_slot_effect
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

    flood_resistance = worn_slot_effect(player, "feet", "flood_resistance")
    if engine.game_map.has_zone_effect(player.x, player.y, ZoneEffect.DEEP_WATER):
        # Deep water goes over the top of any footwear -- the boots' resistance
        # simply doesn't apply here (see the module docstring).
        flood_resistance = 0.0

    endurance = attribute_value(player, "endurance")
    chance = BASE_CONTRACT_CHANCE * (BASELINE_ATTRIBUTE / max(1, endurance)) * (1.0 - flood_resistance)
    if engine.rng.random() < chance and player.afflictions.add(HYDROLITIS_PLAGUE):
        engine.message_log.add_message(
            "The foul water works into your skin -- you've caught the Hydrolitis Plague.",
            color=Color.HAZARD,
        )
