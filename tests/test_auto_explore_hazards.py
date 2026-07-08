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
    engine.game_map.explored[10, 10] = True

    # Stepping from 3 tiles away to 2 tiles away: radius 1 + buffer 1 = 2.
    assert auto_explore.hazard_nearby(engine, (13, 10), (12, 10))


def test_hazard_nearby_false_beyond_buffer():
    engine = Engine(player=_make_player(), seed=1)
    spore = _make_spore(10, 10, radius=1)
    engine.game_map.entities.add(spore)
    engine.game_map.explored[10, 10] = True

    assert not auto_explore.hazard_nearby(engine, (14, 10), (13, 10))  # lands 3 tiles away


def test_hazard_nearby_false_when_unexplored():
    engine = Engine(player=_make_player(), seed=1)
    spore = _make_spore(10, 10, radius=1)
    engine.game_map.entities.add(spore)
    engine.game_map.explored[10, 10] = False  # ground the player has never seen

    assert not auto_explore.hazard_nearby(engine, (13, 10), (12, 10))


def test_hazard_nearby_true_when_explored_but_not_currently_visible():
    # Damage ignores FOV (see hazard.py's _player_in_radius), so a remembered
    # zone that's slipped out of tonight's light radius still stops the run.
    engine = Engine(player=_make_player(), seed=1)
    spore = _make_spore(10, 10, radius=1)
    engine.game_map.entities.add(spore)
    engine.game_map.explored[10, 10] = True
    engine.game_map.visible[10, 10] = False

    assert auto_explore.hazard_nearby(engine, (13, 10), (12, 10))


def test_hazard_nearby_false_when_stepping_away():
    # A player already inside the zone (or its buffer) must be able to
    # auto-walk out: only steps that close the distance count.
    engine = Engine(player=_make_player(), seed=1)
    spore = _make_spore(10, 10, radius=1)
    engine.game_map.entities.add(spore)
    engine.game_map.explored[10, 10] = True

    assert not auto_explore.hazard_nearby(engine, (11, 10), (12, 10))  # inside radius, moving out
    assert not auto_explore.hazard_nearby(engine, (12, 10), (12, 11))  # along the buffer edge, no closer


def test_hazard_nearby_ignores_radiusless_hazards():
    from backrooms.entity.components.hazard import make_unstable_floor

    engine = Engine(player=_make_player(), seed=1)
    floor = Entity(10, 10, char="=", color=(0, 0, 0), name="Unstable Floor", render_order=RenderOrder.HAZARD, hazard=make_unstable_floor())
    engine.game_map.entities.add(floor)
    engine.game_map.explored[10, 10] = True

    assert not auto_explore.hazard_nearby(engine, (11, 10), (10, 10))


def test_auto_explore_stops_before_stepping_into_hazard_range(monkeypatch):
    engine = Engine(player=_make_player(), seed=1)
    player = engine.player
    player.place(5, 5)
    spore = _make_spore(6, 5, radius=1)
    engine.game_map.entities.add(spore)
    engine.game_map.explored[6, 5] = True

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
    engine.game_map.explored[6, 5] = True

    engine.start_travel((9, 5))
    engine.travel_path = [(6, 5), (7, 5), (8, 5), (9, 5)]

    auto_explore.step_travel(engine)

    assert (player.x, player.y) == (5, 5)  # never moved
    assert not engine.traveling
    assert "too close" in engine.message_log.tail(1)[0][0]


def test_travel_can_walk_out_of_a_hazard_zone():
    # Starting inside the damage zone is exactly when the player most wants
    # travel to work -- the gate must not trap them on the spot.
    engine = Engine(player=_make_player(), seed=1)
    player = engine.player
    player.place(5, 5)
    spore = _make_spore(5, 5, radius=1)
    engine.game_map.entities.add(spore)
    engine.game_map.explored[5, 5] = True

    engine.start_travel((8, 5))
    engine.travel_path = [(6, 5), (7, 5), (8, 5)]

    auto_explore.step_travel(engine)

    assert (player.x, player.y) == (6, 5)  # stepped away, not stopped
