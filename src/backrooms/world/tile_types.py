"""Structured numpy dtypes for map tiles.

Mirrors the classic python-tcod tutorial pattern: a small "graphic" struct
(glyph + colors) nested twice inside a "tile" struct, once for how the tile
looks when merely remembered/explored ("dark") and once for how it looks
while actually lit and in FOV ("light").
"""

from __future__ import annotations

from enum import IntFlag, auto

import numpy as np

from backrooms.constants import Color

graphic_dt = np.dtype(
    [
        ("ch", np.int32),
        ("fg", "3B"),
        ("bg", "3B"),
    ]
)


class ZoneEffect(IntFlag):
    """Passive per-turn effects a tile can apply to whoever's standing on
    it -- one bitmask field on the tile struct instead of one bool field per
    effect, so a future third effect (or fourth, ...) is a new member here
    plus a system checking GameMap.has_zone_effect for it, not another
    dtype field/new_tile kwarg/GameMap accessor to hand-wire through the
    whole stack again."""

    NONE = 0
    # Sanity actively recovers here (see systems/sanity_system.py's
    # SAFE_ZONE_RESTORE).
    SAFE = auto()
    # HP and hunger also recover here (see systems/rest_system.py).
    INN = auto()


tile_dt = np.dtype(
    [
        ("walkable", np.bool_),
        ("transparent", np.bool_),
        ("zone_effects", np.uint8),
        ("tile_id", "U20"),  # stable identifier for FEATURE_STEPPED_ON transition rules
        ("dark", graphic_dt),
        ("light", graphic_dt),
    ]
)


def new_tile(
    *,
    walkable: int,
    transparent: int,
    dark: tuple[int, tuple[int, int, int], tuple[int, int, int]],
    light: tuple[int, tuple[int, int, int], tuple[int, int, int]],
    zone_effects: ZoneEffect = ZoneEffect.NONE,
    tile_id: str = "",
) -> np.ndarray:
    """Build a single tile_dt record. Helper so callers don't repeat the tuple shape."""
    return np.array((walkable, transparent, int(zone_effects), tile_id, dark, light), dtype=tile_dt)


SHROUD = np.array((ord(" "), Color.BLACK, Color.BLACK), dtype=graphic_dt)

WALL = new_tile(
    walkable=False,
    transparent=False,
    dark=(ord(" "), Color.WHITE, Color.WALL_DARK),
    light=(ord(" "), Color.WHITE, Color.WALL_LIT),
    tile_id="wall",
)

FLOOR = new_tile(
    walkable=True,
    transparent=True,
    dark=(ord(" "), Color.WHITE, Color.FLOOR_DARK),
    light=(ord(" "), Color.WHITE, Color.FLOOR_LIT),
    tile_id="floor",
)

# A deliberate, player-triggered exit -- see TriggerKind.FEATURE_STEPPED_ON --
# distinct from the organic hazard/sanity/turn-count transitions: standing on
# one always advances, on demand, regardless of level. tile_id is generic
# ("stairs_down") because each LevelDefinition's own TransitionRule decides
# where its stairs actually lead, not the tile itself.
STAIRS_DOWN = new_tile(
    walkable=True,
    transparent=True,
    dark=(ord(">"), Color.STAIRS, Color.FLOOR_DARK),
    light=(ord(">"), Color.STAIRS, Color.FLOOR_LIT),
    tile_id="stairs_down",
)

# The other flavor of exit feature -- set into a room's wall rather than
# standing free in the floor (see generator_office._place_exit_feature), so
# its background matches the wall tiles around it, not the floor.
DOOR_EXIT = new_tile(
    walkable=True,
    transparent=True,
    dark=(ord("+"), Color.DOOR, Color.WALL_DARK),
    light=(ord("+"), Color.DOOR, Color.WALL_LIT),
    tile_id="door_exit",
)

# Level 2's "giant car garage" reskin of WALL/FLOOR -- same shape/tile_id
# semantics (still walkable/transparent the same way, still whatever
# generate_office_level plugs in for LevelDefinition.wall_tile/floor_tile),
# just grey concrete instead of office wallpaper/carpet, with their own
# tile_id so look mode gets garage-flavored text (see rendering/ui.py)
# instead of the office wall/floor descriptions.
GARAGE_WALL = new_tile(
    walkable=False,
    transparent=False,
    dark=(ord(" "), Color.WHITE, Color.GARAGE_WALL_DARK),
    light=(ord(" "), Color.WHITE, Color.GARAGE_WALL_LIT),
    tile_id="garage_wall",
)

GARAGE_FLOOR = new_tile(
    walkable=True,
    transparent=True,
    dark=(ord(" "), Color.WHITE, Color.GARAGE_FLOOR_DARK),
    light=(ord(" "), Color.WHITE, Color.GARAGE_FLOOR_LIT),
    tile_id="garage_floor",
)

# A settlement's own exit feature -- same FEATURE_STEPPED_ON mechanics as
# DOOR_EXIT (generic tile_id, LevelDefinition's own TransitionRule decides
# where it leads), just a distinct look/tile_id so it reads as "the way into
# a settlement" rather than "another loop of the level you're already on"
# (see generator_office._place_settlement_door, registrations.LEVEL_2_GARAGE).
SETTLEMENT_DOOR = new_tile(
    walkable=True,
    transparent=True,
    dark=(ord("+"), Color.SETTLEMENT_DOOR, Color.WALL_DARK),
    light=(ord("+"), Color.SETTLEMENT_DOOR, Color.WALL_LIT),
    tile_id="settlement_door",
)

# A settlement's floor -- warm/lived-in, and a safe zone (see
# GameMap.has_zone_effect / sanity_system.SAFE_ZONE_RESTORE): sanity
# actively recovers here instead of just not draining.
SETTLEMENT_FLOOR = new_tile(
    walkable=True,
    transparent=True,
    zone_effects=ZoneEffect.SAFE,
    dark=(ord(" "), Color.WHITE, Color.SETTLEMENT_FLOOR_DARK),
    light=(ord(" "), Color.WHITE, Color.SETTLEMENT_FLOOR_LIT),
    tile_id="settlement_floor",
)

# A small inn room within a settlement -- still ZoneEffect.SAFE (sanity keeps
# recovering here same as the rest of the settlement) plus ZoneEffect.INN,
# which also passively restores HP and hunger while standing on it (see
# systems/rest_system.py). A warmer, cozier tone than the settlement's own
# floor so it reads as a distinct little room within it, not just more of
# the same safe zone.
INN_FLOOR = new_tile(
    walkable=True,
    transparent=True,
    zone_effects=ZoneEffect.SAFE | ZoneEffect.INN,
    dark=(ord(" "), Color.WHITE, Color.INN_FLOOR_DARK),
    light=(ord(" "), Color.WHITE, Color.INN_FLOOR_LIT),
    tile_id="inn_floor",
)

# Level 3's "pipeworks" reskin of WALL/FLOOR -- same shape/tile_id semantics
# as GARAGE_WALL/GARAGE_FLOOR, just a brown-tile floor and a wall that's a
# grey/brown amalgamation instead of the garage's flat concrete grey.
PIPEWORKS_WALL = new_tile(
    walkable=False,
    transparent=False,
    dark=(ord(" "), Color.WHITE, Color.PIPEWORKS_WALL_DARK),
    light=(ord(" "), Color.WHITE, Color.PIPEWORKS_WALL_LIT),
    tile_id="pipeworks_wall",
)

PIPEWORKS_FLOOR = new_tile(
    walkable=True,
    transparent=True,
    dark=(ord(" "), Color.WHITE, Color.PIPEWORKS_FLOOR_DARK),
    light=(ord(" "), Color.WHITE, Color.PIPEWORKS_FLOOR_LIT),
    tile_id="pipeworks_floor",
)
