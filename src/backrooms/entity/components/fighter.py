from __future__ import annotations

from backrooms.entity.components.base_component import BaseComponent


class Fighter(BaseComponent):
    """HP/combat stats. `take_damage` is shared by hazards (hazard.py's
    tick_spore_damage) and AttackAction -- one mitigation formula for both,
    so endurance behaves consistently regardless of damage source."""

    def __init__(self, hp: int, endurance: int = 0, power: int = 0, xp_reward: int = 0) -> None:
        self.max_hp = hp
        self.hp = hp
        # Flat physical-damage mitigation, subtracted from incoming damage
        # before it's applied to hp.
        self.endurance = endurance
        self.power = power
        # How much XP the player is awarded for killing the entity this is
        # attached to. Meaningless on the player's own Fighter.
        self.xp_reward = xp_reward

    def take_damage(self, amount: float) -> float:
        """Returns the actually-applied (post-mitigation) damage, so callers
        can report it (e.g. AttackAction's combat log line)."""
        mitigated = max(0.0, amount - self.endurance)
        self.hp = max(0, self.hp - mitigated)
        return mitigated

    def heal(self, amount: float) -> None:
        self.hp = min(self.max_hp, self.hp + amount)
