"""Low-sanity perception effects. Split into two halves:

- `process_hallucinations` (called once per turn, in Engine.advance_turn):
  spawns/expires fake "ghost" entities and injects fabricated log lines.
  Fake entities are real Entity objects added to game_map.entities, flagged
  `is_hallucination=True` and rendered identically to real ones -- the
  player can't tell them apart by appearance, only by behavior over a few
  turns (they don't react, and they vanish).

- `apply_visual_distortion` (called once per frame, in renderer.render_all,
  after the true-state map/entity draw and before the console is presented):
  mutates the already-drawn console buffer directly. It never touches
  GameMap or game state, so its effects are gone by the next frame unless
  reapplied -- a flicker, not a persisted corruption.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from backrooms.constants import Color
from backrooms.entity.entity import Entity, RenderOrder
from backrooms.world import tile_types

if TYPE_CHECKING:
    import tcod.console

    from backrooms.engine import Engine

MAX_HALLUCINATIONS = 2
HALLUCINATION_SPAWN_CHANCE = 0.05
HALLUCINATION_MIN_LIFESPAN = 2
HALLUCINATION_MAX_LIFESPAN = 5
FABRICATED_MESSAGE_CHANCE = 0.04

FABRICATED_MESSAGES = (
    "You hear footsteps behind you.",
    "Something breathes, close by.",
    "A door closes somewhere that has no doors.",
    "You could swear that wall just moved.",
    "The hum changes pitch, like it noticed you.",
)

FLICKER_CHANCE = 0.4
FLICKER_SAMPLE_SIZE = 3
FLICKER_GLYPHS = tuple(ord(c) for c in ".,;:'\"")

CORRUPT_CHANCE = 0.5
CORRUPT_SAMPLE_SIZE = 2


def process_hallucinations(engine: "Engine") -> None:
    player = engine.player
    if player.sanity is None:
        return

    game_map = engine.game_map
    _expire_hallucinations(engine)

    band = player.sanity.band
    if not band.hallucinations:
        return

    rng = engine.rng
    existing = sum(1 for e in game_map.entities if e.is_hallucination)
    if existing < MAX_HALLUCINATIONS and rng.random() < HALLUCINATION_SPAWN_CHANCE:
        tile = _random_visible_tile(engine, rng)
        if tile is not None:
            lifespan = rng.randint(HALLUCINATION_MIN_LIFESPAN, HALLUCINATION_MAX_LIFESPAN)
            ghost = Entity(
                *tile,
                char=rng.choice("?!&%"),
                color=(180, 150, 190),
                name="???",
                render_order=RenderOrder.ACTOR,
                is_hallucination=True,
                hallucination_expires_at=engine.turns_in_level + lifespan,
            )
            game_map.entities.add(ghost)

    if rng.random() < FABRICATED_MESSAGE_CHANCE:
        engine.message_log.add_message(rng.choice(FABRICATED_MESSAGES), color=Color.NOCLIP_FLAVOR)


def _expire_hallucinations(engine: "Engine") -> None:
    game_map = engine.game_map
    expired = [
        e
        for e in game_map.entities
        if e.is_hallucination and e.hallucination_expires_at is not None and engine.turns_in_level >= e.hallucination_expires_at
    ]
    for entity in expired:
        game_map.entities.discard(entity)


def _random_visible_tile(engine: "Engine", rng) -> tuple[int, int] | None:  # noqa: ANN001
    game_map = engine.game_map
    candidates = list(zip(*np.nonzero(game_map.visible & game_map.tiles["walkable"])))
    candidates = [(x, y) for x, y in candidates if (x, y) != (engine.player.x, engine.player.y)]
    if not candidates:
        return None
    return rng.choice(candidates)


def apply_visual_distortion(console: "tcod.console.Console", engine: "Engine") -> None:
    player = engine.player
    if player.sanity is None:
        return

    band = player.sanity.band
    rng = engine.rng
    game_map = engine.game_map

    if band.perception_distortion and rng.random() < FLICKER_CHANCE:
        candidates = list(zip(*np.nonzero(game_map.visible & game_map.tiles["walkable"])))
        for x, y in rng.sample(candidates, k=min(FLICKER_SAMPLE_SIZE, len(candidates))):
            console.rgb[x, y]["ch"] = rng.choice(FLICKER_GLYPHS)

    if band.hallucinations and rng.random() < CORRUPT_CHANCE:
        remembered_only = list(zip(*np.nonzero(game_map.explored & ~game_map.visible)))
        for x, y in rng.sample(remembered_only, k=min(CORRUPT_SAMPLE_SIZE, len(remembered_only))):
            fake_tile = tile_types.WALL if game_map.tiles["walkable"][x, y] else tile_types.FLOOR
            console.rgb[x, y] = fake_tile["dark"]
