"""Marks a one-shot searchable debris pile you bump into -- see
actions.SearchDebrisAction. Distinct from both furniture components in
entity/components/: SalvageableComponent gates behind a strength check but
always succeeds once passed; ContainerComponent has no gate but also always
succeeds. A debris pile has no gate either, but `good_chance` odds instead of
a guarantee -- dig through it and you might come up empty-handed (a sanity
hit instead of an item), same gamble tick_debris_pile used to resolve
automatically on step, now resolved by an explicit search."""

from __future__ import annotations

from backrooms.entity.components.base_component import BaseComponent
from backrooms.entity.components.hazard import LootEntry


class DebrisComponent(BaseComponent):
    def __init__(
        self, *, item_factories: tuple[LootEntry, ...], good_chance: float = 0.6, sanity_penalty: float = 10.0
    ) -> None:
        self.item_factories = item_factories
        self.good_chance = good_chance
        self.sanity_penalty = sanity_penalty
