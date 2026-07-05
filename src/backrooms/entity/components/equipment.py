"""Worn gear, one item per slot -- distinct from Inventory (held-but-not-worn
items) and from ConsumableComponent (used once then gone): an equipped item
stays equipped and keeps granting its passive effect (see EquippableComponent)
until explicitly removed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backrooms.entity.components.base_component import BaseComponent

if TYPE_CHECKING:
    from backrooms.entity.entity import Entity

SLOTS: tuple[str, ...] = ("head", "face", "chest", "legs")


class EquipmentComponent(BaseComponent):
    def __init__(self) -> None:
        self.slots: dict[str, "Entity | None"] = {slot: None for slot in SLOTS}

    def equipped_items(self) -> list["Entity"]:
        """SLOTS order, occupied slots only -- the single source of truth for
        how equipped items are ordered, shared by UseItemAction (which slot
        index means which item) and render_inventory_screen (what's printed),
        so the two can never disagree about the ordering."""
        return [item for item in self.slots.values() if item is not None]
