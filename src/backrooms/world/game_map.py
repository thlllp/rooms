from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

import numpy as np
import tcod.map

from backrooms.world import tile_types

if TYPE_CHECKING:
    from backrooms.entity.entity import Entity


class GameMap:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.tiles = np.full((width, height), fill_value=tile_types.WALL, order="F", dtype=tile_types.tile_dt)

        # visible: computed fresh every turn from the current FOV.
        # explored: sticky "remembered" mask, once True stays True.
        self.visible = np.full((width, height), fill_value=False, order="F")
        self.explored = np.full((width, height), fill_value=False, order="F")

        self.entities: set[Entity] = set()

        # Set by the procgen generator that builds this map; consumed by
        # perform_noclip() to place the player after a level transition.
        self.spawn_point: tuple[int, int] = (0, 0)

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_walkable(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and bool(self.tiles["walkable"][x, y])

    def allows_diagonal_step(self, x: int, y: int, dx: int, dy: int) -> bool:
        """False if both orthogonal tiles flanking a diagonal step are walls
        (corner-cutting is disallowed: a diagonal move needs at least one of
        its two flanking orthogonal tiles open)."""
        if dx == 0 or dy == 0:
            return True
        return self.is_walkable(x + dx, y) or self.is_walkable(x, y + dy)

    def tile_id_at(self, x: int, y: int) -> str | None:
        if not self.in_bounds(x, y):
            return None
        return str(self.tiles["tile_id"][x, y])

    def is_safe_zone_at(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and bool(self.tiles["is_safe_zone"][x, y])

    def get_blocking_entity_at(self, x: int, y: int) -> "Entity | None":
        for entity in self.entities:
            if entity.blocks_movement and entity.x == x and entity.y == y:
                return entity
        return None

    def entities_at(self, x: int, y: int) -> Iterable["Entity"]:
        return (e for e in self.entities if e.x == x and e.y == y)

    def compute_fov(self, pov: tuple[int, int], radius: int) -> None:
        self.visible = tcod.map.compute_fov(
            self.tiles["transparent"],
            pov=pov,
            radius=radius,
            light_walls=True,
        )
        self.explored |= self.visible
