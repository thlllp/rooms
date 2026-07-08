import random

from backrooms.entity.entity import Entity, RenderOrder
from backrooms.procgen.spawner import spawn_from_table
from backrooms.world.game_map import GameMap
from backrooms.world.level_registry import SpawnEntry
from backrooms.world import tile_types


def _make_room_map() -> GameMap:
    """7x7 map, all wall except a 5x5 floor room in the middle (indices
    1..5). The room's center tile (3,3) has floor on all four orthogonal
    sides, so it's the one interior tile that is NOT wall-adjacent -- every
    other floor tile borders the wall ring."""
    game_map = GameMap(7, 7)
    for x in range(1, 6):
        for y in range(1, 6):
            game_map.tiles[x, y] = tile_types.FLOOR
    return game_map


def _spawn_marker() -> Entity:
    return Entity(0, 0, char="&", color=(0, 0, 0), name="Marker", render_order=RenderOrder.HAZARD)


def test_near_wall_entry_only_places_on_wall_adjacent_tiles():
    game_map = _make_room_map()
    rng = random.Random(0)
    table = (SpawnEntry(factory=_spawn_marker, weight=1.0, min_count=20, max_count=20, near_wall=True),)

    spawn_from_table(game_map, table, rng)

    placed = [(e.x, e.y) for e in game_map.entities]
    assert placed  # something got placed
    assert (3, 3) not in placed  # the one non-wall-adjacent floor tile
    for x, y in placed:
        neighbors = ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
        assert any(not game_map.is_walkable(nx, ny) for nx, ny in neighbors)
