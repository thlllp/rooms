"""Structured numpy dtypes for map tiles.

Mirrors the classic python-tcod tutorial pattern: a small "graphic" struct
(glyph + colors) nested twice inside a "tile" struct, once for how the tile
looks when merely remembered/explored ("dark") and once for how it looks
while actually lit and in FOV ("light").
"""

from __future__ import annotations

import numpy as np

from backrooms.constants import Color

graphic_dt = np.dtype(
    [
        ("ch", np.int32),
        ("fg", "3B"),
        ("bg", "3B"),
    ]
)

tile_dt = np.dtype(
    [
        ("walkable", np.bool_),
        ("transparent", np.bool_),
        ("is_safe_zone", np.bool_),
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
    is_safe_zone: bool = False,
    tile_id: str = "",
) -> np.ndarray:
    """Build a single tile_dt record. Helper so callers don't repeat the tuple shape."""
    return np.array((walkable, transparent, is_safe_zone, tile_id, dark, light), dtype=tile_dt)


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
