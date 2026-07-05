"""Second level flavor: an irregular, cave-like flooded sublevel, built with
cellular automata rather than rooms+corridors -- a deliberately different
silhouette from the office level's right angles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backrooms.world import tile_types
from backrooms.world.game_map import GameMap

if TYPE_CHECKING:
    from backrooms.world.level_registry import GenerationContext

INITIAL_FLOOR_CHANCE = 0.46
SMOOTHING_STEPS = 5
WALL_BIRTH_THRESHOLD = 5  # a wall cell becomes floor if it has fewer than this many wall neighbors


def _count_wall_neighbors(walls: list[list[bool]], x: int, y: int, width: int, height: int) -> int:
    count = 0
    for nx in range(x - 1, x + 2):
        for ny in range(y - 1, y + 2):
            if nx == x and ny == y:
                continue
            if not (0 <= nx < width and 0 <= ny < height):
                count += 1  # treat out-of-bounds as walls, keeps the map bordered
            elif walls[nx][ny]:
                count += 1
    return count


def _smooth(walls: list[list[bool]], width: int, height: int) -> list[list[bool]]:
    new_walls = [[True] * height for _ in range(width)]
    for x in range(width):
        for y in range(height):
            if x == 0 or y == 0 or x == width - 1 or y == height - 1:
                new_walls[x][y] = True
                continue
            neighbor_walls = _count_wall_neighbors(walls, x, y, width, height)
            new_walls[x][y] = neighbor_walls >= WALL_BIRTH_THRESHOLD
    return new_walls


def _largest_connected_floor(walls: list[list[bool]], width: int, height: int) -> set[tuple[int, int]]:
    seen: set[tuple[int, int]] = set()
    best: set[tuple[int, int]] = set()

    for x in range(width):
        for y in range(height):
            if walls[x][y] or (x, y) in seen:
                continue
            component: set[tuple[int, int]] = set()
            stack = [(x, y)]
            while stack:
                cx, cy = stack.pop()
                if (cx, cy) in component:
                    continue
                component.add((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < width and 0 <= ny < height and not walls[nx][ny] and (nx, ny) not in component:
                        stack.append((nx, ny))
            seen |= component
            if len(component) > len(best):
                best = component

    return best


def generate_flooded_level(ctx: "GenerationContext") -> GameMap:
    width, height = ctx.width, ctx.height
    walls = [
        [ctx.rng.random() >= INITIAL_FLOOR_CHANCE for _y in range(height)]
        for _x in range(width)
    ]

    for _ in range(SMOOTHING_STEPS):
        walls = _smooth(walls, width, height)

    floor_tiles = _largest_connected_floor(walls, width, height)

    game_map = GameMap(width, height)
    for x, y in floor_tiles:
        game_map.tiles[x, y] = tile_types.FLOOR

    game_map.spawn_point = next(iter(floor_tiles))

    if len(floor_tiles) >= 2:
        spawn_x, spawn_y = game_map.spawn_point
        stairs_x, stairs_y = max(floor_tiles, key=lambda t: (t[0] - spawn_x) ** 2 + (t[1] - spawn_y) ** 2)
        game_map.tiles[stairs_x, stairs_y] = tile_types.STAIRS_DOWN

    return game_map
