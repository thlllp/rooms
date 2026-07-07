"""What makes an item wearable -- which EquipmentComponent slot it occupies
and what passive effect it grants while equipped. Minimal for now: just
spore_resistance (see the Mask/tick_spore_damage) and capacity_bonus (see
the back-slot backpacks/EquipmentComponent.capacity_bonus) -- add fields
here as more equipment effects are actually needed rather than building a
speculative generic system upfront.
"""

from __future__ import annotations

from backrooms.entity.components.base_component import BaseComponent


class EquippableComponent(BaseComponent):
    def __init__(self, *, slot: str, spore_resistance: float = 0.0, capacity_bonus: int = 0) -> None:
        self.slot = slot
        self.spore_resistance = spore_resistance
        self.capacity_bonus = capacity_bonus
