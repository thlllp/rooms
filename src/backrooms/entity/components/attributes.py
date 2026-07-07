"""The five core attributes a character is built from, plus how they
translate into the numbers Fighter/SanityComponent actually consume. The
derivation functions live here rather than inside Fighter/SanityComponent
themselves -- mirroring experience_system.py's own reasoning for staying
separate from ExperienceComponent -- so this bridges attributes and those
two components' concerns without any of the three needing to import each
other. Both data/player_classes.py (character creation) and
systems/experience_system.py (leveling) call these same functions, so a
character's displayed attributes and their derived stats can never drift
out of lockstep between the two.

Dexterity is read directly by actions.AttackAction's hit-chance roll (via
attribute_value below, not a derived Fighter/SanityComponent field -- there's
nothing to derive, dexterity IS the combat stat). `luck` has no consumer yet
-- same precedent as QuicknessComponent.value, which sat unused for a while
before its own system existed. Don't invent a mechanic for it here; add one
only once something actually needs it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backrooms.entity.components.base_component import BaseComponent

if TYPE_CHECKING:
    from backrooms.entity.entity import Entity

# Every attribute's default, and what an entity with NO AttributesComponent
# at all (every NPC today -- Hollow, Wanderer, ...) is assumed to have for
# any attribute-driven system (see attribute_value below).
BASELINE_ATTRIBUTE = 5


class AttributesComponent(BaseComponent):
    def __init__(
        self,
        *,
        endurance: int = BASELINE_ATTRIBUTE,
        willpower: int = BASELINE_ATTRIBUTE,
        dexterity: int = BASELINE_ATTRIBUTE,
        strength: int = BASELINE_ATTRIBUTE,
        luck: int = BASELINE_ATTRIBUTE,
    ) -> None:
        self.endurance = endurance
        self.willpower = willpower
        self.dexterity = dexterity
        self.strength = strength
        self.luck = luck


def attribute_value(entity: "Entity", name: str) -> int:
    """The named core attribute's value for `entity`, or BASELINE_ATTRIBUTE
    if it has no AttributesComponent at all. Centralizes the "does this
    entity even have attributes" fallback so each new attribute-driven
    system (dexterity's hit-chance roll today, strength's object-
    manipulation checks or endurance's disease resistance later, per this
    module's own docstring) doesn't reinvent its own default."""
    if entity.attributes is None:
        return BASELINE_ATTRIBUTE
    return getattr(entity.attributes, name)


# Divisors/multipliers are chosen so BASELINE_ATTRIBUTE (5) reproduces
# exactly what player_classes.py used to hardcode before attributes
# existed: hp=20, endurance=1, max_sanity=100, willpower=0.3, power=1.
HP_PER_ENDURANCE = 4
ENDURANCE_MITIGATION_DIVISOR = 5
SANITY_PER_WILLPOWER = 20
WILLPOWER_MITIGATION_PER_POINT = 0.06
POWER_PER_STRENGTH_DIVISOR = 5


def _scale(value: int, factor: float) -> float:
    return value * factor


def _floor_divide(value: int, divisor: int) -> int:
    return value // divisor


def max_hp_from_endurance(endurance: int) -> int:
    return int(_scale(endurance, HP_PER_ENDURANCE))


def endurance_mitigation_from_endurance(endurance: int) -> int:
    return _floor_divide(endurance, ENDURANCE_MITIGATION_DIVISOR)


def max_sanity_from_willpower(willpower: int) -> int:
    return int(_scale(willpower, SANITY_PER_WILLPOWER))


def willpower_mitigation_from_willpower(willpower: int) -> float:
    return round(_scale(willpower, WILLPOWER_MITIGATION_PER_POINT), 2)


def power_from_strength(strength: int) -> int:
    return _floor_divide(strength, POWER_PER_STRENGTH_DIVISOR)
