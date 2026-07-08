import random

from backrooms.data.registrations import LEVEL_1_22
from backrooms.procgen.spawner import spawn_from_table
from backrooms.world.level_registry import GenerationContext


def test_level_1_22_debris_never_shares_a_tile_with_a_heater():
    """spawn_from_table excludes any tile already holding an entity (see
    spawner._random_walkable_tile/_random_wall_adjacent_tile), regardless of
    which SpawnEntry runs first -- so heaters and debris piles can never
    land on the same tile. Run across many seeds/level regenerations to
    guard against a future change (e.g. reordering hazard_table, or a
    debris factory that bypasses the shared exclusion) reintroducing an
    overlap."""
    for seed in range(300):
        rng = random.Random(seed)
        ctx = GenerationContext(rng=rng, level_def=LEVEL_1_22, width=40, height=25)
        game_map = LEVEL_1_22.generator(ctx)
        spawn_from_table(game_map, LEVEL_1_22.hazard_table, rng)

        heater_tiles = {(e.x, e.y) for e in game_map.entities if e.name == "Combusting Heater"}
        debris_tiles = {(e.x, e.y) for e in game_map.entities if "Debris" in e.name}

        assert not (heater_tiles & debris_tiles), f"seed {seed}: debris overlapped a heater"
