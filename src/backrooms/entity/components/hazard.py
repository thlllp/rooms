"""Generic hazard component: any entity carrying one gets ticked once per
turn by systems/hazard_system.py. Concrete hazard behaviors (spore zone,
unstable floor, ...) are just tick_effect functions plus a factory that
builds a HazardComponent closing over their own bookkeeping in `.data` --
there is no hazard-kind-specific subclass hierarchy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from backrooms.constants import Color
from backrooms.entity.components.base_component import BaseComponent
from backrooms.geometry import chebyshev_distance

if TYPE_CHECKING:
    from backrooms.engine import Engine
    from backrooms.entity.entity import Entity

SPORE_DAMAGE_KIND = "spore_damage"


@dataclass(frozen=True)
class LootEntry:
    """One possible debris-pile find and its relative weight within that
    pile's own pool -- see make_debris_pile. `weight` is relative, not a
    per-entry probability (unlike world.level_registry.SpawnEntry.weight,
    which gates whether an entry is attempted at all): a pool of two
    weight=1.0 entries and one weight=0.2 entry picks that third one roughly
    1/5th as often as either of the other two, not "20% independent chance."
    Lets the same item (e.g. a Simple Backpack) be common in one debris
    pile's pool and rare in another's, without touching tick_debris_pile."""

    factory: Callable[[], "Entity"]
    weight: float = 1.0


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
    if chebyshev_distance(player.x, player.y, entity.x, entity.y) > radius:
        return

    # A worn face-slot item (see EquippableComponent.spore_resistance, e.g.
    # the crafted Mask) blunts this specifically -- a respiratory hazard, not
    # a generic one -- rather than a blanket damage-reduction stat. This is
    # the single-slot equip-effect pattern (see EquipmentComponent's own
    # docstring for when to use this vs. a pool-wide summed method like
    # capacity_bonus).
    mask = player.equipment.slots.get("face") if player.equipment is not None else None
    spore_resistance = mask.equippable.spore_resistance if mask is not None and mask.equippable is not None else 0.0
    severity = entity.hazard.severity * (1.0 - spore_resistance)

    if severity <= 0:
        engine.message_log.add_message("Your mask filters the spores out.", color=Color.GREY)
        return

    if player.fighter is not None:
        player.fighter.take_damage(severity)
    if player.sanity is not None:
        player.sanity.drain(severity * 0.5)
    engine.message_log.add_message("Spores fill your lungs.", color=Color.HAZARD)

    # Hazard damage can kill the player same as combat -- route through the
    # same kill_entity path AttackAction uses, or game_over never gets set.
    if player.fighter is not None and player.fighter.hp <= 0:
        engine.kill_entity(player)


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


def tick_debris_pile(entity: "Entity", engine: "Engine") -> None:
    """One-shot: the moment the player steps onto it, the pile resolves into
    either a useful item dropped underfoot or a jolt of bad luck that drains
    sanity instead, then removes itself -- searching the same debris twice
    wouldn't mean anything."""
    player = engine.player
    if (player.x, player.y) != (entity.x, entity.y):
        return

    data = entity.hazard.data
    if engine.rng.random() < data["good_chance"]:
        entries: tuple[LootEntry, ...] = data["item_factories"]
        entry = engine.rng.choices(entries, weights=[e.weight for e in entries], k=1)[0]
        item = entry.factory()
        item.place(entity.x, entity.y)
        engine.game_map.entities.add(item)
        engine.message_log.add_message("You dig through the debris and find something useful.", color=Color.WHITE)
    else:
        if player.sanity is not None:
            player.sanity.drain(entity.hazard.severity)
        engine.message_log.add_message("Something about the debris unsettles you.", color=Color.HAZARD)

    engine.game_map.entities.discard(entity)


def make_spore_zone(*, radius: int = 1, severity: float = 2.0) -> HazardComponent:
    return HazardComponent(SPORE_DAMAGE_KIND, tick_spore_damage, severity=severity, data={"radius": radius})


def make_unstable_floor(*, collapse_threshold: int = 4, event_flag: str = "floor_collapsed") -> HazardComponent:
    return HazardComponent(
        "unstable_floor",
        tick_unstable_floor,
        data={"collapse_threshold": collapse_threshold, "event_flag": event_flag},
    )


def make_debris_pile(
    *, item_factories: tuple[LootEntry, ...], good_chance: float = 0.6, sanity_penalty: float = 10.0
) -> HazardComponent:
    """`item_factories` is a weighted pool, not a single fixed item -- one
    LootEntry is picked per its weight on a good outcome, so a debris pile
    can turn up any of several different possible finds instead of always
    the same one, and different debris piles can weight the same item
    differently (see LootEntry)."""
    return HazardComponent(
        "debris_pile",
        tick_debris_pile,
        severity=sanity_penalty,
        data={"good_chance": good_chance, "item_factories": item_factories},
    )
