"""Starting player classes -- picked once at boot (see main.py's selection
screen), each just a different bundle of starting stats on the same Entity
shape. Simple for now: two classes, one differing stat each, everything else
shared with the common baseline below.
"""

from __future__ import annotations

from dataclasses import dataclass

from backrooms.constants import Color
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

# Shared baseline every class starts from -- a class only overrides the one
# or two stats that make it distinct (see PLAYER_CLASSES below).
BASE_HP = 20
BASE_ENDURANCE = 1
BASE_POWER = 1
BASE_MAX_SANITY = 100
BASE_WILLPOWER = 0.3
BASE_QUICKNESS = 1.0


@dataclass(frozen=True)
class PlayerClass:
    id: str
    display_name: str
    description: str
    quickness: float = BASE_QUICKNESS
    max_sanity: int = BASE_MAX_SANITY
    willpower: float = BASE_WILLPOWER


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
        max_sanity=120,
        willpower=0.5,
    ),
)


def build_player(player_class: PlayerClass) -> Entity:
    return Entity(
        0,
        0,
        char="@",
        color=Color.PLAYER,
        name="Player",
        blocks_movement=True,
        render_order=RenderOrder.PLAYER,
        # Slight starting defenses: endurance blunts physical hazard damage,
        # willpower blunts sanity drain -- neither negates it outright.
        fighter=Fighter(hp=BASE_HP, endurance=BASE_ENDURANCE, power=BASE_POWER),
        sanity=SanityComponent(max_sanity=player_class.max_sanity, willpower=player_class.willpower),
        light_source=LightSourceComponent(max_fuel=300.0, radius=6, burn_rate=1.0, is_lit=False),
        perception=PerceptionComponent(acuity=1),
        experience=ExperienceComponent(),
        inventory=Inventory(capacity=10),
        quickness=QuicknessComponent(value=player_class.quickness),
        hunger=HungerComponent(max_hunger=100.0),
        equipment=EquipmentComponent(),
    )
