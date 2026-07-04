from __future__ import annotations

from backrooms.entity.components.base_component import BaseComponent


class Fighter(BaseComponent):
    """HP/combat stats only -- no attack() or damage-resolution logic yet.

    Deliberately left as the seam for a future combat milestone: hazards
    that deal damage (see hazard.py's tick_spore_damage) already write to
    `.hp` directly, proving the field is load-bearing before any attack
    action exists.
    """

    def __init__(self, hp: int, defense: int = 0, power: int = 0) -> None:
        self.max_hp = hp
        self.hp = hp
        self.defense = defense
        self.power = power
