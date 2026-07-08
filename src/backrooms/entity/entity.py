from __future__ import annotations

from enum import IntEnum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backrooms.entity.components.afflictions import AfflictionsComponent
    from backrooms.entity.components.ai import BaseAI
    from backrooms.entity.components.attributes import AttributesComponent
    from backrooms.entity.components.barter import BarterComponent
    from backrooms.entity.components.consumable import ConsumableComponent
    from backrooms.entity.components.container import ContainerComponent
    from backrooms.entity.components.dialogue import DialogueComponent
    from backrooms.entity.components.equipment import EquipmentComponent
    from backrooms.entity.components.equippable import EquippableComponent
    from backrooms.entity.components.experience import ExperienceComponent
    from backrooms.entity.components.fighter import Fighter
    from backrooms.entity.components.hazard import HazardComponent
    from backrooms.entity.components.hunger import HungerComponent
    from backrooms.entity.components.inventory import Inventory
    from backrooms.entity.components.light_source import LightSourceComponent
    from backrooms.entity.components.perception import PerceptionComponent
    from backrooms.entity.components.quickness import QuicknessComponent
    from backrooms.entity.components.salvageable import SalvageableComponent
    from backrooms.entity.components.sanity import SanityComponent
    from backrooms.entity.components.tool import ToolComponent


class RenderOrder(IntEnum):
    HAZARD = auto()
    ITEM = auto()
    ACTOR = auto()
    PLAYER = auto()


class Entity:
    """A generic composable object on the map: player, wanderer, item, or hazard.

    Behavior is opt-in via component attributes (``ai``, ``fighter``, ``sanity``,
    ``hazard``, ...) rather than an inheritance hierarchy per entity kind, so new
    entity types are assembled instead of subclassed.
    """

    def __init__(
        self,
        x: int,
        y: int,
        char: str,
        color: tuple[int, int, int],
        name: str,
        *,
        blocks_movement: bool = False,
        blocks_sight: bool = False,
        render_order: RenderOrder = RenderOrder.ACTOR,
        is_hallucination: bool = False,
        hallucination_expires_at: int | None = None,
        causes_dread: bool = False,
        dread_radius: int = 0,
        contains_fabric: bool = False,
        ai: "BaseAI | None" = None,
        attributes: "AttributesComponent | None" = None,
        fighter: "Fighter | None" = None,
        inventory: "Inventory | None" = None,
        sanity: "SanityComponent | None" = None,
        light_source: "LightSourceComponent | None" = None,
        hazard: "HazardComponent | None" = None,
        perception: "PerceptionComponent | None" = None,
        experience: "ExperienceComponent | None" = None,
        consumable: "ConsumableComponent | None" = None,
        quickness: "QuicknessComponent | None" = None,
        hunger: "HungerComponent | None" = None,
        dialogue: "DialogueComponent | None" = None,
        equipment: "EquipmentComponent | None" = None,
        equippable: "EquippableComponent | None" = None,
        barter: "BarterComponent | None" = None,
        afflictions: "AfflictionsComponent | None" = None,
        tool: "ToolComponent | None" = None,
        salvageable: "SalvageableComponent | None" = None,
        container: "ContainerComponent | None" = None,
    ) -> None:
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.name = name
        self.blocks_movement = blocks_movement
        # A tile-transparency override, not a GameMap.tiles property -- see
        # GameMap.compute_fov, which layers this over the base tile
        # transparency each time FOV is recomputed. Lets a column/pillar
        # entity block sight without needing its own wall tile underneath.
        self.blocks_sight = blocks_sight
        self.render_order = render_order

        # Marks entities spawned by the hallucination system: they look and
        # render exactly like the real thing, this flag is never surfaced to
        # the player-facing renderer, only read by hallucination bookkeeping.
        self.is_hallucination = is_hallucination
        # Set only on hallucinated entities: the turns_in_level value at
        # which the hallucination system should despawn this entity.
        self.hallucination_expires_at = hallucination_expires_at

        # An entity doesn't need to be combat-capable (no `fighter`) to be a
        # sanity-draining presence -- an unsettling silhouette that never
        # attacks still costs the player sanity by proximity.
        self.causes_dread = causes_dread
        self.dread_radius = dread_radius
        # Whether scissors (see components.tool.make_fabric_cutter) can cut
        # this item up into a Rag -- a plain flag rather than a component
        # since it has no behavior of its own, same shape as causes_dread.
        self.contains_fabric = contains_fabric

        # Single source of truth for "what components exist on an Entity":
        # each is set as an attribute AND wired with its `.entity` backref
        # from this one dict, instead of a hand-written assignment plus a
        # separately-maintained wiring tuple that has to list the exact same
        # components in a second place.
        components: dict[str, object | None] = {
            "ai": ai,
            "attributes": attributes,
            "fighter": fighter,
            "inventory": inventory,
            "sanity": sanity,
            "light_source": light_source,
            "hazard": hazard,
            "perception": perception,
            "experience": experience,
            "consumable": consumable,
            "quickness": quickness,
            "hunger": hunger,
            "dialogue": dialogue,
            "equipment": equipment,
            "equippable": equippable,
            "barter": barter,
            "afflictions": afflictions,
            "tool": tool,
            "salvageable": salvageable,
            "container": container,
        }
        for name, component in components.items():
            setattr(self, name, component)
            if component is not None:
                component.entity = self

    def distance_to(self, x: int, y: int) -> float:
        return ((self.x - x) ** 2 + (self.y - y) ** 2) ** 0.5

    def move(self, dx: int, dy: int) -> None:
        self.x += dx
        self.y += dy

    def place(self, x: int, y: int) -> None:
        self.x = x
        self.y = y
