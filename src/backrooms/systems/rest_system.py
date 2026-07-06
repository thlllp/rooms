"""Per-turn passive HP/hunger recovery while standing in an inn zone (see
tile_types.INN_FLOOR) -- the physical-recovery counterpart to
sanity_system's safe-zone restore, kept as its own module since it's a
different pair of stats with their own components/None-guards.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backrooms.world.tile_types import ZoneEffect

if TYPE_CHECKING:
    from backrooms.engine import Engine

INN_HP_RESTORE = 0.5
INN_HUNGER_RESTORE = 1.0


def process_rest(engine: "Engine") -> None:
    player = engine.player
    if not engine.game_map.has_zone_effect(player.x, player.y, ZoneEffect.INN):
        return
    if player.fighter is not None:
        player.fighter.heal(INN_HP_RESTORE)
    if player.hunger is not None:
        player.hunger.restore(INN_HUNGER_RESTORE)
