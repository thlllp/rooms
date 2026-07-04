from __future__ import annotations

from typing import TYPE_CHECKING

from backrooms.entity.components.base_component import BaseComponent

if TYPE_CHECKING:
    from backrooms.engine import Engine


class BaseAI(BaseComponent):
    def perform(self, engine: "Engine") -> None:
        raise NotImplementedError


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


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
            dx, dy = engine.rng.choice(
                [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1), (0, 0)]
            )

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
