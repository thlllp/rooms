from __future__ import annotations

from backrooms.entity.components.base_component import BaseComponent


class ExperienceComponent(BaseComponent):
    """Tracks level/XP only -- what a level-up actually grants lives in
    systems/experience_system.py, not here, so this component doesn't need
    to know about Fighter/PerceptionComponent/etc to level them up."""

    def __init__(
        self,
        level: int = 1,
        current_xp: int = 0,
        base_xp_to_level: int = 20,
        level_up_factor: float = 1.5,
    ) -> None:
        self.level = level
        self.current_xp = current_xp
        self.base_xp_to_level = base_xp_to_level
        self.level_up_factor = level_up_factor

    @property
    def xp_to_next_level(self) -> int:
        return round(self.base_xp_to_level * (self.level_up_factor ** (self.level - 1)))

    def gain_xp(self, amount: int) -> int:
        """Applies the XP and returns how many levels were gained (0 if none)."""
        self.current_xp += amount
        levels_gained = 0
        while self.current_xp >= self.xp_to_next_level:
            self.current_xp -= self.xp_to_next_level
            self.level += 1
            levels_gained += 1
        return levels_gained
