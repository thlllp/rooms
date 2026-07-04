"""Evaluates each level's TransitionRules every turn and performs the
"noclip" when one fires: regenerate the destination map, reposition the
player, log the flavor message. This is the only place level transitions
happen -- hazards and sanity feed into it via TransitionContext, they never
trigger a transition directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backrooms.constants import Color
from backrooms.world.level_registry import LEVEL_REGISTRY, TransitionContext

if TYPE_CHECKING:
    from backrooms.engine import Engine


def evaluate_transitions(engine: "Engine") -> bool:
    """Returns True if a noclip occurred this turn."""
    level_def = LEVEL_REGISTRY[engine.current_level_id]
    if not level_def.transition_rules:
        return False

    player = engine.player
    ctx = TransitionContext(
        player_sanity=int(player.sanity.current) if player.sanity is not None else 100,
        turns_in_level=engine.turns_in_level,
        event_flags=engine.event_flags,
        tile_under_player_id=engine.game_map.tile_id_at(player.x, player.y),
        rng=engine.rng,
    )

    for rule in level_def.transition_rules:
        if rule.is_satisfied(ctx):
            destination_id = rule.pick_destination(engine.rng)
            _perform_noclip(engine, destination_id, rule.message)
            return True

    return False


def _perform_noclip(engine: "Engine", destination_id: str, message: str) -> None:
    if message:
        engine.message_log.add_message(message, color=Color.NOCLIP_FLAVOR)
    engine.load_level(destination_id)
