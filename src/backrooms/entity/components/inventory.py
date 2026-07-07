from __future__ import annotations

from typing import TYPE_CHECKING

from backrooms.entity.components.base_component import BaseComponent

if TYPE_CHECKING:
    from backrooms.entity.entity import Entity


class Inventory(BaseComponent):
    """Held items are Entity objects, same as anything on the map -- picking
    one up just moves it from GameMap.entities into this list."""

    def __init__(self, capacity: int = 10) -> None:
        self.capacity = capacity
        self.items: list["Entity"] = []


def effective_capacity(entity: "Entity") -> int:
    """How many items `entity` can actually hold: its base Inventory.capacity
    plus whatever worn gear adds (a back-slot backpack, see
    EquipmentComponent.capacity_bonus). Computed fresh rather than mutating
    Inventory.capacity on equip/unequip, so it can never drift out of sync with
    what's worn. Lives here (not in actions) so both the pickup/equip paths and
    hazard drops share one definition. Returns 0 for an entity with no
    inventory."""
    if entity.inventory is None:
        return 0
    bonus = entity.equipment.capacity_bonus() if entity.equipment is not None else 0
    return entity.inventory.capacity + bonus
