"""Starting player classes -- picked once at boot (see main.py's selection
screen), each just a different bundle of starting stats on the same Entity
shape. Simple for now: two classes, one differing stat each, everything else
shared with the common baseline below.
"""

from __future__ import annotations

from dataclasses import dataclass

from backrooms.constants import Color
from backrooms.entity.components.afflictions import AfflictionsComponent
from backrooms.entity.components.attributes import (
    BASELINE_ATTRIBUTE,
    AttributesComponent,
    endurance_mitigation_from_endurance,
    max_hp_from_endurance,
    max_sanity_from_willpower,
    power_from_strength,
    willpower_mitigation_from_willpower,
)
from backrooms.entity.components.equipment import EquipmentComponent
from backrooms.entity.components.experience import ExperienceComponent
from backrooms.entity.components.fighter import Fighter
from backrooms.entity.components.hunger import HungerComponent
from backrooms.entity.components.inventory import Inventory
from backrooms.entity.components.light_source import LightSourceComponent
from backrooms.entity.components.perception import PerceptionComponent
from backrooms.entity.components.quickness import QuicknessComponent
from backrooms.entity.components.sanity import SanityComponent
from backrooms.entity.entity import Entity, RenderOrder
from backrooms.data.registrations import spawn_cotton_tshirt, spawn_faded_jeans, spawn_sneakers

# Shared baseline every class starts from -- a class only overrides the one
# or two attributes that make it distinct (see PLAYER_CLASSES below). Tied
# to AttributesComponent's own baseline so PlayerClass's defaults and "no
# AttributesComponent at all" NPC fallback (attributes.attribute_value)
# always mean the same number for the same reason.
BASE_ATTRIBUTE = BASELINE_ATTRIBUTE
BASE_QUICKNESS = 1.0


@dataclass(frozen=True)
class PlayerClass:
    id: str
    display_name: str
    description: str
    quickness: float = BASE_QUICKNESS
    endurance: int = BASE_ATTRIBUTE
    willpower: int = BASE_ATTRIBUTE
    dexterity: int = BASE_ATTRIBUTE
    strength: int = BASE_ATTRIBUTE
    luck: int = BASE_ATTRIBUTE


PLAYER_CLASSES: tuple[PlayerClass, ...] = (
    PlayerClass(
        id="athletic",
        display_name="Athletic",
        description="A little faster on your feet than most.",
        quickness=1.2,
    ),
    PlayerClass(
        id="sturdy",
        display_name="Sturdy",
        description="Steadier nerves -- your grip on this place slips slower.",
        willpower=8,
    ),
)


def build_player(player_class: PlayerClass) -> Entity:
    attributes = AttributesComponent(
        endurance=player_class.endurance,
        willpower=player_class.willpower,
        dexterity=player_class.dexterity,
        strength=player_class.strength,
        luck=player_class.luck,
    )
    player = Entity(
        0,
        0,
        char="@",
        color=Color.PLAYER,
        name="Player",
        blocks_movement=True,
        render_order=RenderOrder.PLAYER,
        attributes=attributes,
        # Slight starting defenses: endurance blunts physical hazard damage,
        # willpower blunts sanity drain -- neither negates it outright.
        fighter=Fighter(
            hp=max_hp_from_endurance(attributes.endurance),
            endurance=endurance_mitigation_from_endurance(attributes.endurance),
            power=power_from_strength(attributes.strength),
        ),
        sanity=SanityComponent(
            max_sanity=max_sanity_from_willpower(attributes.willpower),
            willpower=willpower_mitigation_from_willpower(attributes.willpower),
        ),
        light_source=LightSourceComponent(max_fuel=300.0, radius=6, burn_rate=1.0, is_lit=False),
        perception=PerceptionComponent(acuity=1),
        experience=ExperienceComponent(),
        inventory=Inventory(capacity=10),
        quickness=QuicknessComponent(value=player_class.quickness),
        hunger=HungerComponent(max_hunger=100.0),
        equipment=EquipmentComponent(),
        afflictions=AfflictionsComponent(),
    )
    # Ordinary clothes, not gear -- the same plain chest/legs/feet items a
    # debris pile can turn up (see data.registrations), just worn from the
    # start rather than found. None grant any passive effect
    # (EquippableComponent.grants_benefit is False for all three); a fresh
    # character just isn't naked, nothing more.
    player.equipment.slots["chest"] = spawn_cotton_tshirt()
    player.equipment.slots["legs"] = spawn_faded_jeans()
    player.equipment.slots["feet"] = spawn_sneakers()
    return player
