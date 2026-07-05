"""Level 0-style generator: rectangular rooms ("cubicles") joined by
L-shaped corridors -- the sterile, repetitive office-maze read.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from backrooms.constants import Color
from backrooms.entity.entity import Entity, RenderOrder
from backrooms.world import tile_types
from backrooms.world.game_map import GameMap
from backrooms.world.level_registry import LEVEL_STYLES, LevelKind

if TYPE_CHECKING:
    import random

    from backrooms.world.level_registry import GenerationContext

MAX_ROOMS = 42
# fill_screen styles try this many placement attempts instead -- bigger rooms
# reject more often as the map fills up, so packing it densely needs a much
# larger attempt budget than a normal cubicle maze does.
MAX_ROOMS_FILL_SCREEN = 400

# How many placements to try before giving up on getting an edge-touching
# room on a given wall (see _force_edge_room).
EDGE_ROOM_ATTEMPTS = 30

# Fraction of tunnels that get widened to two tiles instead of one -- keeps
# most hallways the original cramped width while still giving a few of them
# the wider, more "hallway-like" read.
DOUBLE_WIDE_HALLWAY_CHANCE = 0.3

# A room only gets an interior column if both its outer dimensions meet this --
# keeps columns to the handful of biggest rooms, not every room.
LARGE_ROOM_MIN_DIM = 7


class RectangularRoom:
    def __init__(self, x: int, y: int, width: int, height: int) -> None:
        self.x1, self.y1 = x, y
        self.x2, self.y2 = x + width, y + height

    @property
    def center(self) -> tuple[int, int]:
        return (self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2

    def intersects(self, other: "RectangularRoom") -> bool:
        return self.x1 <= other.x2 and self.x2 >= other.x1 and self.y1 <= other.y2 and self.y2 >= other.y1


def _draw_segment(
    game_map: GameMap, x1: int, y1: int, x2: int, y2: int, *, double_wide: bool, floor_tile: np.ndarray
) -> None:
    """One straight leg of an L-shaped tunnel. When `double_wide`, also
    carves the adjacent parallel row/column so the corridor reads as two
    tiles wide instead of one -- the offset direction is picked to stay off
    the map's outer wall regardless of which edge the segment runs along."""
    for x, y in _line(x1, y1, x2, y2):
        game_map.tiles[x, y] = floor_tile

    if not double_wide:
        return

    if x1 == x2:  # vertical segment -- widen sideways along x
        offset_x = x1 + 1 if x1 + 1 <= game_map.width - 2 else x1 - 1
        for _, y in _line(x1, y1, x2, y2):
            game_map.tiles[offset_x, y] = floor_tile
    else:  # horizontal segment -- widen sideways along y
        offset_y = y1 + 1 if y1 + 1 <= game_map.height - 2 else y1 - 1
        for x, _ in _line(x1, y1, x2, y2):
            game_map.tiles[x, offset_y] = floor_tile


def _tunnel_between(
    game_map: GameMap,
    start: tuple[int, int],
    end: tuple[int, int],
    rng: "random.Random",
    *,
    double_wide: bool = False,
    floor_tile: np.ndarray,
) -> None:
    x1, y1 = start
    x2, y2 = end
    corner = (x2, y1) if rng.random() < 0.5 else (x1, y2)

    _draw_segment(game_map, x1, y1, corner[0], corner[1], double_wide=double_wide, floor_tile=floor_tile)
    _draw_segment(game_map, corner[0], corner[1], x2, y2, double_wide=double_wide, floor_tile=floor_tile)


def _line(x1: int, y1: int, x2: int, y2: int) -> list[tuple[int, int]]:
    points = []
    if x1 == x2:
        lo, hi = sorted((y1, y2))
        points.extend((x1, y) for y in range(lo, hi + 1))
    else:
        lo, hi = sorted((x1, x2))
        points.extend((x, y1) for x in range(lo, hi + 1))
    return points


def _make_column() -> Entity:
    return Entity(
        0,
        0,
        char="0",
        color=Color.COLUMN,
        name="Column",
        blocks_movement=True,
        blocks_sight=True,
        render_order=RenderOrder.HAZARD,
    )


def _place_columns(
    game_map: GameMap, rooms: list[RectangularRoom], *, exclude: tuple[int, int] | None, column_spacing: int | None
) -> None:
    """Large rooms get columns -- big enough that a single centered one is
    still trivially walkable all the way around (see LARGE_ROOM_MIN_DIM), so
    this can't disconnect the room the way it might in a cramped one; a
    scattered grid of single-tile columns (spaced `column_spacing` tiles
    apart) can't disconnect one either, since a diagonal step around any of
    them is always legal (allows_diagonal_step only looks at tile
    walkability, never at entities). `exclude` additionally skips whichever
    position got the stairway, so a column can't spawn on top of it and
    block the only way to reach it."""
    for room in rooms:
        if room.x2 - room.x1 < LARGE_ROOM_MIN_DIM or room.y2 - room.y1 < LARGE_ROOM_MIN_DIM:
            continue

        if column_spacing is None:
            positions = [room.center]
        else:
            positions = [
                (x, y)
                for x in range(room.x1 + 2, room.x2 - 1, column_spacing)
                for y in range(room.y1 + 2, room.y2 - 1, column_spacing)
            ]

        for pos in positions:
            if pos == game_map.spawn_point or pos == exclude:
                continue
            column = _make_column()
            column.place(*pos)
            game_map.entities.add(column)


def _room_wall_perimeter(game_map: GameMap, room: RectangularRoom) -> list[tuple[int, int]]:
    """A room's four wall edges, corners excluded, filtered down to cells
    still actually solid wall (a tunnel may have already carved through one
    of them to connect this room to the corridor network) -- candidates for
    embedding a door directly into the wall rather than in the open floor.
    Checks walkability rather than a specific tile_id so this works
    regardless of which wall/floor tile theme a level uses (see
    LevelDefinition.wall_tile/floor_tile). in_bounds-filtered first: a
    uses_edge_exit room is allowed to touch the map's true boundary (see
    _carve_room), so room.x2/y2 can legitimately equal game_map.width/height
    -- one past the last valid index -- with no wall tile out there to check.
    """
    cells = [(x, room.y1) for x in range(room.x1 + 1, room.x2)]
    cells += [(x, room.y2) for x in range(room.x1 + 1, room.x2)]
    cells += [(room.x1, y) for y in range(room.y1 + 1, room.y2)]
    cells += [(room.x2, y) for y in range(room.y1 + 1, room.y2)]
    return [(x, y) for x, y in cells if game_map.in_bounds(x, y) and not game_map.tiles["walkable"][x, y]]


def _place_exit_feature(
    game_map: GameMap, rooms: list[RectangularRoom], rng: "random.Random", *, door_chance: float
) -> tuple[int, int] | None:
    """Puts the level's single stepped-on exit feature in whichever room is
    farthest from spawn, so reaching it means actually crossing the level.
    With `door_chance` probability it's a door embedded in that room's wall
    instead of the usual stairs standing in the open floor -- functionally
    identical (see TriggerKind.FEATURE_STEPPED_ON), just a different tile_id
    and placement for flavor. Returns the stairs position specifically (for
    the caller to keep a column from covering it); doors need no such
    exclusion since columns only ever spawn at room centers. Returns None in
    the degenerate single-room case, where every room center is spawn."""
    if len(rooms) < 2:
        return None
    spawn_x, spawn_y = game_map.spawn_point
    farthest = max(rooms, key=lambda r: (r.center[0] - spawn_x) ** 2 + (r.center[1] - spawn_y) ** 2)

    if rng.random() < door_chance:
        wall_cells = _room_wall_perimeter(game_map, farthest)
        if wall_cells:
            x, y = rng.choice(wall_cells)
            game_map.tiles[x, y] = tile_types.DOOR_EXIT
            return None

    x, y = farthest.center
    game_map.tiles[x, y] = tile_types.STAIRS_DOWN
    return x, y


def _place_settlement_door(
    game_map: GameMap, rooms: list[RectangularRoom], rng: "random.Random", *, chance: float
) -> None:
    """Independent of the level's normal exit feature (stairs/door, or the
    map-edge for uses_edge_exit levels) -- a settlement is a bonus find, not
    the way forward, so it doesn't compete with or replace either. Picks any
    room with a spare wall cell and embeds a settlement door there; records
    the position on game_map for Engine._generate_map to drop a Sign next to
    it (generators only build tiles here, entities are placed separately)."""
    if not rooms or rng.random() >= chance:
        return
    candidates = list(rooms)
    rng.shuffle(candidates)
    for room in candidates:
        wall_cells = _room_wall_perimeter(game_map, room)
        if wall_cells:
            x, y = rng.choice(wall_cells)
            game_map.tiles[x, y] = tile_types.SETTLEMENT_DOOR
            game_map.settlement_door_position = (x, y)
            return


def _carve_room(game_map: GameMap, room: RectangularRoom, floor_tile: np.ndarray) -> None:
    """Reserves this room's own wall on a side as usual (starts one tile in
    from x1/y1) -- except on a side touching the map's true boundary (x1 or
    y1 == 0), where there's nothing to reserve: the world edge itself is the
    boundary, so floor extends all the way to it (see uses_edge_exit)."""
    inner_x_start = room.x1 if room.x1 == 0 else room.x1 + 1
    inner_y_start = room.y1 if room.y1 == 0 else room.y1 + 1
    game_map.tiles[inner_x_start : room.x2, inner_y_start : room.y2] = floor_tile


def _force_edge_room(
    game_map: GameMap,
    rooms: list[RectangularRoom],
    rng: "random.Random",
    *,
    wall: str,
    room_min_size: int,
    room_max_size: int,
    floor_tile: np.ndarray,
) -> RectangularRoom | None:
    """Tries EDGE_ROOM_ATTEMPTS placements of a room touching `wall`, for
    uses_edge_exit levels that want at least one exit opening per wall
    rather than leaving edge-touching entirely to chance (normal room
    placement already sometimes reaches an edge; this backfills whichever
    walls it missed). Returns the placed room (carved, not yet
    tunnel-connected -- the caller does that), or None if no
    non-overlapping placement was found."""
    for _ in range(EDGE_ROOM_ATTEMPTS):
        room_width = rng.randint(room_min_size, room_max_size)
        room_height = rng.randint(room_min_size, room_max_size)
        if wall == "left":
            x, y = 0, rng.randint(0, game_map.height - room_height)
        elif wall == "right":
            x, y = game_map.width - room_width, rng.randint(0, game_map.height - room_height)
        elif wall == "top":
            x, y = rng.randint(0, game_map.width - room_width), 0
        else:
            x, y = rng.randint(0, game_map.width - room_width), game_map.height - room_height

        candidate = RectangularRoom(x, y, room_width, room_height)
        if any(candidate.intersects(other) for other in rooms):
            continue

        _carve_room(game_map, candidate, floor_tile)
        return candidate

    return None


def generate_office_level(ctx: "GenerationContext") -> GameMap:
    # Reskin knob plus the level's structural "kind", read from the registry
    # entry driving this generation -- ctx.level_def is None only in
    # generator-isolation tests (see tests/test_procgen_determinism.py),
    # where INDOOR (matching every pre-existing level's prior behavior)
    # applies instead.
    if ctx.level_def is not None:
        door_chance = ctx.level_def.door_exit_chance
        settlement_door_chance = ctx.level_def.settlement_door_chance
        wall_tile = ctx.level_def.wall_tile
        floor_tile = ctx.level_def.floor_tile
        style = LEVEL_STYLES[ctx.level_def.kind]
        max_rooms_override = ctx.level_def.max_rooms
    else:
        door_chance = 0.0
        settlement_door_chance = 0.0
        wall_tile = tile_types.WALL
        floor_tile = tile_types.FLOOR
        style = LEVEL_STYLES[LevelKind.INDOOR]
        max_rooms_override = None

    game_map = GameMap(ctx.width, ctx.height, wall_tile=wall_tile)
    rooms: list[RectangularRoom] = []

    if style.uses_edge_exit:
        # Placed first, on an otherwise-empty map, so each wall reliably
        # gets its own exit opening -- attempting this after the random fill
        # loop below (which can cover half the map or more) leaves these
        # rooms competing for scraps of leftover space and often failing
        # outright.
        for wall in ("left", "right", "top", "bottom"):
            anchor = _force_edge_room(
                game_map,
                rooms,
                ctx.rng,
                wall=wall,
                room_min_size=style.room_min_size,
                room_max_size=style.room_max_size,
                floor_tile=floor_tile,
            )
            if anchor is None:
                continue
            if rooms:
                _tunnel_between(game_map, rooms[-1].center, anchor.center, ctx.rng, floor_tile=floor_tile)
            else:
                game_map.spawn_point = anchor.center
            rooms.append(anchor)
            # Lets Engine.load_level place the player on the matching side
            # when entering this zone from its neighbor in that direction
            # (see LevelStability.STABLE / GameMap.edge_entry_points) --
            # a point actually AT the true boundary this room touches, not
            # just the room's center, so a further step in that direction
            # genuinely leaves the map again.
            if wall == "left":
                entry_point = (0, anchor.center[1])
            elif wall == "right":
                entry_point = (ctx.width - 1, anchor.center[1])
            elif wall == "top":
                entry_point = (anchor.center[0], 0)
            else:
                entry_point = (anchor.center[0], ctx.height - 1)
            game_map.edge_entry_points[wall] = entry_point

    if max_rooms_override is not None:
        max_attempts = max_rooms_override
    else:
        max_attempts = MAX_ROOMS_FILL_SCREEN if style.fill_screen else MAX_ROOMS
    for _ in range(max_attempts):
        room_width = ctx.rng.randint(style.room_min_size, style.room_max_size)
        room_height = ctx.rng.randint(style.room_min_size, style.room_max_size)
        if style.uses_edge_exit:
            # Rooms are allowed to touch the map's true boundary (x1/y1 as
            # low as 0, x2/y2 as high as ctx.width/ctx.height) instead of
            # always leaving a 1-tile margin -- otherwise no floor tile is
            # ever adjacent to the actual coordinate boundary, and
            # MovementAction._handle_edge's out-of-bounds check can never
            # fire no matter how far the player walks.
            x = ctx.rng.randint(0, ctx.width - room_width)
            y = ctx.rng.randint(0, ctx.height - room_height)
        else:
            x = ctx.rng.randint(1, ctx.width - room_width - 2)
            y = ctx.rng.randint(1, ctx.height - room_height - 2)

        new_room = RectangularRoom(x, y, room_width, room_height)
        if any(new_room.intersects(other) for other in rooms):
            continue

        _carve_room(game_map, new_room, floor_tile)

        if rooms:
            double_wide = ctx.rng.random() < DOUBLE_WIDE_HALLWAY_CHANCE
            _tunnel_between(
                game_map, rooms[-1].center, new_room.center, ctx.rng, double_wide=double_wide, floor_tile=floor_tile
            )
        else:
            game_map.spawn_point = new_room.center

        rooms.append(new_room)

    # Levels that use the map-edge exit skip the usual floor-standing exit
    # tile entirely instead of placing one nobody's meant to use.
    stairs_position = (
        None if style.uses_edge_exit else _place_exit_feature(game_map, rooms, ctx.rng, door_chance=door_chance)
    )
    _place_settlement_door(game_map, rooms, ctx.rng, chance=settlement_door_chance)
    _place_columns(game_map, rooms, exclude=stairs_position, column_spacing=style.column_spacing)
    return game_map
