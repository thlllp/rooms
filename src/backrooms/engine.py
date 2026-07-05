from __future__ import annotations

import random

from backrooms.constants import DEFAULT_FOV_RADIUS, MAP_HEIGHT, MAP_WIDTH, UNLIT_FOV_RADIUS, Color
from backrooms.entity.entity import Entity
from backrooms.procgen.spawner import spawn_from_table
from backrooms.systems import auto_explore
from backrooms.systems.ai_system import process_ai
from backrooms.systems.dev_tools import log_level_overview
from backrooms.systems.experience_system import award_xp
from backrooms.systems.hallucination_system import process_hallucinations
from backrooms.systems.hazard_system import process_hazards
from backrooms.systems.npc_social import process_npc_social
from backrooms.systems.sanity_system import process_sanity
from backrooms.systems.transition_system import evaluate_transitions
from backrooms.world.game_map import GameMap
from backrooms.world.level_registry import (
    LEVEL_REGISTRY,
    GenerationContext,
    LevelDefinition,
    LevelStability,
    get_entry_level,
)

# Single source of truth for "which boolean flags are a modal UI screen."
# Read by Engine (to initialize/reset them all in one place, instead of a
# hand-written line per flag that's easy to forget -- see main.py's
# MODE_ALLOWED_ACTIONS, which is keyed by these same names and asserts its
# keys match this tuple exactly).
MODAL_FLAGS = ("show_character_screen", "show_inventory", "look_mode")

# Wall crossed -> which neighboring zone coordinate that leads to, and which
# wall of that neighbor the player arrives at (the opposite side -- walk off
# the right edge of one zone, arrive on the left edge of the next). Used only
# by LevelStability.STABLE levels; see Engine._load_stable_zone.
_WALL_DELTA = {"left": (-1, 0), "right": (1, 0), "top": (0, -1), "bottom": (0, 1)}
_OPPOSITE_WALL = {"left": "right", "right": "left", "top": "bottom", "bottom": "top"}


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

    def __init__(
        self,
        player: Entity,
        *,
        seed: int | None = None,
        dev_mode: bool = False,
        start_level_id: str | None = None,
    ) -> None:
        self.player = player
        self.message_log = MessageLog()
        self.rng = random.Random(seed)
        self.dev_mode = dev_mode
        self.game_map: GameMap
        self.current_level_id: str = ""
        # How many consecutive load_level() calls in a row have loaded the
        # same level id -- 0 the moment a *different* level id loads (see
        # load_level below), so it measures repeats of the current level
        # type, not total visits. Read by callers that want difficulty/
        # content to ramp up the longer you stay on one level type (e.g.
        # spawn_from_table's bonus_max, or a future streak-scaled chance of
        # a door leading to a not-yet-built next level type).
        self.level_repeat_streak = 0
        # LevelStability.STABLE levels are a small grid of zones rather than
        # one map -- each (level_id, zone coordinate) is generated once and
        # cached here; _zone_position tracks which zone coordinate is
        # "current" for each such level_id. See _load_stable_zone.
        self._zone_maps: dict[tuple[str, int, int], GameMap] = {}
        self._zone_position: dict[str, tuple[int, int]] = {}
        # Set by actions.MovementAction._handle_edge the instant the player
        # walks off a wall on a uses_edge_exit level; consumed (and cleared)
        # by the very next load_level() call to pick the right neighboring
        # zone. None means "entering from outside the zone grid entirely"
        # (a different level's door, or the very first visit).
        self.pending_edge_wall: str | None = None
        # Level-scoped state: reset on every load_level() call (initial boot
        # or a noclip transition), never carried between levels.
        self.turns_in_level = 0
        self.event_flags: set[str] = set()
        self.game_over = False
        self._reset_modal_flags()
        self.look_cursor: tuple[int, int] = (0, 0)
        # Not a MODAL_FLAGS entry -- auto-explore isn't a UI screen with an
        # allowed-actions whitelist, it's a continuing mode main.py drives
        # step-by-step (see step_auto_explore) and any keypress interrupts.
        self.auto_exploring = False
        self.auto_explore_steps = 0
        self.load_level(start_level_id if start_level_id is not None else get_entry_level().id)

    def _reset_modal_flags(self) -> None:
        for flag in MODAL_FLAGS:
            setattr(self, flag, False)

    def load_level(self, level_id: str) -> None:
        # Whether this counts as "still repeating the same level type" --
        # read by _load_stable_zone/_generate_map below to decide whether
        # level_repeat_streak should move at all. Computed once, up front,
        # since current_level_id is about to be overwritten either way.
        same_level = level_id == self.current_level_id

        # The player is only ever a member of whichever map is "current" --
        # drop it from the outgoing one before switching, or a STABLE map
        # cached below would keep a stale reference to it forever.
        if hasattr(self, "game_map"):
            self.game_map.entities.discard(self.player)

        level_def = LEVEL_REGISTRY[level_id]
        if level_def.stability is LevelStability.STABLE:
            game_map, spawn_at = self._load_stable_zone(level_id, level_def, same_level)
        else:
            self.level_repeat_streak = self.level_repeat_streak + 1 if same_level else 0
            game_map = self._generate_map(level_def)
            spawn_at = game_map.spawn_point

        self.pending_edge_wall = None
        self.game_map = game_map
        self.current_level_id = level_id
        self.turns_in_level = 0
        self.event_flags = set()
        self.auto_explore_steps = 0
        self._reset_modal_flags()
        self.player.place(*spawn_at)
        game_map.entities.add(self.player)
        self.update_fov()

        if self.dev_mode:
            log_level_overview(self)

    def _generate_map(self, level_def: LevelDefinition) -> GameMap:
        ctx = GenerationContext(rng=self.rng, level_def=level_def, width=MAP_WIDTH, height=MAP_HEIGHT)
        game_map = level_def.generator(ctx)
        spawn_from_table(game_map, level_def.spawn_table, self.rng, bonus_max=self.level_repeat_streak)
        spawn_from_table(game_map, level_def.hazard_table, self.rng, bonus_max=self.level_repeat_streak)
        spawn_from_table(game_map, level_def.furniture_table, self.rng, bonus_max=self.level_repeat_streak)
        return game_map

    def _load_stable_zone(
        self, level_id: str, level_def: LevelDefinition, same_level: bool
    ) -> tuple[GameMap, tuple[int, int]]:
        """A STABLE level is a small grid of zones, not one map: each
        (level_id, zone coordinate) is generated once and cached. Walking
        off an edge moves to the neighboring zone in that direction --
        retracing your steps back the way you came returns to the SAME
        already-generated zone (same remaining entities, same explored
        state); a wall you haven't crossed before generates a brand new
        one. Entering from outside the grid entirely (a different level's
        door, or the very first visit) always lands on the canonical
        (0, 0) zone.

        Bouncing between already-cached zones doesn't touch
        level_repeat_streak at all -- no new content was generated, so it
        isn't "another repeat" of anything. Only a genuine cache miss (a
        wall crossed for the first time) advances it, and only entering
        fresh from a different level (even onto an already-cached zone)
        resets it -- otherwise a later real generation would inherit a
        streak built entirely out of idle back-and-forth navigation."""
        if self.pending_edge_wall is not None and same_level:
            dx, dy = _WALL_DELTA[self.pending_edge_wall]
            prev_zone = self._zone_position.get(level_id, (0, 0))
            zone = (prev_zone[0] + dx, prev_zone[1] + dy)
            entry_wall = _OPPOSITE_WALL[self.pending_edge_wall]
        else:
            zone = (0, 0)
            entry_wall = None

        self._zone_position[level_id] = zone

        cache_key = (level_id, *zone)
        game_map = self._zone_maps.get(cache_key)
        if game_map is None:
            self.level_repeat_streak = self.level_repeat_streak + 1 if same_level else 0
            game_map = self._generate_map(level_def)
            self._zone_maps[cache_key] = game_map
        elif not same_level:
            self.level_repeat_streak = 0

        if entry_wall is not None and entry_wall in game_map.edge_entry_points:
            spawn_at = game_map.edge_entry_points[entry_wall]
        else:
            spawn_at = game_map.spawn_point
        return game_map, spawn_at

    def kill_entity(self, entity: Entity) -> None:
        if entity is self.player:
            if self.game_over:
                return  # Already dead this turn (e.g. a second overlapping hazard) -- don't re-log/re-process.
            self.game_over = True
            self.message_log.add_message("Everything goes quiet.", color=Color.HAZARD)
        else:
            xp_reward = entity.fighter.xp_reward if entity.fighter is not None else 0
            self.game_map.entities.discard(entity)
            self.message_log.add_message(f"{entity.name} collapses and dissolves into the carpet.", color=Color.WARNING)
            award_xp(self, xp_reward)

    def update_fov(self) -> None:
        level_def = LEVEL_REGISTRY[self.current_level_id]
        light = self.player.light_source
        if level_def.is_well_lit:
            # Ambient light, independent of the player's own light source.
            base_radius = DEFAULT_FOV_RADIUS
        elif light is not None and light.is_lit and light.fuel > 0:
            base_radius = min(light.radius, DEFAULT_FOV_RADIUS)
        else:
            base_radius = UNLIT_FOV_RADIUS
        perception_bonus = self.player.perception.acuity if self.player.perception is not None else 0
        radius = max(1, base_radius + perception_bonus)
        self.game_map.compute_fov((self.player.x, self.player.y), radius=radius)

    def start_auto_explore(self) -> None:
        self.auto_exploring = True
        self.auto_explore_steps = 0

    def step_auto_explore(self) -> None:
        auto_explore.step(self)

    def advance_turn(self) -> None:
        """The per-turn pipeline, run once after every dispatched player action."""
        self.turns_in_level += 1
        process_ai(self)
        if self.game_over:
            return
        process_hazards(self)
        if self.game_over:
            return
        process_sanity(self)
        process_hallucinations(self)
        process_npc_social(self)
        if not evaluate_transitions(self):
            self.update_fov()
