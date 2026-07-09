"""Frontier-BFS pathfinding for auto-explore, plus click-to-travel to a
specific tile using that same BFS core.

A "frontier" tile is any walkable tile bordering an unexplored one -- heading
toward the nearest one and repeating is a standard, simple way to cover a
level without the player manually retracing already-seen ground. Travel-to-
point instead heads for one exact destination tile -- same walkability/
occupancy rules, but additionally confined to ground the player has already
seen (see _bfs_path's require_explored), since a click can only ever land on
a tile the player is looking at, not a route through fog the player has no
way to know is even open.

`step()`/`step_travel()` each perform exactly one such move and are meant to
be called once per real-time tick from main.py's loop (via
Engine.step_continuing_mode) while engine.auto_exploring/engine.traveling is
set (see actions.AutoExploreAction/TravelToAction, which just call
Engine.start_auto_explore/start_travel -- see engine.py's ContinuingMode) --
rate-limited there rather than run in a tight loop, so a single keypress or
click animates step-by-step instead of resolving instantly.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Callable

from backrooms.constants import Color
from backrooms.entity.components.hazard import hazard_threatens
from backrooms.geometry import chebyshev_distance

if TYPE_CHECKING:
    from backrooms.engine import Engine
    from backrooms.world.game_map import GameMap

# Safety cap on total steps per auto-explore/travel run, in case a
# pathfinding edge case ever oscillates -- generous relative to a full map's
# walkable-tile count (~2000-4000 on the current MAP_WIDTH/MAP_HEIGHT) so it
# never cuts a real run short. The player can also just press any key (or
# click a new destination) to stop.
MAX_STEPS = 5000


def _borders_unexplored(game_map: "GameMap", x: int, y: int) -> bool:
    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
        if game_map.in_bounds(nx, ny) and not game_map.explored[nx, ny]:
            return True
    return False


def _bfs_path(
    game_map: "GameMap",
    start: tuple[int, int],
    is_goal: Callable[[tuple[int, int]], bool],
    *,
    require_explored: bool = False,
) -> list[tuple[int, int]] | None:
    """Shared BFS core for find_step_toward_frontier/find_path_to: walks
    outward from `start` over walkable, unoccupied tiles
    until `is_goal` matches some reachable tile, then walks that tile's
    parent chain back into the full route there (excluding `start`, ending
    with the matched tile). None if no reachable tile (other than `start`
    itself, which never counts) satisfies `is_goal`.

    `require_explored` additionally confines every tile the BFS steps onto
    (including the goal) to game_map.explored -- used by the travel-to-point
    callers so a click can't route through fog the player has never seen,
    while find_step_toward_frontier leaves it off: auto-explore already
    knows the full map's walkability and is finding its way *to* the edge of
    what's explored, not restricted to staying inside it."""
    visited = {start}
    parent: dict[tuple[int, int], tuple[int, int]] = {}
    queue: deque[tuple[int, int]] = deque([start])

    while queue:
        current = queue.popleft()
        if current != start and is_goal(current):
            path = [current]
            while parent[path[-1]] != start:
                path.append(parent[path[-1]])
            path.reverse()
            return path

        cx, cy = current
        for neighbor in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if neighbor in visited:
                continue
            nx, ny = neighbor
            if not game_map.is_walkable(nx, ny) or game_map.get_blocking_entity_at(nx, ny) is not None:
                continue
            if require_explored and not game_map.explored[nx, ny]:
                continue
            visited.add(neighbor)
            parent[neighbor] = current
            queue.append(neighbor)

    return None


def find_step_toward_frontier(game_map: "GameMap", start: tuple[int, int]) -> tuple[int, int] | None:
    """Returns the (dx, dy) of the first step toward the nearest tile
    bordering unexplored ground, or None if nothing reachable is left to
    explore."""
    path = _bfs_path(game_map, start, lambda pos: _borders_unexplored(game_map, *pos))
    return None if path is None else (path[0][0] - start[0], path[0][1] - start[1])


def find_path_to(
    game_map: "GameMap", start: tuple[int, int], target: tuple[int, int]
) -> list[tuple[int, int]] | None:
    """The full route (excluding `start`, ending with `target`) to a clicked
    destination -- step_travel consumes/refreshes it one move at a time and
    rendering/ui.render_travel_path previews the same cached list. Confined
    to already-explored ground (see _bfs_path's require_explored) -- None if
    `target` is unreachable that way or is `start` itself."""
    return _bfs_path(game_map, start, lambda pos: pos == target, require_explored=True)


def hostile_visible(engine: "Engine") -> bool:
    """True if any AI-driven entity is currently in the player's FOV --
    auto-explore stops rather than walking toward or past something
    dangerous unattended."""
    game_map = engine.game_map
    player = engine.player
    return any(e is not player and e.ai is not None and game_map.visible[e.x, e.y] for e in game_map.entities)


# Extra buffer (in tiles, beyond the hazard's own damage radius) that counts
# as "nearby" for hazard_nearby below -- one tile of warning before a step
# would actually put the player in range, same spirit as hostile_visible
# stopping short of a fight rather than mid-hit.
HAZARD_WARNING_BUFFER = 1


def hazard_nearby(engine: "Engine", from_pos: tuple[int, int], next_pos: tuple[int, int]) -> bool:
    """True if stepping from `from_pos` to `next_pos` would close in on an
    area hazard (spore cloud, heater, lurching wall, ... -- see
    HazardComponent.is_area) the player knows about, landing within
    HAZARD_WARNING_BUFFER tiles of its damage radius -- auto-explore/travel
    stop before wandering into (or right up to the edge of) a damage zone
    unattended, rather than after taking the hit.

    "Knows about" means the hazard's tile has been explored, not that it's
    currently in FOV: damage doesn't care about visibility (see hazard.py's
    _player_in_radius), so a remembered zone just outside tonight's light
    radius still stops the run. A hazard on ground never seen at all is the
    player's risk to take, same as walking there by hand. Only steps that
    strictly decrease the distance to the hazard count, so a player already
    inside a zone (or its buffer) can still auto-walk out instead of being
    stopped on the spot every try. Tile-only hazards (is_area False: unstable
    floors) aren't something you "walk into" the same way and are left out
    here -- debris piles/toolboxes aren't hazards at all anymore (see
    components.debris/container), just ordinary blocks_movement obstacles the
    pathfinding BFS already routes around (see _bfs_path)."""
    game_map = engine.game_map
    return any(
        e.hazard is not None
        and e.hazard.is_area
        and game_map.explored[e.x, e.y]
        and hazard_threatens(e, next_pos[0], next_pos[1], buffer=HAZARD_WARNING_BUFFER)
        and chebyshev_distance(next_pos[0], next_pos[1], e.x, e.y) < chebyshev_distance(from_pos[0], from_pos[1], e.x, e.y)
        for e in game_map.entities
    )


def _stops_for_hazard(engine: "Engine", next_pos: tuple[int, int], doing: str) -> bool:
    """Shared hazard gate for step()/step_travel(): if moving the player onto
    `next_pos` would close in on a known hazard (see hazard_nearby), log the
    warning, stop the continuing mode, and report True so the caller returns
    without moving."""
    player = engine.player
    if hazard_nearby(engine, (player.x, player.y), next_pos):
        engine.message_log.add_message(f"A hazard's too close -- you stop {doing}.", color=Color.WARNING)
        engine.stop_continuing_mode()
        return True
    return False


def step(engine: "Engine") -> None:
    """One auto-explore move. Stops the continuing mode (with a log message)
    the moment it should stop; otherwise moves the player one tile toward
    the nearest frontier and advances a turn, same as a manual move."""
    engine.continuing_steps += 1
    if engine.game_over:
        engine.stop_continuing_mode()
        return
    if engine.continuing_steps > MAX_STEPS:
        engine.message_log.add_message("Auto-explore stops (safety limit reached).", color=Color.GREY)
        engine.stop_continuing_mode()
        return
    if hostile_visible(engine):
        engine.message_log.add_message("Something's here -- you stop exploring.", color=Color.WARNING)
        engine.stop_continuing_mode()
        return

    player = engine.player
    move = find_step_toward_frontier(engine.game_map, (player.x, player.y))
    if move is None:
        engine.message_log.add_message("Nothing left to explore here.", color=Color.GREY)
        engine.stop_continuing_mode()
        return

    dx, dy = move
    if _stops_for_hazard(engine, (player.x + dx, player.y + dy), "exploring"):
        return

    level_before = engine.current_level_id
    player.move(dx, dy)
    engine.advance_turn()

    # The frontier BFS treats stairs/doors/map edges as ordinary walkable
    # tiles, so it can walk the player straight through one -- stop rather
    # than silently continuing to explore a level the player never chose to
    # enter (also resets continuing_steps for that fresh level, via
    # load_level -- see Engine.load_level).
    if engine.current_level_id != level_before:
        engine.message_log.add_message("Somewhere new now -- you stop exploring.", color=Color.GREY)
        engine.stop_continuing_mode()


def step_travel(engine: "Engine") -> None:
    """One travel-to-point move -- same step-by-step, interruptible shape as
    step(), but heading toward engine.travel_target instead of the nearest
    unexplored frontier, and consuming/refreshing engine.travel_path rather
    than pathfinding fresh from scratch (rendering/ui.py's render_travel_path
    reads that same cached route to preview it, so this is the only BFS run
    per tick, not two)."""
    engine.continuing_steps += 1
    if engine.game_over:
        engine.stop_continuing_mode()
        return
    if engine.continuing_steps > MAX_STEPS:
        engine.message_log.add_message("Travel stops (safety limit reached).", color=Color.GREY)
        engine.stop_continuing_mode()
        return
    if hostile_visible(engine):
        engine.message_log.add_message("Something's here -- you stop traveling.", color=Color.WARNING)
        engine.stop_continuing_mode()
        return

    player = engine.player
    if (player.x, player.y) == engine.travel_target:
        engine.stop_continuing_mode()
        return

    path = engine.travel_path
    if not path:
        engine.message_log.add_message("Can't find a way there.", color=Color.GREY)
        engine.stop_continuing_mode()
        return

    if _stops_for_hazard(engine, path[0], "traveling"):
        return

    dx, dy = path[0][0] - player.x, path[0][1] - player.y
    level_before = engine.current_level_id
    player.move(dx, dy)
    engine.advance_turn()

    # Same reasoning as step()'s own check: don't keep traveling into a level
    # the player never chose to enter just because the path crossed its exit.
    if engine.current_level_id != level_before:
        engine.message_log.add_message("Somewhere new now -- you stop traveling.", color=Color.GREY)
        engine.stop_continuing_mode()
        return

    # Refreshed from the player's new position for the next tick's render
    # (preview) and step (movement) to share -- see the docstring above.
    engine.travel_path = find_path_to(engine.game_map, (player.x, player.y), engine.travel_target)
