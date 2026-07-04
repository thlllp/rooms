from __future__ import annotations

import random

from backrooms.constants import DEFAULT_FOV_RADIUS, MAP_HEIGHT, MAP_WIDTH, UNLIT_FOV_RADIUS
from backrooms.entity.entity import Entity
from backrooms.procgen.spawner import spawn_from_table
from backrooms.systems.ai_system import process_ai
from backrooms.systems.hallucination_system import process_hallucinations
from backrooms.systems.hazard_system import process_hazards
from backrooms.systems.sanity_system import process_sanity
from backrooms.systems.transition_system import evaluate_transitions
from backrooms.world.game_map import GameMap
from backrooms.world.level_registry import LEVEL_REGISTRY, GenerationContext, get_entry_level


class MessageLog:
    def __init__(self) -> None:
        self.messages: list[tuple[str, tuple[int, int, int]]] = []

    def add_message(self, text: str, color: tuple[int, int, int] = (200, 200, 200)) -> None:
        self.messages.append((text, color))

    def tail(self, count: int) -> list[tuple[str, tuple[int, int, int]]]:
        return self.messages[-count:]


class Engine:
    """Owns the world's mutable state and the level registry indirection.

    `load_level` is the single path both the initial boot and (from Step 4
    onward) noclip transitions use to enter a level -- there is no separate
    "startup" map-construction code path to keep in sync with transitions.
    """

    def __init__(self, player: Entity, *, seed: int | None = None) -> None:
        self.player = player
        self.message_log = MessageLog()
        self.rng = random.Random(seed)
        self.game_map: GameMap
        self.current_level_id: str = ""
        # Level-scoped state: reset on every load_level() call (initial boot
        # or a noclip transition), never carried between levels.
        self.turns_in_level = 0
        self.event_flags: set[str] = set()
        self.load_level(get_entry_level().id)

    def load_level(self, level_id: str) -> None:
        level_def = LEVEL_REGISTRY[level_id]
        ctx = GenerationContext(rng=self.rng, level_def=level_def, width=MAP_WIDTH, height=MAP_HEIGHT)
        game_map = level_def.generator(ctx)

        spawn_from_table(game_map, level_def.spawn_table, self.rng)
        spawn_from_table(game_map, level_def.hazard_table, self.rng)

        self.game_map = game_map
        self.current_level_id = level_id
        self.turns_in_level = 0
        self.event_flags = set()
        self.player.place(*game_map.spawn_point)
        game_map.entities.add(self.player)
        self.update_fov()

    def update_fov(self) -> None:
        light = self.player.light_source
        if light is not None and light.is_lit and light.fuel > 0:
            radius = min(light.radius, DEFAULT_FOV_RADIUS)
        else:
            radius = UNLIT_FOV_RADIUS
        self.game_map.compute_fov((self.player.x, self.player.y), radius=radius)

    def advance_turn(self) -> None:
        """The per-turn pipeline, run once after every dispatched player action."""
        self.turns_in_level += 1
        process_ai(self)
        process_hazards(self)
        process_sanity(self)
        process_hallucinations(self)
        if not evaluate_transitions(self):
            self.update_fov()
