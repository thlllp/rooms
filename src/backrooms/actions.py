from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backrooms.engine import Engine
    from backrooms.entity.entity import Entity


class Action:
    def __init__(self, entity: "Entity") -> None:
        self.entity = entity

    def perform(self, engine: "Engine") -> None:
        raise NotImplementedError


class EscapeAction(Action):
    def perform(self, engine: "Engine") -> None:
        raise SystemExit()


class WaitAction(Action):
    def perform(self, engine: "Engine") -> None:
        pass


class MovementAction(Action):
    def __init__(self, entity: "Entity", dx: int, dy: int) -> None:
        super().__init__(entity)
        self.dx = dx
        self.dy = dy

    def perform(self, engine: "Engine") -> None:
        dest_x = self.entity.x + self.dx
        dest_y = self.entity.y + self.dy
        game_map = engine.game_map

        if not game_map.is_walkable(dest_x, dest_y):
            return
        if not game_map.allows_diagonal_step(self.entity.x, self.entity.y, self.dx, self.dy):
            return
        if game_map.get_blocking_entity_at(dest_x, dest_y) is not None:
            return

        self.entity.move(self.dx, self.dy)
