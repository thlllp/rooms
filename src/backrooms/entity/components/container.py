"""Marks furniture you bump into to open, yielding one weighted-random item
from its pool into your pack -- e.g. a Toolbox holding nails, scissors, a
sewing kit, or (rarely) a nailgun (see actions.OpenContainerAction). One-shot:
the container is removed once opened, so it can't be searched twice.

Distinct from SalvageableComponent, which destroys structural furniture (a
chair, a table) for one specific part behind a strength check -- a container
just opens, has no gate, and draws from a weighted pool. The two share their
extract-and-store plumbing (loot pick via hazard.pick_loot, placement via
inventory.store_or_drop) rather than each hand-rolling it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backrooms.entity.components.base_component import BaseComponent

if TYPE_CHECKING:
    from backrooms.entity.components.hazard import LootEntry


class ContainerComponent(BaseComponent):
    def __init__(self, *, loot_pool: tuple["LootEntry", ...]) -> None:
        self.loot_pool = loot_pool
