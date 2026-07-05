from __future__ import annotations

from backrooms.entity.components.base_component import BaseComponent


class QuicknessComponent(BaseComponent):
    """A single stat, `value`, meant as an actions-per-turn multiplier: 1.0 is
    the current 1-action-per-turn baseline every entity effectively has today.
    Nothing consumes this yet -- the turn loop (main.py's advance_turn call)
    always advances one turn per costs_turn action regardless of `value` --
    it exists so future speed-affecting effects (items, hazards, sanity
    bands) have a stat to modify without having to invent one under time
    pressure once an actual turn-economy/energy system lands."""

    def __init__(self, value: float = 1.0) -> None:
        self.value = value
