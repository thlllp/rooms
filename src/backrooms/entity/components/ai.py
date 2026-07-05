from __future__ import annotations

from typing import TYPE_CHECKING

from backrooms.actions import AttackAction
from backrooms.entity.components.base_component import BaseComponent
from backrooms.geometry import chebyshev_distance

if TYPE_CHECKING:
    from backrooms.engine import Engine
    from backrooms.entity.entity import Entity


class BaseAI(BaseComponent):
    def perform(self, engine: "Engine") -> None:
        raise NotImplementedError


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


RANDOM_STEPS = ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1), (0, 0))


def _attempt_step(engine: "Engine", entity: "Entity", dx: int, dy: int) -> None:
    """Shared by every AI: same walkability/corner-cut/blocking checks
    MovementAction applies to the player, so AI can't cheat through a wall
    or a corner the player couldn't."""
    if dx == 0 and dy == 0:
        return
    game_map = engine.game_map
    dest_x, dest_y = entity.x + dx, entity.y + dy
    if not game_map.is_walkable(dest_x, dest_y):
        return
    if not game_map.allows_diagonal_step(entity.x, entity.y, dx, dy):
        return
    if game_map.get_blocking_entity_at(dest_x, dest_y) is not None:
        return
    entity.move(dx, dy)


class WanderingAI(BaseAI):
    """Non-hostile: drifts toward a lit player within perception range
    (curious, not predatory), otherwise takes a random step. Never attacks --
    Fighter stays present but unused this milestone."""

    def __init__(self, *, perception_radius: int = 8) -> None:
        self.perception_radius = perception_radius

    def perform(self, engine: "Engine") -> None:
        entity = self.entity
        player = engine.player
        light = player.light_source
        player_is_lit = light is not None and light.is_lit and light.fuel > 0

        if player_is_lit and entity.distance_to(player.x, player.y) <= self.perception_radius:
            dx = _sign(player.x - entity.x)
            dy = _sign(player.y - entity.y)
        else:
            dx, dy = engine.rng.choice(RANDOM_STEPS)

        _attempt_step(engine, entity, dx, dy)


class HostileAI(BaseAI):
    """Hunts the player within perception_radius regardless of light (unlike
    WanderingAI's light-gated curiosity), and bump-attacks via AttackAction
    once adjacent instead of moving into them."""

    def __init__(self, *, perception_radius: int = 8) -> None:
        self.perception_radius = perception_radius

    def perform(self, engine: "Engine") -> None:
        entity = self.entity
        player = engine.player

        if entity.distance_to(player.x, player.y) > self.perception_radius:
            _attempt_step(engine, entity, *engine.rng.choice(RANDOM_STEPS))
            return

        dx = _sign(player.x - entity.x)
        dy = _sign(player.y - entity.y)
        is_adjacent = chebyshev_distance(player.x, player.y, entity.x, entity.y) <= 1

        if is_adjacent:
            # AttackAction itself checks allows_diagonal_step now, so if the
            # only path is a blocked corner this just quietly does nothing
            # this turn rather than attacking illegally.
            AttackAction(entity, dx, dy).perform(engine)
        else:
            _attempt_step(engine, entity, dx, dy)
