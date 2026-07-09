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


def worn_slot_effect(entity: "Entity", slot: str, attr: str) -> float:
    """The named EquippableComponent effect (`spore_resistance`,
    `flood_resistance`, ...) granted by whatever `entity` wears in `slot`, or
    0.0 if the slot is empty or the entity has no equipment. The single
    "read one resistance off one worn slot" lookup, shared by every hazard
    that a specific slot's gear protects against (see hazard.tick_spore_damage
    for the face-slot Mask, disease_system.process_diseases for the feet-slot
    Wading Boots) so each one isn't its own hand-rolled None-guard chain."""
    if entity.equipment is None:
        return 0.0
    item = entity.equipment.slots.get(slot)
    if item is None or item.equippable is None:
        return 0.0
    return getattr(item.equippable, attr)


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

    def power_bonus(self) -> int:
        """Sum of every equipped item's EquippableComponent.power_bonus (a
        hand-slot weapon, e.g. a salvaged Chair Leg/Table Leg) -- read by
        AttackAction's power calculation, same pool-wide-additive shape as
        capacity_bonus above."""
        return sum(item.equippable.power_bonus for item in self.equipped_items())

    def register_weapon_hit(self) -> list["Entity"]:
        """Spends a durability charge on whatever actually contributed to a
        connecting attack's power -- i.e. equipped items with a power_bonus
        (a hand-slot weapon), not every durable item worn elsewhere (a worn
        item with no power_bonus was never doing the hitting, so it never
        loses a charge for someone else's swing). Called once per connecting
        attack (see AttackAction), never on a miss. Breaks (unequipped,
        returned) at zero; an item with no Charges (unlimited -- every
        non-weapon equippable today, and most weapons too) is untouched."""
        broken = []
        for slot, item in list(self.slots.items()):
            if item is None or item.equippable.power_bonus <= 0 or item.equippable.charges is None:
                continue
            if item.equippable.charges.spend():
                self.slots[slot] = None
                broken.append(item)
        return broken
