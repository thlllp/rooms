"""Applies XP gains and, on level-up, the actual stat bumps -- kept separate
from ExperienceComponent so leveling can touch Fighter/PerceptionComponent
without those components needing to know about each other."""

from __future__ import annotations

from typing import TYPE_CHECKING

from backrooms.constants import Color
from backrooms.entity.components.attributes import (
    endurance_mitigation_from_endurance,
    max_hp_from_endurance,
    power_from_strength,
)

if TYPE_CHECKING:
    from backrooms.engine import Engine

# When the player HAS an AttributesComponent (true today -- see
# data/player_classes.py's build_player), leveling grows the underlying
# attribute and re-derives Fighter's fields from it via the same functions
# build_player uses, via attributes.max_hp_from_endurance/power_from_strength
# -- rather than bumping Fighter directly -- so the character screen's raw
# Endurance/Strength numbers never fall out of step with the HP/Power they're
# shown next to. Chosen so the *net* per-level growth matches exactly what
# this module hardcoded before AttributesComponent existed: +1 endurance ->
# +4 max_hp (HP_PER_ENDURANCE=4); +5 strength -> +1 power (strength // 5).
ENDURANCE_PER_LEVEL = 1
STRENGTH_PER_LEVEL = 5

# Fallback for an entity with a Fighter but no AttributesComponent (no
# player-facing entity lacks one today, but this function shouldn't assume
# the combination without checking) -- the flat bumps this module used
# before AttributesComponent existed.
LEVEL_UP_HP_BONUS = 4
LEVEL_UP_POWER_BONUS = 1
LEVEL_UP_PERCEPTION_BONUS = 1


def award_xp(engine: "Engine", amount: int) -> None:
    player = engine.player
    if player.experience is None or amount <= 0:
        return

    levels_gained = player.experience.gain_xp(amount)
    for _ in range(levels_gained):
        _apply_level_up(engine)


def _apply_level_up(engine: "Engine") -> None:
    player = engine.player

    if player.fighter is not None:
        if player.attributes is not None:
            player.attributes.endurance += ENDURANCE_PER_LEVEL
            player.attributes.strength += STRENGTH_PER_LEVEL
            player.fighter.max_hp = max_hp_from_endurance(player.attributes.endurance)
            player.fighter.endurance = endurance_mitigation_from_endurance(player.attributes.endurance)
            player.fighter.power = power_from_strength(player.attributes.strength)
        else:
            player.fighter.max_hp += LEVEL_UP_HP_BONUS
            player.fighter.power += LEVEL_UP_POWER_BONUS
        player.fighter.hp = player.fighter.max_hp

    if player.perception is not None:
        player.perception.acuity += LEVEL_UP_PERCEPTION_BONUS

    engine.message_log.add_message(
        f"You feel sharper. (Level {player.experience.level})", color=Color.WARNING
    )
