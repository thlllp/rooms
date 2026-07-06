import backrooms.data.registrations  # noqa: F401 -- populates LEVEL_REGISTRY
from backrooms.actions import AutoExploreAction, TravelToAction
from backrooms.engine import Engine
from backrooms.entity.entity import Entity, RenderOrder
from backrooms.systems.auto_explore import find_path_to


def _make_player():
    return Entity(0, 0, char="@", color=(255, 255, 255), name="Player", blocks_movement=True, render_order=RenderOrder.PLAYER)


def test_travel_path_reaches_unexplored_target():
    # Exercises find_path_to directly rather than driving step_travel() for
    # 150+ turns: game_map.entities is a plain set with no __hash__/__eq__
    # override, so process_ai's iteration order over it (and therefore how
    # much of engine.rng's stream each AI-driven entity consumes, and so
    # where they end up wandering) isn't stable across process runs -- an
    # entity occasionally wanders into view over that many turns and trips
    # hostile_visible(), which is a real pre-existing engine-determinism gap
    # but not what this test is about. Pathfinding itself has no such
    # dependency: it only reads game_map tiles/blocking entities, so this is
    # fully deterministic for a given seed.
    engine = Engine(player=_make_player(), seed=1)
    game_map = engine.game_map
    start = (engine.player.x, engine.player.y)

    # The farthest walkable tile that hasn't been seen yet -- travel should
    # still path straight to it, ignoring fog of war entirely.
    target = max(
        ((x, y) for x in range(game_map.width) for y in range(game_map.height) if game_map.tiles["walkable"][x, y]),
        key=lambda pos: abs(pos[0] - start[0]) + abs(pos[1] - start[1]),
    )
    assert not game_map.explored[target]

    path = find_path_to(game_map, start, target)

    assert path is not None
    assert path[-1] == target


def test_travel_and_auto_explore_are_mutually_exclusive():
    engine = Engine(player=_make_player(), seed=1)

    engine.start_auto_explore()
    assert engine.auto_exploring and not engine.traveling

    TravelToAction(engine.player, 1, 1).perform(engine)
    assert engine.traveling and not engine.auto_exploring

    AutoExploreAction(engine.player).perform(engine)
    assert engine.auto_exploring and not engine.traveling


def test_travel_redirects_to_a_new_click_mid_run():
    engine = Engine(player=_make_player(), seed=1)

    TravelToAction(engine.player, 5, 5).perform(engine)
    TravelToAction(engine.player, 9, 9).perform(engine)

    assert engine.traveling
    assert engine.travel_target == (9, 9)


def test_travel_to_unreachable_tile_stops_with_message():
    engine = Engine(player=_make_player(), seed=1)
    game_map = engine.game_map

    # A tile that's never walkable can never be reached.
    wall_tile = next(
        (x, y) for x in range(game_map.width) for y in range(game_map.height) if not game_map.tiles["walkable"][x, y]
    )

    TravelToAction(engine.player, *wall_tile).perform(engine)
    engine.step_travel()

    assert not engine.traveling
    assert "way there" in engine.message_log.tail(1)[0][0]
