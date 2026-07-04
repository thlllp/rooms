"""Generic hazard component: any entity carrying one gets ticked once per
turn by systems/hazard_system.py. Concrete hazard behaviors (spore zone,
unstable floor, ...) are just tick_effect functions plus a factory that
builds a HazardComponent closing over their own bookkeeping in `.data` --
there is no hazard-kind-specific subclass hierarchy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from backrooms.constants import Color
from backrooms.entity.components.base_component import BaseComponent

if TYPE_CHECKING:
    from backrooms.engine import Engine
    from backrooms.entity.entity import Entity


class HazardComponent(BaseComponent):
    def __init__(
        self,
        kind: str,
        tick_effect: Callable[["Entity", "Engine"], None],
        *,
        severity: float = 1.0,
        active: bool = True,
        data: dict | None = None,
    ) -> None:
        self.kind = kind
        self.tick_effect = tick_effect
        self.severity = severity
        self.active = active
        self.data = data if data is not None else {}

    def tick(self, engine: "Engine") -> None:
        if self.active:
            self.tick_effect(self.entity, engine)


def tick_spore_damage(entity: "Entity", engine: "Engine") -> None:
    """Tile-anchored damage zone: hurts HP (once Fighter exists) and sanity
    while the player stands within `radius` tiles of the zone's placement.
    Radius is checked live off the entity's position rather than a
    precomputed tile set, so the spawner can drop it anywhere on the
    generated map without the factory needing to know map layout up front."""
    player = engine.player
    radius = entity.hazard.data.get("radius", 0)
    distance = max(abs(player.x - entity.x), abs(player.y - entity.y))
    if distance > radius:
        return

    severity = entity.hazard.severity
    if player.fighter is not None:
        player.fighter.hp = max(0, player.fighter.hp - severity)
    if player.sanity is not None:
        player.sanity.drain(severity * 0.5)
    engine.message_log.add_message("Spores fill your lungs.", color=Color.HAZARD)


def tick_unstable_floor(entity: "Entity", engine: "Engine") -> None:
    """Sets an event flag after enough steps on it -- composes with an
    EVENT_FLAG_SET TransitionRule for free, no bespoke collapse logic here."""
    player = engine.player
    if (player.x, player.y) != (entity.x, entity.y):
        return

    data = entity.hazard.data
    data["step_count"] = data.get("step_count", 0) + 1
    if data["step_count"] >= data["collapse_threshold"] and data["event_flag"] not in engine.event_flags:
        engine.event_flags.add(data["event_flag"])
        engine.message_log.add_message("The floor gives way beneath your feet.", color=Color.WARNING)


def make_spore_zone(*, radius: int = 1, severity: float = 2.0) -> HazardComponent:
    return HazardComponent("spore_damage", tick_spore_damage, severity=severity, data={"radius": radius})


def make_unstable_floor(*, collapse_threshold: int = 4, event_flag: str = "floor_collapsed") -> HazardComponent:
    return HazardComponent(
        "unstable_floor",
        tick_unstable_floor,
        data={"collapse_threshold": collapse_threshold, "event_flag": event_flag},
    )
