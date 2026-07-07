"""Bartering with a community's Elder -- a small, one-shot stock of goods the
player buys with a currency item. Almond Water is the default currency, but
it's per-Elder configurable (currency_item_name), so a different community or
faction can demand something else entirely without any new machinery. Prices
are quoted in whole currency items and scaled by the level's own
LevelDefinition.barter_price_multiplier (see price_for), so the same good is
worth more or fewer bottles depending on which community you're standing in.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from backrooms.entity.components.base_component import BaseComponent

if TYPE_CHECKING:
    from backrooms.entity.entity import Entity


@dataclass(frozen=True)
class BarterOffer:
    """One good the Elder will part with and its base price, in whole units of
    the owning BarterComponent.currency_item_name. base_price is the "at par"
    cost (level multiplier 1.0); what the player actually pays is this scaled
    by the community's price multiplier (see BarterComponent.price_for)."""

    result_factory: Callable[[], "Entity"]
    base_price: int


class BarterComponent(BaseComponent):
    def __init__(
        self,
        *,
        offers: tuple[BarterOffer, ...],
        currency_item_name: str = "Almond Water Bottle",
        greeting_lines: tuple[str, ...] = (),
    ) -> None:
        # A per-instance COPY -- offers are consumed (popped) as they're bought
        # (see actions.BarterAction), so every Elder built from the same
        # factory must get its own independent, depletable stock rather than
        # sharing and mutating one tuple.
        self.offers: list[BarterOffer] = list(offers)
        self.currency_item_name = currency_item_name
        self.greeting_lines = greeting_lines

    def price_for(self, offer: "BarterOffer", *, multiplier: float) -> int:
        """A good's base price scaled by the community's price multiplier --
        floored at 1, so nothing is ever free no matter how cheap the level."""
        return max(1, round(offer.base_price * multiplier))

    def pick_greeting(self, rng: random.Random) -> str:
        return rng.choice(self.greeting_lines) if self.greeting_lines else ""
