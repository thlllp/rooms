"""Resolves a LevelDefinition's spawn_table/hazard_table onto a generated map.

Both tables share the same SpawnEntry shape, so one resolver handles both --
callers just pass the table they want placed.
"""

from __future__ import annotations

import random

from backrooms.world.game_map import GameMap
from backrooms.world.level_registry import SpawnEntry


def _random_walkable_tile(game_map: GameMap, rng: random.Random) -> tuple[int, int] | None:
    walkable_coords = [
        (x, y)
        for x in range(game_map.width)
        for y in range(game_map.height)
        if game_map.tiles["walkable"][x, y]
    ]
    if not walkable_coords:
        return None
    return rng.choice(walkable_coords)


def spawn_from_table(game_map: GameMap, table: tuple[SpawnEntry, ...], rng: random.Random) -> None:
    for entry in table:
        count = rng.randint(entry.min_count, entry.max_count)
        for _ in range(count):
            if rng.random() > entry.weight:
                continue
            tile = _random_walkable_tile(game_map, rng)
            if tile is None:
                continue
            entity = entry.factory()
            entity.place(*tile)
            game_map.entities.add(entity)
