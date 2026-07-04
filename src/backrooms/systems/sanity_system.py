"""Per-turn sanity drain/restore. All drain sources are additive and each one
degrades gracefully to zero when its associated feature doesn't exist yet
(e.g. no light_source component until Step 5, no dread-flagged entities until
Step 6) -- this module doesn't need to change shape as those land.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backrooms.world.level_registry import LEVEL_REGISTRY

if TYPE_CHECKING:
    from backrooms.engine import Engine

# Flat drain applied whenever the player has no active, lit light source.
# Once Step 5 adds LightSourceComponent, a lit source suppresses this entirely.
UNLIT_DARKNESS_DRAIN = 0.3

DREAD_DRAIN_WEIGHT = 0.15  # per tile of (dread_radius - distance), per dreadful entity in range
REPEAT_LOOP_DRAIN = 0.2

SAFE_ZONE_RESTORE = 0.5


def _darkness_drain(engine: "Engine") -> float:
    player = engine.player
    light = player.light_source
    if light is not None and light.is_lit and light.fuel > 0:
        return 0.0
    level_def = LEVEL_REGISTRY[engine.current_level_id]
    return UNLIT_DARKNESS_DRAIN * level_def.darkness_factor


def _dread_proximity_drain(engine: "Engine") -> float:
    player = engine.player
    total = 0.0
    for entity in engine.game_map.entities:
        if not entity.causes_dread or entity is player:
            continue
        distance = player.distance_to(entity.x, entity.y)
        if distance <= entity.dread_radius:
            total += (entity.dread_radius - distance) * DREAD_DRAIN_WEIGHT
    return total


def _repeat_loop_drain(sanity) -> float:  # noqa: ANN001 -- SanityComponent, kept untyped to dodge import cycle noise
    return REPEAT_LOOP_DRAIN if sanity.is_pacing_in_loop() else 0.0


def process_sanity(engine: "Engine") -> None:
    player = engine.player
    if player.sanity is None:
        return

    sanity = player.sanity
    previous_band = sanity.band

    level_def = LEVEL_REGISTRY[engine.current_level_id]
    total_drain = level_def.ambient_sanity_drain
    total_drain += _darkness_drain(engine)
    total_drain += _dread_proximity_drain(engine)
    total_drain += _repeat_loop_drain(sanity)
    sanity.drain(total_drain)

    if engine.game_map.is_safe_zone_at(player.x, player.y):
        sanity.restore(SAFE_ZONE_RESTORE)

    sanity.record_position(player.x, player.y)

    new_band = sanity.band
    if new_band is not previous_band:
        engine.message_log.add_message(f"Your grip on this place shifts... ({new_band.name})")
