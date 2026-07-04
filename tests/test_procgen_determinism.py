import random
from collections import deque

import numpy as np
import pytest

from backrooms.procgen.generator_flooded import generate_flooded_level
from backrooms.procgen.generator_office import generate_office_level
from backrooms.world.game_map import GameMap
from backrooms.world.level_registry import GenerationContext

GENERATORS = [generate_office_level, generate_flooded_level]
WIDTH, HEIGHT = 40, 25


def _make_ctx(seed: int) -> GenerationContext:
    return GenerationContext(rng=random.Random(seed), level_def=None, width=WIDTH, height=HEIGHT)


def _reachable_count(game_map: GameMap) -> int:
    start = game_map.spawn_point
    seen = {start}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if game_map.is_walkable(nx, ny) and (nx, ny) not in seen:
                seen.add((nx, ny))
                queue.append((nx, ny))
    return len(seen)


@pytest.mark.parametrize("generator", GENERATORS)
def test_same_seed_produces_identical_map(generator):
    map_a = generator(_make_ctx(42))
    map_b = generator(_make_ctx(42))
    assert np.array_equal(map_a.tiles, map_b.tiles)


@pytest.mark.parametrize("generator", GENERATORS)
@pytest.mark.parametrize("seed", [1, 2, 3, 100])
def test_map_has_walkable_spawn_point(generator, seed):
    game_map = generator(_make_ctx(seed))
    assert game_map.is_walkable(*game_map.spawn_point)


@pytest.mark.parametrize("generator", GENERATORS)
@pytest.mark.parametrize("seed", [1, 2, 3, 100])
def test_map_is_fully_reachable_from_spawn(generator, seed):
    game_map = generator(_make_ctx(seed))
    total_walkable = int(game_map.tiles["walkable"].sum())
    assert _reachable_count(game_map) == total_walkable
