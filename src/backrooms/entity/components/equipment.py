"""Worn gear, one item per slot -- distinct from Inventory (held-but-not-worn
items) and from ConsumableComponent (used once then gone): an equipped item
stays equipped and keeps granting its passive effect (see EquippableComponent)
until explicitly removed.

Two sanctioned patterns for reading an equip effect, depending on its shape:
- Pool-wide, additive across every slot (e.g. capacity_bonus below): a method
  here on EquipmentComponent that sums the field over `equipped_items()`.
- Tied to one specific slot (e.g. spore_resistance, only meaningful from
  whatever's in the face slot): an ad-hoc `self.slots.get("face")` lookup at
  the point of use (see hazard.tick_spore_damage) -- there's nothing to sum
  across slots for an effect that only ever comes from one of them. Pick
  whichever of these two matches a new effect's shape rather than inventing
  a third pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backrooms.entity.components.base_component import BaseComponent

if TYPE_CHECKING:
    from backrooms.entity.entity import Entity

SLOTS: tuple[str, ...] = ("head", "face", "chest", "back", "legs", "feet", "left_hand", "right_hand")


class EquipmentComponent(BaseComponent):
    def __init__(self) -> None:
        self.slots: dict[str, "Entity | None"] = {slot: None for slot in SLOTS}

    def equipped_items(self) -> list["Entity"]:
        """SLOTS order, occupied slots only -- the single source of truth for
        how equipped items are ordered, shared by UseItemAction (which slot
        index means which item) and render_inventory_screen (what's printed),
        so the two can never disagree about the ordering."""
        return [item for item in self.slots.values() if item is not None]

    def capacity_bonus(self) -> int:
        """Sum of every equipped item's EquippableComponent.capacity_bonus
        (e.g. a back-slot backpack) -- read by Inventory-capacity checks
        (see actions.PickupAction/UseItemAction) rather than mutating
        Inventory.capacity directly on equip/unequip, so it can never drift
        out of sync with what's actually worn."""
        return sum(item.equippable.capacity_bonus for item in self.equipped_items())
