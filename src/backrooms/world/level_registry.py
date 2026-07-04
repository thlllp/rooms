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


@dataclass(frozen=True)
class DestinationOption:
    level_id: str
    weight: float = 1.0


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

    def pick_destination(self, rng: random.Random) -> str:
        if len(self.destinations) == 1:
            return self.destinations[0].level_id
        total = sum(d.weight for d in self.destinations)
        roll = rng.uniform(0, total)
        upto = 0.0
        for option in self.destinations:
            upto += option.weight
            if roll <= upto:
                return option.level_id
        return self.destinations[-1].level_id  # float rounding fallback


@dataclass(frozen=True)
class SpawnEntry:
    factory: Callable[[], "Entity"]  # zero-arg factory -- a fresh Entity per call, no shared mutable state
    weight: float = 1.0
    min_count: int = 0
    max_count: int = 1


@dataclass(frozen=True)
class LevelDefinition:
    id: str
    display_name: str
    generator: Callable[["GenerationContext"], "GameMap"]
    ambient_sanity_drain: float = 0.0
    darkness_factor: float = 1.0
    spawn_table: tuple[SpawnEntry, ...] = field(default_factory=tuple)
    hazard_table: tuple[SpawnEntry, ...] = field(default_factory=tuple)
    transition_rules: tuple[TransitionRule, ...] = field(default_factory=tuple)
    is_entry_level: bool = False


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
