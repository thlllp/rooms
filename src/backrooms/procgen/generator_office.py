"""Level 0-style generator: rectangular rooms ("cubicles") joined by
L-shaped corridors -- the sterile, repetitive office-maze read.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backrooms.world import tile_types
from backrooms.world.game_map import GameMap

if TYPE_CHECKING:
    import random

    from backrooms.world.level_registry import GenerationContext

MAX_ROOMS = 24
ROOM_MIN_SIZE = 4
ROOM_MAX_SIZE = 9


class RectangularRoom:
    def __init__(self, x: int, y: int, width: int, height: int) -> None:
        self.x1, self.y1 = x, y
        self.x2, self.y2 = x + width, y + height

    @property
    def center(self) -> tuple[int, int]:
        return (self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2

    @property
    def inner(self) -> tuple[slice, slice]:
        """The room's floor area, excluding its outer wall."""
        return slice(self.x1 + 1, self.x2), slice(self.y1 + 1, self.y2)

    def intersects(self, other: "RectangularRoom") -> bool:
        return self.x1 <= other.x2 and self.x2 >= other.x1 and self.y1 <= other.y2 and self.y2 >= other.y1


def _tunnel_between(
    game_map: GameMap, start: tuple[int, int], end: tuple[int, int], rng: "random.Random"
) -> None:
    x1, y1 = start
    x2, y2 = end
    corner = (x2, y1) if rng.random() < 0.5 else (x1, y2)

    for x, y in _line(x1, y1, corner[0], corner[1]):
        game_map.tiles[x, y] = tile_types.FLOOR
    for x, y in _line(corner[0], corner[1], x2, y2):
        game_map.tiles[x, y] = tile_types.FLOOR


def _line(x1: int, y1: int, x2: int, y2: int) -> list[tuple[int, int]]:
    points = []
    if x1 == x2:
        lo, hi = sorted((y1, y2))
        points.extend((x1, y) for y in range(lo, hi + 1))
    else:
        lo, hi = sorted((x1, x2))
        points.extend((x, y1) for x in range(lo, hi + 1))
    return points


def generate_office_level(ctx: "GenerationContext") -> GameMap:
    game_map = GameMap(ctx.width, ctx.height)
    rooms: list[RectangularRoom] = []

    for _ in range(MAX_ROOMS):
        room_width = ctx.rng.randint(ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        room_height = ctx.rng.randint(ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        x = ctx.rng.randint(1, ctx.width - room_width - 2)
        y = ctx.rng.randint(1, ctx.height - room_height - 2)

        new_room = RectangularRoom(x, y, room_width, room_height)
        if any(new_room.intersects(other) for other in rooms):
            continue

        game_map.tiles[new_room.inner] = tile_types.FLOOR

        if rooms:
            _tunnel_between(game_map, rooms[-1].center, new_room.center, ctx.rng)
        else:
            game_map.spawn_point = new_room.center

        rooms.append(new_room)

    return game_map
