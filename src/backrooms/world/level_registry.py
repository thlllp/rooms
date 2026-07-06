"""Data-driven registry of levels/sublevels and the rules that connect them.

Adding a new level or sublevel means writing one more `LevelDefinition` in
`data/registrations.py` -- nothing here or in the engine needs to change.
Transitions between levels ("noclips") are driven entirely by `TransitionRule`
objects attached to each `LevelDefinition`, evaluated fresh every turn by
`systems/transition_system.py`.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Callable

import numpy as np

from backrooms.world import tile_types

if TYPE_CHECKING:
    from backrooms.entity.entity import Entity
    from backrooms.world.game_map import GameMap


class TriggerKind(Enum):
    SANITY_BELOW = auto()
    SANITY_ABOVE = auto()
    TURN_COUNT_ELAPSED = auto()  # since level entry, not a global turn counter
    EVENT_FLAG_SET = auto()  # e.g. an item picked up, a hazard reaching a threshold
    FEATURE_STEPPED_ON = auto()  # player standing on a tile flagged with a given tile_id
    RANDOM_CHANCE_PER_TURN = auto()


class LevelKind(Enum):
    """Tags a level as one of a small number of structural 'kinds'
    generate_office_level knows how to build. A level just carries this tag
    (LevelDefinition.kind) rather than repeating room-size/column/exit
    numbers itself -- see LEVEL_STYLES below for what each kind actually
    means."""

    INDOOR = auto()  # cramped cubicle maze -- level_0/level_1's original feel
    SPACIOUS = auto()  # open, cavernous, fills the map -- level_2's feel
    SETTLEMENT = auto()  # tiny, enclosed safe zone -- a narrower room-size range and far fewer of them than INDOOR


class LevelStability(Enum):
    """Tags whether a level id is regenerated fresh every time it's entered
    (UNSTABLE -- the default, and level_1_office's whole "endless shifting
    maze" identity) or generated once and cached thereafter (STABLE -- the
    same rooms, the same remaining entities, killed enemies stay dead and
    looted items stay gone, every time you come back). See
    Engine.load_level, the only place this is read."""

    UNSTABLE = auto()
    STABLE = auto()


@dataclass(frozen=True)
class LevelStyle:
    room_min_size: int
    room_max_size: int
    # None -> one column at each large room's center. An int instead spaces
    # a grid of columns this many tiles apart across each large room's
    # interior -- a denser "support pillar" cavern feel.
    column_spacing: int | None
    # Opts out of the usual stairs/door exit tile placed in the open floor
    # in favor of walking off the map's edges -- see actions.MovementAction
    # and generator_office.py's forced one-room-per-wall placement. Pair
    # with a TransitionRule keyed on EVENT_FLAG_SET / "map_edge_exited".
    uses_edge_exit: bool
    # Room placement tries much harder to pack the available space full
    # instead of leaving the usual gaps -- see generator_office.py.
    fill_screen: bool
    # Caps how many rooms generate_office_level places, overriding the
    # module's own MAX_ROOMS/MAX_ROOMS_FILL_SCREEN default for every level of
    # this kind. None (the default) leaves that fallback alone.
    # LevelDefinition.max_rooms, if set, wins over this for a one-off level.
    max_rooms: int | None = None


LEVEL_STYLES: dict[LevelKind, LevelStyle] = {
    LevelKind.INDOOR: LevelStyle(
        room_min_size=4, room_max_size=9, column_spacing=None, uses_edge_exit=False, fill_screen=False
    ),
    LevelKind.SPACIOUS: LevelStyle(
        room_min_size=16, room_max_size=28, column_spacing=5, uses_edge_exit=True, fill_screen=True
    ),
    LevelKind.SETTLEMENT: LevelStyle(
        room_min_size=5, room_max_size=8, column_spacing=None, uses_edge_exit=False, fill_screen=False, max_rooms=3
    ),
}


@dataclass(frozen=True)
class DestinationOption:
    level_id: str
    weight: float = 1.0
    # Added to `weight`, scaled by Engine.level_repeat_streak, before picking
    # -- lets a destination become more likely the longer the current level
    # type has repeated in a row (e.g. a door's chance of leading somewhere
    # new growing with how many times you've looped the same level), without
    # the engine needing a special case for any specific level or rule.
    weight_per_streak: float = 0.0


@dataclass(frozen=True)
class TransitionRule:
    trigger: TriggerKind
    destinations: tuple[DestinationOption, ...]  # weighted pool; single entry = deterministic
    sanity_threshold: int | None = None
    turn_threshold: int | None = None
    event_flag: str | None = None
    feature_tile_id: str | None = None
    chance_per_turn: float | None = None
    min_turns_in_level: int = 0
    message: str = ""

    def is_satisfied(self, ctx: "TransitionContext") -> bool:
        if ctx.turns_in_level < self.min_turns_in_level:
            return False
        if self.trigger is TriggerKind.SANITY_BELOW:
            return ctx.player_sanity < self.sanity_threshold
        if self.trigger is TriggerKind.SANITY_ABOVE:
            return ctx.player_sanity > self.sanity_threshold
        if self.trigger is TriggerKind.TURN_COUNT_ELAPSED:
            return ctx.turns_in_level >= self.turn_threshold
        if self.trigger is TriggerKind.EVENT_FLAG_SET:
            return self.event_flag in ctx.event_flags
        if self.trigger is TriggerKind.FEATURE_STEPPED_ON:
            return ctx.tile_under_player_id == self.feature_tile_id
        if self.trigger is TriggerKind.RANDOM_CHANCE_PER_TURN:
            return ctx.rng.random() < self.chance_per_turn
        raise AssertionError(f"Unhandled trigger kind: {self.trigger}")

    def pick_destination(self, rng: random.Random, *, level_repeat_streak: int = 0) -> str:
        if len(self.destinations) == 1:
            return self.destinations[0].level_id
        weights = [max(0.0, d.weight + d.weight_per_streak * level_repeat_streak) for d in self.destinations]
        total = sum(weights)
        if total <= 0:
            return self.destinations[0].level_id
        roll = rng.uniform(0, total)
        upto = 0.0
        for option, w in zip(self.destinations, weights):
            upto += w
            if roll <= upto:
                return option.level_id
        return self.destinations[-1].level_id  # float rounding fallback


@dataclass(frozen=True)
class SpawnEntry:
    factory: Callable[[], "Entity"]  # zero-arg factory -- a fresh Entity per call, no shared mutable state
    weight: float = 1.0
    min_count: int = 0
    max_count: int = 1
    # None -> every instance placed independently anywhere on the map (the
    # original behavior). An int instead places the first instance anywhere,
    # then every further instance within this many tiles of it -- lets one
    # SpawnEntry describe a clustered "encampment" of NPCs rather than
    # scattered individuals. See spawner.spawn_from_table.
    cluster_radius: int | None = None


@dataclass(frozen=True)
class LevelDefinition:
    id: str
    display_name: str
    generator: Callable[["GenerationContext"], "GameMap"]
    ambient_sanity_drain: float = 0.0
    darkness_factor: float = 1.0
    spawn_table: tuple[SpawnEntry, ...] = field(default_factory=tuple)
    hazard_table: tuple[SpawnEntry, ...] = field(default_factory=tuple)
    # Purely decorative clutter (desks, oil drums, ...) -- a third
    # SpawnEntry table resolved the same way as spawn_table/hazard_table
    # (see spawner.spawn_from_table), so it shares that mechanism's
    # bonus_max scaling with Engine.level_repeat_streak for free: entries
    # with max_count=0 place nothing on a fresh visit and start
    # accumulating the more times in a row the level repeats.
    furniture_table: tuple[SpawnEntry, ...] = field(default_factory=tuple)
    transition_rules: tuple[TransitionRule, ...] = field(default_factory=tuple)
    is_entry_level: bool = False
    # Chance generate_office_level embeds a door in a wall instead of placing
    # the usual stairs tile for the level's single stepped-on exit feature --
    # a generator-agnostic knob read via GenerationContext.level_def, so the
    # generator itself never needs to special-case a level id.
    door_exit_chance: float = 0.0
    # Ambient illumination independent of the player's own light source --
    # Engine.update_fov and sanity_system._darkness_drain both check this so
    # a well-lit level gives full FOV and no darkness sanity drain whether or
    # not the player's light is lit/fueled.
    is_well_lit: bool = False
    # Reskin knobs for generate_office_level, read via
    # GenerationContext.level_def -- a level gets a different color palette
    # without the generator special-casing a level id. Defaults match the
    # generator's own previous hardcoded values.
    wall_tile: np.ndarray = field(default_factory=lambda: tile_types.WALL)
    floor_tile: np.ndarray = field(default_factory=lambda: tile_types.FLOOR)
    # Which structural kind of level this is -- room size, column density,
    # exit style, and screen-filling all come from LEVEL_STYLES[kind] rather
    # than being repeated per level (see LevelKind/LevelStyle above).
    kind: LevelKind = LevelKind.INDOOR
    # Whether this level id regenerates fresh every time or is cached and
    # reused (see LevelStability above).
    stability: LevelStability = LevelStability.UNSTABLE
    # The "isolation phenomenon" -- True (the default) means two dialogue-
    # bearing NPCs on this level can never interact with each other, no
    # matter how close together they end up (see systems/npc_social.py).
    # Encampments/colonies are meaningless without this being False, so a
    # level author flips it only once that level is meant to allow them.
    isolation: bool = True
    # Chance generate_office_level embeds a settlement door in a room wall,
    # in addition to (and independent of) the level's normal exit feature --
    # a settlement is a separate small sublevel (LevelKind.SETTLEMENT,
    # TriggerKind.FEATURE_STEPPED_ON on "settlement_door"), not more of the
    # level you're already on. 0.0 (the default) means this level never gets
    # one. See generator_office._place_settlement_door.
    settlement_door_chance: float = 0.0
    # Caps how many rooms generate_office_level places, overriding
    # LEVEL_STYLES[kind]'s own max_rooms/MAX_ROOMS/MAX_ROOMS_FILL_SCREEN cap --
    # None (the default) leaves the style's own cap untouched. An escape
    # hatch for one single level to deviate from every other level sharing
    # its LevelStyle, without needing a whole new LevelKind.
    max_rooms: int | None = None
    # Zero-arg Entity factory placed near a settlement door if one was
    # generated (see settlement_door_chance) -- engine.py stays
    # content-agnostic (it just calls this if set) while the actual Sign
    # entity is defined as regular content in data/registrations.py.
    sign_factory: Callable[[], "Entity"] | None = None
    # If set, generate_office_level reskins one room's interior with this
    # tile instead of the level's own floor_tile -- a small "inn" rest area
    # (see systems/rest_system.py, which passively heals HP/hunger on
    # tile_types.INN_FLOOR) within a level that's otherwise built like any
    # other. None (the default) means this level never gets one. See
    # generator_office._place_inn.
    inn_floor_tile: np.ndarray | None = None

    def feature_trigger_tile_ids(self) -> frozenset[str]:
        """Every tile_id that would fire a FEATURE_STEPPED_ON transition on
        this level -- used by Engine.load_level to avoid ever spawning the
        player back onto one of these (that tile's whole purpose is to fire
        again the instant something stands on it, so restoring a saved
        position onto it would immediately re-trigger the transition on the
        player's very next action)."""
        return frozenset(
            rule.feature_tile_id
            for rule in self.transition_rules
            if rule.trigger is TriggerKind.FEATURE_STEPPED_ON and rule.feature_tile_id is not None
        )


@dataclass
class GenerationContext:
    rng: random.Random
    level_def: LevelDefinition
    width: int
    height: int


@dataclass
class TransitionContext:
    """Snapshot of world state, rebuilt every turn, fed to each rule's is_satisfied()."""

    player_sanity: int
    turns_in_level: int
    event_flags: set[str]
    tile_under_player_id: str | None
    rng: random.Random


LEVEL_REGISTRY: dict[str, LevelDefinition] = {}


def register(level_def: LevelDefinition) -> LevelDefinition:
    if level_def.id in LEVEL_REGISTRY:
        raise ValueError(f"Duplicate level id: {level_def.id}")
    LEVEL_REGISTRY[level_def.id] = level_def
    return level_def


def get_entry_level() -> LevelDefinition:
    for level_def in LEVEL_REGISTRY.values():
        if level_def.is_entry_level:
            return level_def
    raise ValueError("No LevelDefinition is marked is_entry_level=True")
