from __future__ import annotations

from backrooms.entity.components.base_component import BaseComponent


class HungerComponent(BaseComponent):
    """Current/max hunger, shown as a bar (see rendering/ui.py's
    render_hunger_bar). Nothing drains or restores this yet -- no system
    ticks it down per turn and no food item exists to restore it -- it's
    just the stat and its display, wired up ahead of that logic landing."""

    def __init__(self, max_hunger: float = 100.0) -> None:
        self.max_hunger = max_hunger
        self.current = max_hunger
