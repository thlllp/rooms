"""The content file: every level/sublevel the game knows about is declared
here as one LevelDefinition each. Importing this module populates
world.level_registry.LEVEL_REGISTRY as a side effect -- the engine never
references a generator function directly, only registry lookups by id.
"""

from __future__ import annotations

from backrooms.constants import Color
from backrooms.entity.components.ai import WanderingAI
from backrooms.entity.components.fighter import Fighter
from backrooms.entity.components.hazard import make_spore_zone, make_unstable_floor
from backrooms.entity.entity import Entity, RenderOrder
from backrooms.procgen.generator_flooded import generate_flooded_level
from backrooms.procgen.generator_office import generate_office_level
from backrooms.world.level_registry import (
    DestinationOption,
    LevelDefinition,
    SpawnEntry,
    TransitionRule,
    TriggerKind,
    register,
)


def _spawn_spore_zone() -> Entity:
    return Entity(
        0,
        0,
        char='"',
        color=Color.HAZARD,
        name="Spore Cloud",
        render_order=RenderOrder.HAZARD,
        hazard=make_spore_zone(radius=1, severity=2.0),
    )


def _spawn_unstable_floor() -> Entity:
    return Entity(
        0,
        0,
        char="=",
        color=Color.WARNING,
        name="Unstable Floor",
        render_order=RenderOrder.HAZARD,
        hazard=make_unstable_floor(collapse_threshold=4, event_flag="floor_collapsed"),
    )


def _spawn_wanderer() -> Entity:
    return Entity(
        0,
        0,
        char="?",
        color=(150, 130, 170),
        name="Wandering Presence",
        blocks_movement=True,
        render_order=RenderOrder.ACTOR,
        causes_dread=True,
        dread_radius=5,
        ai=WanderingAI(perception_radius=8),
        fighter=Fighter(hp=1, defense=0, power=0),
    )


LEVEL_OFFICE = register(
    LevelDefinition(
        id="level_0_office",
        display_name="Level 0",
        generator=generate_office_level,
        ambient_sanity_drain=0.05,
        darkness_factor=1.0,
        is_entry_level=True,
        spawn_table=(SpawnEntry(factory=_spawn_wanderer, weight=1.0, min_count=1, max_count=1),),
        hazard_table=(
            SpawnEntry(factory=_spawn_spore_zone, weight=1.0, min_count=1, max_count=2),
            SpawnEntry(factory=_spawn_unstable_floor, weight=1.0, min_count=1, max_count=1),
        ),
        transition_rules=(
            TransitionRule(
                trigger=TriggerKind.EVENT_FLAG_SET,
                event_flag="floor_collapsed",
                destinations=(DestinationOption("level_flooded", 1.0),),
                message="The floor gives way beneath your feet entirely.",
            ),
            TransitionRule(
                trigger=TriggerKind.SANITY_BELOW,
                sanity_threshold=15,
                destinations=(DestinationOption("level_flooded", 1.0),),
                message="The hum grows deafening. The floor gives way beneath you.",
            ),
            TransitionRule(
                trigger=TriggerKind.RANDOM_CHANCE_PER_TURN,
                chance_per_turn=0.002,
                min_turns_in_level=50,
                destinations=(
                    DestinationOption("level_flooded", 0.7),
                    DestinationOption("level_0_office", 0.3),
                ),
                message="You blink, and nothing is where it was.",
            ),
        ),
    )
)

LEVEL_FLOODED = register(
    LevelDefinition(
        id="level_flooded",
        display_name="The Flooded Sublevel",
        generator=generate_flooded_level,
        ambient_sanity_drain=0.15,
        darkness_factor=1.4,
        transition_rules=(
            TransitionRule(
                trigger=TriggerKind.TURN_COUNT_ELAPSED,
                turn_threshold=300,
                destinations=(DestinationOption("level_0_office", 1.0),),
                message="Something forces you out.",
            ),
        ),
    )
)
