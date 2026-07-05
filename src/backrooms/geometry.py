"""Small shared geometry helpers, used anywhere Chebyshev (8-directional)
distance/adjacency is needed -- hazard radius checks, AI adjacency checks,
and hazard footprint rendering all want the exact same notion of "distance"
so they can't silently drift into different shapes."""

from __future__ import annotations

from functools import lru_cache


def chebyshev_distance(x1: int, y1: int, x2: int, y2: int) -> int:
    return max(abs(x1 - x2), abs(y1 - y2))


@lru_cache(maxsize=None)
def tiles_in_chebyshev_radius(radius: int) -> tuple[tuple[int, int], ...]:
    """(dx, dy) offsets within `radius` of the origin, excluding the origin
    itself. Cached since the set of offsets only depends on the radius, not
    on any particular hazard's position -- callers add their own (x, y)."""
    return tuple(
        (dx, dy)
        for dx in range(-radius, radius + 1)
        for dy in range(-radius, radius + 1)
        if (dx, dy) != (0, 0)
    )
