"""Ongoing conditions an entity has contracted -- e.g. the Hydrolitis Plague
picked up from Level 1.11's contaminated water (see systems/disease_system.py).

Deliberately minimal for now: just the set of active affliction names. It's the
seam future systems hang mechanical effects off (a plague that drains stats,
spreads, or needs curing); contraction and any effects live in their own
systems, not here -- mirroring how AttributesComponent stays a plain data bag
with its consumers elsewhere.
"""

from __future__ import annotations

from backrooms.entity.components.base_component import BaseComponent


class AfflictionsComponent(BaseComponent):
    def __init__(self, active: set[str] | None = None) -> None:
        self.active: set[str] = set(active) if active else set()

    def has(self, name: str) -> bool:
        return name in self.active

    def add(self, name: str) -> bool:
        """Marks `name` active; returns True only if it wasn't already, so a
        caller can log the moment of contraction exactly once."""
        if name in self.active:
            return False
        self.active.add(name)
        return True
