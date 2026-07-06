from __future__ import annotations

from backrooms.entity.components.base_component import BaseComponent


class HungerComponent(BaseComponent):
    """Current/max hunger, shown as a bar (see rendering/ui.py's
    render_hunger_bar). Nothing drains this down yet -- no system ticks it
    per turn -- so restore() only matters once something does (currently
    systems/rest_system.py, which restores it passively in an inn zone);
    it's just the stat, its display, and a way to raise it, wired up ahead
    of the drain side landing."""

    def __init__(self, max_hunger: float = 100.0) -> None:
        self.max_hunger = max_hunger
        self.current = max_hunger

    def restore(self, amount: float) -> None:
        self.current = min(self.max_hunger, self.current + amount)
