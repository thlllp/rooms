"""Frontier-BFS pathfinding for auto-explore.

A "frontier" tile is any walkable tile bordering an unexplored one -- heading
toward the nearest one and repeating is a standard, simple way to cover a
level without the player manually retracing already-seen ground.

`step()` performs exactly one such move and is meant to be called once per
real-time tick from main.py's loop while `engine.auto_exploring` is set (see
actions.AutoExploreAction, which just flips that flag on) -- rate-limited
there rather than run in a tight loop, so a single keypress animates
step-by-step instead of resolving instantly.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from backrooms.constants import Color

if TYPE_CHECKING:
    from backrooms.engine import Engine
    from backrooms.world.game_map import GameMap

# Safety cap on total steps per auto-explore run, in case a pathfinding edge
# case ever oscillates -- generous relative to a full map's walkable-tile
# count (~2000-4000 on the current MAP_WIDTH/MAP_HEIGHT) so it never cuts a
# real exploration short. The player can also just press any key to stop.
MAX_STEPS = 5000


def _borders_unexplored(game_map: "GameMap", x: int, y: int) -> bool:
    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
        if game_map.in_bounds(nx, ny) and not game_map.explored[nx, ny]:
            return True
    return False


def find_step_toward_frontier(game_map: "GameMap", start: tuple[int, int]) -> tuple[int, int] | None:
    """BFS from `start` over walkable, unoccupied tiles. Returns the (dx, dy)
    of the first step toward the nearest tile bordering unexplored ground,
    or None if nothing reachable is left to explore."""
    visited = {start}
    parent: dict[tuple[int, int], tuple[int, int]] = {}
    queue: deque[tuple[int, int]] = deque([start])

    while queue:
        current = queue.popleft()
        if current != start and _borders_unexplored(game_map, *current):
            step = current
            while parent[step] != start:
                step = parent[step]
            return step[0] - start[0], step[1] - start[1]

        cx, cy = current
        for neighbor in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if neighbor in visited:
                continue
            nx, ny = neighbor
            if not game_map.is_walkable(nx, ny) or game_map.get_blocking_entity_at(nx, ny) is not None:
                continue
            visited.add(neighbor)
            parent[neighbor] = current
            queue.append(neighbor)

    return None


def hostile_visible(engine: "Engine") -> bool:
    """True if any AI-driven entity is currently in the player's FOV --
    auto-explore stops rather than walking toward or past something
    dangerous unattended."""
    game_map = engine.game_map
    player = engine.player
    return any(e is not player and e.ai is not None and game_map.visible[e.x, e.y] for e in game_map.entities)


def step(engine: "Engine") -> None:
    """One auto-explore move. Clears engine.auto_exploring (with a log
    message) the moment it should stop; otherwise moves the player one tile
    toward the nearest frontier and advances a turn, same as a manual move."""
    engine.auto_explore_steps += 1
    if engine.game_over:
        engine.auto_exploring = False
        return
    if engine.auto_explore_steps > MAX_STEPS:
        engine.message_log.add_message("Auto-explore stops (safety limit reached).", color=Color.GREY)
        engine.auto_exploring = False
        return
    if hostile_visible(engine):
        engine.message_log.add_message("Something's here -- you stop exploring.", color=Color.WARNING)
        engine.auto_exploring = False
        return

    player = engine.player
    move = find_step_toward_frontier(engine.game_map, (player.x, player.y))
    if move is None:
        engine.message_log.add_message("Nothing left to explore here.", color=Color.GREY)
        engine.auto_exploring = False
        return

    dx, dy = move
    level_before = engine.current_level_id
    player.move(dx, dy)
    engine.advance_turn()

    # The frontier BFS treats stairs/doors/map edges as ordinary walkable
    # tiles, so it can walk the player straight through one -- stop rather
    # than silently continuing to explore a level the player never chose to
    # enter (also resets auto_explore_steps for that fresh level, via
    # load_level -- see Engine.load_level).
    if engine.current_level_id != level_before:
        engine.message_log.add_message("Somewhere new now -- you stop exploring.", color=Color.GREY)
        engine.auto_exploring = False
