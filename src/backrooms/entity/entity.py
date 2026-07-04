from __future__ import annotations

from enum import IntEnum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backrooms.entity.components.ai import BaseAI
    from backrooms.entity.components.fighter import Fighter
    from backrooms.entity.components.hazard import HazardComponent
    from backrooms.entity.components.inventory import Inventory
    from backrooms.entity.components.light_source import LightSourceComponent
    from backrooms.entity.components.sanity import SanityComponent


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
        render_order: RenderOrder = RenderOrder.ACTOR,
        is_hallucination: bool = False,
        hallucination_expires_at: int | None = None,
        causes_dread: bool = False,
        dread_radius: int = 0,
        ai: "BaseAI | None" = None,
        fighter: "Fighter | None" = None,
        inventory: "Inventory | None" = None,
        sanity: "SanityComponent | None" = None,
        light_source: "LightSourceComponent | None" = None,
        hazard: "HazardComponent | None" = None,
    ) -> None:
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.name = name
        self.blocks_movement = blocks_movement
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

        self.ai = ai
        self.fighter = fighter
        self.inventory = inventory
        self.sanity = sanity
        self.light_source = light_source
        self.hazard = hazard

        for component in (ai, fighter, inventory, sanity, light_source, hazard):
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
