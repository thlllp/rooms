import backrooms.data.registrations  # noqa: F401 -- populates LEVEL_REGISTRY
from backrooms.engine import Engine
from backrooms.entity.components.hazard import make_spore_zone
from backrooms.entity.entity import Entity, RenderOrder
from backrooms.systems import auto_explore


def _make_player():
    return Entity(0, 0, char="@", color=(255, 255, 255), name="Player", blocks_movement=True, render_order=RenderOrder.PLAYER)


def _make_spore(x, y, *, radius=1):
    return Entity(x, y, char='"', color=(0, 0, 0), name="Spore Cloud", render_order=RenderOrder.HAZARD, hazard=make_spore_zone(radius=radius, severity=3.0))


def test_hazard_nearby_true_within_radius_plus_buffer():
    engine = Engine(player=_make_player(), seed=1)
    spore = _make_spore(10, 10, radius=1)
    engine.game_map.entities.add(spore)
    engine.game_map.visible[10, 10] = True

    assert auto_explore.hazard_nearby(engine, (12, 10))  # radius 1 + buffer 1 = 2 tiles away


def test_hazard_nearby_false_beyond_buffer():
    engine = Engine(player=_make_player(), seed=1)
    spore = _make_spore(10, 10, radius=1)
    engine.game_map.entities.add(spore)
    engine.game_map.visible[10, 10] = True

    assert not auto_explore.hazard_nearby(engine, (13, 10))  # 3 tiles away


def test_hazard_nearby_false_when_not_visible():
    engine = Engine(player=_make_player(), seed=1)
    spore = _make_spore(10, 10, radius=1)
    engine.game_map.entities.add(spore)
    engine.game_map.visible[10, 10] = False  # not currently in FOV

    assert not auto_explore.hazard_nearby(engine, (10, 10))


def test_hazard_nearby_ignores_radiusless_hazards():
    from backrooms.entity.components.hazard import make_unstable_floor

    engine = Engine(player=_make_player(), seed=1)
    floor = Entity(10, 10, char="=", color=(0, 0, 0), name="Unstable Floor", render_order=RenderOrder.HAZARD, hazard=make_unstable_floor())
    engine.game_map.entities.add(floor)
    engine.game_map.visible[10, 10] = True

    assert not auto_explore.hazard_nearby(engine, (10, 10))


def test_auto_explore_stops_before_stepping_into_hazard_range(monkeypatch):
    engine = Engine(player=_make_player(), seed=1)
    player = engine.player
    player.place(5, 5)
    spore = _make_spore(6, 5, radius=1)
    engine.game_map.entities.add(spore)
    engine.game_map.visible[6, 5] = True

    # Isolate the hazard gate from procgen's frontier choice (see
    # test_travel.py's note on why frontier direction isn't deterministic
    # across a freshly generated map) by forcing the "next step" straight at
    # the hazard, same as real pathfinding would if that's the direction it
    # picked.
    monkeypatch.setattr(auto_explore, "find_step_toward_frontier", lambda game_map, start: (1, 0))
    engine.start_auto_explore()

    auto_explore.step(engine)

    assert (player.x, player.y) == (5, 5)  # never moved
    assert not engine.auto_exploring
    assert "too close" in engine.message_log.tail(1)[0][0]


def test_travel_stops_before_stepping_into_hazard_range():
    engine = Engine(player=_make_player(), seed=1)
    player = engine.player
    player.place(5, 5)
    spore = _make_spore(6, 5, radius=1)
    engine.game_map.entities.add(spore)
    engine.game_map.visible[6, 5] = True

    engine.start_travel((9, 5))
    engine.travel_path = [(6, 5), (7, 5), (8, 5), (9, 5)]

    auto_explore.step_travel(engine)

    assert (player.x, player.y) == (5, 5)  # never moved
    assert not engine.traveling
    assert "too close" in engine.message_log.tail(1)[0][0]
