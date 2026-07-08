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
from backrooms.entity.components.equipment import worn_slot_effect
from backrooms.entity.components.inventory import store_or_drop
from backrooms.geometry import chebyshev_distance

if TYPE_CHECKING:
    import random

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


def pick_loot(rng: "random.Random", pool: tuple["LootEntry", ...]) -> "Entity":
    """Builds one freshly-spawned item from `pool`, chosen by LootEntry.weight
    (see its docstring) -- the shared weighted-pick used by both debris piles
    (tick_debris_pile) and searchable containers
    (actions.OpenContainerAction), so the weighting rule lives in one place.
    Drawn from `rng` (engine.rng) rather than the global random so a seed
    reproduces the same finds."""
    entry = rng.choices(pool, weights=[e.weight for e in pool], k=1)[0]
    return entry.factory()


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

    @property
    def is_area(self) -> bool:
        """Whether this hazard endangers a radius around its tile (spore/heat/
        impact/twilight zones) rather than only the exact tile it sits on
        (unstable floors, debris piles) -- the classification auto_explore
        uses to decide what counts as something you can "walk into", kept
        here so callers never key on `.data`'s internal layout directly."""
        return "radius" in self.data


def hazard_threatens(entity: "Entity", x: int, y: int, *, buffer: int = 0) -> bool:
    """Whether (x, y) is within the hazard's data['radius'] (Chebyshev, plus
    `buffer` extra tiles) of its tile -- the single radius rule for every
    tile-anchored hazard, shared by the damage ticks (via _player_in_radius)
    and by auto_explore's early-warning stop (buffer=1), so "would this hurt"
    and "should auto-movement stop" can never drift apart. Inactive hazards
    never tick (see HazardComponent.tick), so they threaten nothing here
    either. Checked live off the entity's position rather than a precomputed
    tile set, so the spawner can drop the hazard anywhere without knowing map
    layout."""
    return entity.hazard.active and chebyshev_distance(x, y, entity.x, entity.y) <= entity.hazard.data.get("radius", 0) + buffer


def _player_in_radius(entity: "Entity", engine: "Engine") -> bool:
    """hazard_threatens at the player's own tile -- the shared entry gate for
    every tile-anchored radius hazard's tick."""
    player = engine.player
    return hazard_threatens(entity, player.x, player.y)


def tick_spore_damage(entity: "Entity", engine: "Engine") -> None:
    """Tile-anchored damage zone: hurts HP (once Fighter exists) and sanity
    while the player stands within `radius` tiles of the zone's placement."""
    if not _player_in_radius(entity, engine):
        return
    player = engine.player

    # A worn face-slot item (see EquippableComponent.spore_resistance, e.g.
    # the crafted Mask) blunts this specifically -- a respiratory hazard, not
    # a generic one -- rather than a blanket damage-reduction stat. This is
    # the single-slot equip-effect pattern (see equipment.worn_slot_effect,
    # shared with disease_system's feet-slot flood resistance).
    spore_resistance = worn_slot_effect(player, "face", "spore_resistance")
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


def tick_proximity_damage(entity: "Entity", engine: "Engine") -> None:
    """Tile-anchored physical radius damage -- the same shape as
    tick_spore_damage but purely physical: no face-slot mask resistance (this
    isn't a respiratory hazard) and no sanity component. The flavor line comes
    from `data["message"]` so one tick serves every "stand near it and it
    hurts" hazard (lurching walls, ...) without a near-identical copy per
    kind."""
    if not _player_in_radius(entity, engine):
        return
    player = engine.player

    if player.fighter is not None:
        player.fighter.take_damage(entity.hazard.severity)
        engine.message_log.add_message(entity.hazard.data.get("message", "It hurts."), color=Color.HAZARD)
        # Hazard damage can kill the player same as combat -- route through
        # the same kill_entity path, or game_over never gets set.
        if player.fighter.hp <= 0:
            engine.kill_entity(player)


def _danger_shade(color: tuple[int, int, int]) -> tuple[int, int, int]:
    """Darkens `color` and pushes it toward pink/red -- the "about to go off"
    warning tint for tick_heater_burst's live phase. Boosts red and blue
    relative to green so an orange heater reads as a dull magenta rather than
    just dimming uniformly."""
    r, g, b = color
    return (min(255, int(r * 0.6 + 40)), int(g * 0.35), min(255, int(b * 0.6 + 40)))


def tick_heater_burst(entity: "Entity", engine: "Engine") -> None:
    """Combusting heater: after a burst it's dormant (`data["grace_period"]`
    turns, default 7) with no risk at all, then goes "live" -- every turn
    after that has a `data["burst_chance"]` (default 25%) chance to burst
    again. This is the heater's own clock: it advances every turn regardless
    of the player's position, same as the radius check below only gates
    whether a burst actually hurts the player, not whether the clock ticks.
    While live, the entity's color shifts to a darker, pinker shade (see
    _danger_shade) as a visible warning; it reverts the instant a burst
    resets the grace timer."""
    data = entity.hazard.data
    if "base_color" not in data:
        data["base_color"] = entity.color

    if data.get("grace_remaining", 0) > 0:
        data["grace_remaining"] -= 1
        entity.color = data["base_color"]
        return

    entity.color = _danger_shade(data["base_color"])
    if engine.rng.random() >= data.get("burst_chance", 0.25):
        return  # rolled safe -- stays live and keeps rolling next turn

    data["grace_remaining"] = data.get("grace_period", 7)
    entity.color = data["base_color"]

    if not _player_in_radius(entity, engine):
        return
    player = engine.player
    if player.fighter is not None:
        player.fighter.take_damage(entity.hazard.severity)
        engine.message_log.add_message(data.get("message", "It bursts."), color=Color.HAZARD)
        # Hazard damage can kill the player same as combat -- route through
        # the same kill_entity path, or game_over never gets set.
        if player.fighter.hp <= 0:
            engine.kill_entity(player)


def tick_sanity_drain_zone(entity: "Entity", engine: "Engine") -> None:
    """Tile-anchored radius zone that erodes only sanity, no HP (see Level
    1.66's Twilight Zones): a dark pocket that's disorienting rather than
    physically dangerous."""
    if not _player_in_radius(entity, engine):
        return
    player = engine.player

    if player.sanity is not None:
        player.sanity.drain(entity.hazard.severity)
        engine.message_log.add_message(entity.hazard.data.get("message", "The dark presses in."), color=Color.HAZARD)


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
        item = pick_loot(engine.rng, data["item_factories"])
        # Put the find straight into the pack rather than dropping it on the
        # tile the player is already standing on -- there it renders hidden
        # under the player and reads as "the message lied, nothing appeared."
        # Fall back to the floor only when there's genuinely no room (shared
        # store-or-drop, same as furniture salvage -- see inventory.store_or_drop).
        store_or_drop(
            player, item, entity.x, entity.y, engine,
            stored_message=f"You dig through the debris and find a {item.name}.",
            dropped_message=f"You find a {item.name}, but your pack is full -- it's at your feet.",
        )
    else:
        if player.sanity is not None:
            player.sanity.drain(entity.hazard.severity)
        engine.message_log.add_message("Something about the debris unsettles you.", color=Color.HAZARD)

    engine.game_map.entities.discard(entity)


def make_spore_zone(*, radius: int = 1, severity: float = 2.0) -> HazardComponent:
    return HazardComponent(SPORE_DAMAGE_KIND, tick_spore_damage, severity=severity, data={"radius": radius})


def make_heat_zone(
    *, radius: int = 1, severity: float = 3.0, grace_period: int = 7, burst_chance: float = 0.25
) -> HazardComponent:
    """Bursts on a random clock rather than constantly -- `grace_period` safe
    turns after each burst, then a `burst_chance` roll every turn after that
    until one hits (see tick_heater_burst)."""
    return HazardComponent(
        "heat_damage",
        tick_heater_burst,
        severity=severity,
        data={
            "radius": radius,
            "message": "The heater bursts, and the heat sears you.",
            "grace_period": grace_period,
            "burst_chance": burst_chance,
        },
    )


def make_impact_zone(*, radius: int = 1, severity: float = 4.0) -> HazardComponent:
    return HazardComponent(
        "impact_damage",
        tick_proximity_damage,
        severity=severity,
        data={"radius": radius, "message": "A wall lurches past, fast enough to break bone."},
    )


def make_twilight_zone(*, radius: int = 2, severity: float = 3.0) -> HazardComponent:
    return HazardComponent(
        "twilight_zone",
        tick_sanity_drain_zone,
        severity=severity,
        data={"radius": radius, "message": "The dark swallows your light and your nerve with it."},
    )


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
