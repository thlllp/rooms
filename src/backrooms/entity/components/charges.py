"""A finite pool of uses that depletes one at a time -- the shared durability
primitive behind both weapon wear (EquippableComponent, spent per connecting
hit via EquipmentComponent.register_weapon_hit) and finite-use tools
(ToolComponent, spent per craft via consume_charge). Extracted so "starts
full, spend one per use, depleted at zero" has exactly one definition rather
than a copy in each component. A component whose `charges` is None has no
pool at all -- it's unlimited.
"""

from __future__ import annotations


class Charges:
    def __init__(self, total: int) -> None:
        # A zero/negative pool is never a valid "finite but empty" item -- it
        # would deliver its effect once (0 -> -1 still passes the <= 0 break)
        # and then vanish. Reject it at construction so the None-vs-finite
        # split stays the only distinction callers reason about.
        if total <= 0:
            raise ValueError(f"Charges total must be positive, got {total}")
        self.total = total
        self.remaining = total

    def spend(self) -> bool:
        """Consumes one charge and returns whether that emptied the last one.
        The holder (a weapon that breaks, a tool that's used up) is
        responsible for acting on a True -- same "value reports, owner acts"
        split the callers already use."""
        self.remaining -= 1
        return self.remaining <= 0
