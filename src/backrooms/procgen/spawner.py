"""Resolves a LevelDefinition's spawn_table/hazard_table onto a generated map.

Both tables share the same SpawnEntry shape, so one resolver handles both --
callers just pass the table they want placed.
"""

from __future__ import annotations

import random

from backrooms.world.game_map import GameMap
from backrooms.world.level_registry import SpawnEntry


def _random_walkable_tile(game_map: GameMap, rng: random.Random) -> tuple[int, int] | None:
    """Excludes tiles ANY entity already occupies -- not just a blocking one
    (a column, an already-placed monster), but also non-blocking ones like a
    hazard or item, since a later table's spawn (e.g. furniture_table
    resolved after hazard_table -- see Engine._generate_map) could otherwise
    land a blocking piece of furniture directly on top of a debris pile or
    spore cloud, permanently sealing it off even though neither entity would
    have objected to sharing that tile individually. Checked fresh against
    game_map.entities on every call, so later spawns in the same pass, or a
    later table's call, always see everything already placed."""
    walkable_coords = [
        (x, y)
        for x in range(game_map.width)
        for y in range(game_map.height)
        if game_map.tiles["walkable"][x, y] and not any(game_map.entities_at(x, y))
    ]
    if not walkable_coords:
        return None
    return rng.choice(walkable_coords)


def random_walkable_tile_near(
    game_map: GameMap, rng: random.Random, center: tuple[int, int], radius: int, *, exclude: tuple[int, int] | None = None
) -> tuple[int, int] | None:
    """Same exclusions as _random_walkable_tile, restricted to a box around
    `center` -- falls back to None (never the unrestricted map) if nothing's
    free nearby, so a clustered entry either clusters or skips that instance
    rather than silently scattering it far from the rest of its group.
    `exclude` additionally rules out one specific tile (e.g. Engine._generate_map
    placing a Sign near a settlement door -- the door tile itself is walkable
    and would otherwise be a valid candidate, blocking the door)."""
    cx, cy = center
    candidates = [
        (x, y)
        for x in range(max(0, cx - radius), min(game_map.width, cx + radius + 1))
        for y in range(max(0, cy - radius), min(game_map.height, cy + radius + 1))
        if game_map.tiles["walkable"][x, y] and not any(game_map.entities_at(x, y)) and (x, y) != exclude
    ]
    if not candidates:
        return None
    return rng.choice(candidates)


def spawn_from_table(
    game_map: GameMap, table: tuple[SpawnEntry, ...], rng: random.Random, *, bonus_max: int = 0
) -> None:
    """`bonus_max` raises each entry's roll ceiling (not its floor) by that
    much -- callers pass a difficulty knob like Engine.level_repeat_streak
    so repeat visits *can* get busier without guaranteeing it every time."""
    for entry in table:
        count = rng.randint(entry.min_count, entry.max_count + bonus_max)
        anchor: tuple[int, int] | None = None
        for _ in range(count):
            if rng.random() > entry.weight:
                continue
            if entry.cluster_radius is not None and anchor is not None:
                tile = random_walkable_tile_near(game_map, rng, anchor, entry.cluster_radius)
            else:
                tile = _random_walkable_tile(game_map, rng)
            if tile is None:
                continue
            if anchor is None:
                anchor = tile
            entity = entry.factory()
            entity.place(*tile)
            game_map.entities.add(entity)
