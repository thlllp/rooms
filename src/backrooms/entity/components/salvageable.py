"""Marks furniture that can be bumped into to attempt salvaging a usable
item out of it -- e.g. wrenching a leg off a wooden chair/table into an
improvised melee weapon (see actions.SalvageAction). Success is a flat
strength threshold, not a probability: at or above strength_required it
always works, below it it never does. Add fields here only once a second
kind of salvage check is actually needed (a tool requirement, say) rather
than building that in speculatively now.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from backrooms.entity.components.base_component import BaseComponent

if TYPE_CHECKING:
    from backrooms.entity.entity import Entity


class SalvageableComponent(BaseComponent):
    def __init__(self, *, result_factory: Callable[[], "Entity"], strength_required: int) -> None:
        self.result_factory = result_factory
        self.strength_required = strength_required
