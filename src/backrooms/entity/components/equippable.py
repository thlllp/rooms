"""What makes an item wearable -- which EquipmentComponent slot it occupies
and what passive effect it grants while equipped. Minimal for now: just
spore_resistance (see the Mask/tick_spore_damage), flood_resistance (see
the Wading Boots/disease_system.process_diseases), capacity_bonus (see
the back-slot backpacks/EquipmentComponent.capacity_bonus), and power_bonus
(see the improvised furniture-leg weapons/EquipmentComponent.power_bonus)
-- add fields here as more equipment effects are actually needed rather
than building a speculative generic system upfront.
"""

from __future__ import annotations

from backrooms.entity.components.base_component import BaseComponent
from backrooms.entity.components.charges import Charges


class EquippableComponent(BaseComponent):
    def __init__(
        self,
        *,
        slot: str,
        spore_resistance: float = 0.0,
        flood_resistance: float = 0.0,
        capacity_bonus: int = 0,
        power_bonus: int = 0,
        max_uses: int | None = None,
    ) -> None:
        self.slot = slot
        self.spore_resistance = spore_resistance
        self.flood_resistance = flood_resistance
        self.capacity_bonus = capacity_bonus
        self.power_bonus = power_bonus
        # None (every non-weapon equippable today) means unlimited durability;
        # a finite `max_uses` becomes a Charges pool that ticks down on each
        # connecting hit and breaks at zero (see
        # EquipmentComponent.register_weapon_hit). Each spawned item gets its
        # own pool, so wear on one Chair Leg doesn't affect another.
        self.charges = Charges(max_uses) if max_uses is not None else None

    @property
    def grants_benefit(self) -> bool:
        """Whether actually wearing this does anything -- any passive effect
        or a weapon's power. Plain found clothing (see the Flannel Shirt/
        Faded Jeans in registrations.py) is equippable but grants nothing,
        existing only as fabric; Scissors (make_fabric_cutter) reads this to
        cut that scrap up before ever touching functional gear that merely
        happens to be cloth (the Mask, the backpacks)."""
        return bool(self.spore_resistance or self.flood_resistance or self.capacity_bonus or self.power_bonus)
