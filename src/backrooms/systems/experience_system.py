"""Applies XP gains and, on level-up, the actual stat bumps -- kept separate
from ExperienceComponent so leveling can touch Fighter/PerceptionComponent
without those components needing to know about each other."""

from __future__ import annotations

from typing import TYPE_CHECKING

from backrooms.constants import Color

if TYPE_CHECKING:
    from backrooms.engine import Engine

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
        player.fighter.max_hp += LEVEL_UP_HP_BONUS
        player.fighter.hp = player.fighter.max_hp
        player.fighter.power += LEVEL_UP_POWER_BONUS

    if player.perception is not None:
        player.perception.acuity += LEVEL_UP_PERCEPTION_BONUS

    engine.message_log.add_message(
        f"You feel sharper. (Level {player.experience.level})", color=Color.WARNING
    )
