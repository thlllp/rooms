"""Dev-mode diagnostics. When Engine is constructed with dev_mode=True,
log_level_overview() prints a plain-text dump to stdout every time a level
loads (initial boot and every noclip, since load_level() is the one path
both go through) -- entrance/exits and every entity's position, for
developer/testing use, not shown anywhere in the actual game UI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backrooms.world.level_registry import LEVEL_REGISTRY, TriggerKind

if TYPE_CHECKING:
    from backrooms.engine import Engine
    from backrooms.entity.entity import Entity
    from backrooms.world.game_map import GameMap
    from backrooms.world.level_registry import LevelDefinition, TransitionRule


def _categorize(entity: "Entity") -> str:
    if entity.ai is not None:
        kind = type(entity.ai).__name__.replace("AI", "") or "Actor"
        return f"npc:{kind.lower()}"
    if entity.hazard is not None:
        return f"hazard:{entity.hazard.kind}"
    if entity.consumable is not None:
        return "item"
    if entity.barter is not None:
        return "vendor"
    if entity.blocks_movement or entity.blocks_sight:
        return "structural"
    return "object"


def _describe_condition(rule: "TransitionRule", game_map: "GameMap") -> str:
    if rule.trigger is TriggerKind.SANITY_BELOW:
        return f"sanity < {rule.sanity_threshold}"
    if rule.trigger is TriggerKind.SANITY_ABOVE:
        return f"sanity > {rule.sanity_threshold}"
    if rule.trigger is TriggerKind.TURN_COUNT_ELAPSED:
        return f"turns_in_level >= {rule.turn_threshold}"
    if rule.trigger is TriggerKind.EVENT_FLAG_SET:
        condition = f"event_flag '{rule.event_flag}' set"
        sources = [
            f"{e.name}@({e.x},{e.y})"
            for e in game_map.entities
            if e.hazard is not None and e.hazard.data.get("event_flag") == rule.event_flag
        ]
        if sources:
            condition += f" [source: {', '.join(sources)}]"
        return condition
    if rule.trigger is TriggerKind.FEATURE_STEPPED_ON:
        return f"standing on tile_id '{rule.feature_tile_id}'"
    if rule.trigger is TriggerKind.RANDOM_CHANCE_PER_TURN:
        return f"random {rule.chance_per_turn:.3%}/turn (min_turns_in_level={rule.min_turns_in_level})"
    return "?"


def _describe_rule(rule: "TransitionRule", game_map: "GameMap") -> str:
    destinations = ", ".join(f"{d.level_id}(w={d.weight:g})" for d in rule.destinations)
    return f"  - {_describe_condition(rule, game_map)} -> {destinations}"


def _incoming_levels(level_id: str) -> list[str]:
    return sorted(
        {
            other_id
            for other_id, other_def in LEVEL_REGISTRY.items()
            if other_id != level_id
            for rule in other_def.transition_rules
            for destination in rule.destinations
            if destination.level_id == level_id
        }
    )


def log_level_overview(engine: "Engine") -> None:
    game_map = engine.game_map
    level_def: "LevelDefinition" = LEVEL_REGISTRY[engine.current_level_id]

    print(f"\n=== DEV MODE: level '{level_def.id}' ({level_def.display_name}) loaded ===")

    print(f"Repeat streak: {engine.level_repeat_streak} (consecutive loads of this same level id)")
    print(f"Entrance (spawn point): {game_map.spawn_point}")
    incoming = _incoming_levels(level_def.id)
    print(f"Entrances (reachable from): {', '.join(incoming) if incoming else '(none -- only reached as the initial level)'}")

    print("Exits:")
    if not level_def.transition_rules:
        print("  (none registered)")
    for rule in level_def.transition_rules:
        print(_describe_rule(rule, game_map))

    entities = sorted((e for e in game_map.entities if e is not engine.player), key=lambda e: (e.x, e.y))
    print(f"Points of interest / NPCs ({len(entities)}):")
    if not entities:
        print("  (none)")
    for entity in entities:
        print(f"  ({entity.x:>2},{entity.y:>2})  {entity.name:<22} [{_categorize(entity)}]")

    print("=" * 60)
