"""Generic tool component: an item that performs an effect when used but,
unlike ConsumableComponent, is never removed from inventory afterward (see
UseItemAction) -- mirrors consumable.py's wrap-an-effect-callable shape,
just without the "gone after one use" part. Optionally has a finite Charges
pool (see the Sewing Kit/CraftingRecipe.required_tool) instead of being
reusable forever like Scissors -- the same durability primitive
EquippableComponent uses for weapon wear, just spent by CraftAction rather
than by a connecting attack.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from backrooms.constants import Color
from backrooms.entity.components.base_component import BaseComponent
from backrooms.entity.components.charges import Charges

if TYPE_CHECKING:
    from backrooms.engine import Engine
    from backrooms.entity.entity import Entity


class ToolComponent(BaseComponent):
    def __init__(self, use_effect: Callable[["Entity", "Engine"], bool], *, max_uses: int | None = None) -> None:
        self.use_effect = use_effect
        # None (Scissors today) means unlimited; a finite max_uses becomes a
        # Charges pool spent per craft (see consume_charge). Per-instance so
        # each spawned tool tracks its own remaining count.
        self.charges = Charges(max_uses) if max_uses is not None else None

    def use(self, user: "Entity", engine: "Engine") -> bool:
        """Runs the tool's effect and returns whether it actually did
        something -- False for a no-op (nothing to cut, or a tool with no
        direct-use effect at all), so UseItemAction can refund the turn
        rather than charging the player for a selection that changed no
        game state."""
        return self.use_effect(user, engine)

    def consume_charge(self) -> bool:
        """Spends one charge if this tool has a finite pool; a no-op (always
        False) for an unlimited tool. Returns whether that use just exhausted
        the last charge -- the caller (CraftAction, for a required_tool) is
        responsible for actually removing a depleted tool from wherever it's
        held, same "value reports, owner acts" split as
        EquipmentComponent.register_weapon_hit."""
        return self.charges.spend() if self.charges is not None else False


def _fabric_scrap_first(held: list["Entity"]) -> "Entity | None":
    """The fabric item Scissors should cut, or None if nothing is fabric.
    Prefers plain scrap -- clothing that grants no benefit worn (see
    EquippableComponent.grants_benefit) -- over functional gear that merely
    happens to be cloth, so a player who owns both a Flannel Shirt and an
    unequipped Hiking Bag never loses the bag to a mis-aimed cut. Cutting a
    Mask/backpack back into a Rag is still possible, just only once no plain
    clothing is left to take the blade first. Inventory order breaks ties
    within each tier, same "resolve it, no picker" shape as CraftAction."""
    fabric = [item for item in held if item.contains_fabric]
    scrap = next((item for item in fabric if item.equippable is None or not item.equippable.grants_benefit), None)
    return scrap if scrap is not None else (fabric[0] if fabric else None)


def make_fabric_cutter(rag_factory: Callable[[], "Entity"]) -> ToolComponent:
    """Scissors: cuts a held item tagged Entity.contains_fabric (found
    clothing, and -- only when no plain clothing is on hand -- the Mask or
    backpacks) into `rag_factory()`. See _fabric_scrap_first for which item
    is chosen. Takes the Rag factory as a parameter instead of importing one
    directly: this module sits below data/registrations.py in the dependency
    graph (every concrete item factory lives there), same reason
    make_debris_pile takes its item_factories from the caller rather than
    importing them itself."""

    def _use(user: "Entity", engine: "Engine") -> bool:
        held = user.inventory.items if user.inventory is not None else []
        target = _fabric_scrap_first(held)
        if target is None:
            engine.message_log.add_message("Nothing here is made of fabric.", color=Color.GREY)
            return False
        held.remove(target)
        held.append(rag_factory())
        engine.message_log.add_message(f"You cut the {target.name} into a rag.", color=Color.WHITE)
        return True

    return ToolComponent(_use)


def make_sewing_kit(*, max_uses: int = 5) -> ToolComponent:
    """Sewing Kit: a finite-charge tool meant to be required by future
    crafting recipes (see CraftingRecipe.required_tool/CraftAction) rather
    than consumed as an ordinary named ingredient -- one charge per
    successful craft that calls for it, worn out and discarded once
    depleted. What it can actually help craft isn't decided yet; this only
    wires up the reusable-with-finite-charges mechanic itself. Selecting it
    directly from inventory (see UseItemAction) has no effect of its own --
    there's nothing to sew without a recipe that needs it yet, so it returns
    False and UseItemAction refunds the turn."""

    def _use(user: "Entity", engine: "Engine") -> bool:
        engine.message_log.add_message("Best saved for mending something -- try crafting instead.", color=Color.GREY)
        return False

    return ToolComponent(_use, max_uses=max_uses)
