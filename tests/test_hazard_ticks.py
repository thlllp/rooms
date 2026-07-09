import random

from backrooms.entity.components.fighter import Fighter
from backrooms.entity.components.hazard import (
    make_heat_zone,
    make_impact_zone,
    make_spore_zone,
    make_unstable_floor,
    tick_heater_burst,
    tick_proximity_damage,
    tick_spore_damage,
    tick_unstable_floor,
)
from backrooms.entity.components.light_source import LightSourceComponent, tick_light_fuel
from backrooms.entity.components.sanity import SanityComponent
from backrooms.entity.entity import Entity, RenderOrder
from backrooms.world.game_map import GameMap


class FakeLog:
    def __init__(self):
        self.messages = []

    def add_message(self, text, color=None):
        self.messages.append(text)


class FakeEngine:
    def __init__(self, player):
        self.player = player
        self.message_log = FakeLog()
        self.event_flags = set()
        self.game_over = False
        self.rng = random.Random(0)
        self.game_map = GameMap(20, 20)

    def kill_entity(self, entity):
        if entity is self.player:
            self.game_over = True
            self.message_log.add_message("Everything goes quiet.")


def _make_player(**kwargs):
    return Entity(0, 0, char="@", color=(255, 255, 255), name="Player", render_order=RenderOrder.PLAYER, **kwargs)


def test_light_fuel_burns_down_each_tick():
    player = _make_player(light_source=LightSourceComponent(max_fuel=10.0, burn_rate=1.0))
    tick_light_fuel(player, FakeEngine(player))
    assert player.light_source.fuel == 9.0
    assert player.light_source.is_lit


def test_light_fuel_extinguishes_at_zero_and_logs_message():
    player = _make_player(light_source=LightSourceComponent(max_fuel=1.0, burn_rate=1.0))
    engine = FakeEngine(player)
    tick_light_fuel(player, engine)
    assert player.light_source.fuel == 0.0
    assert not player.light_source.is_lit
    assert any("sputters out" in m for m in engine.message_log.messages)


def test_light_fuel_does_nothing_once_unlit():
    player = _make_player(light_source=LightSourceComponent(max_fuel=5.0, burn_rate=1.0))
    player.light_source.is_lit = False
    engine = FakeEngine(player)
    tick_light_fuel(player, engine)
    assert player.light_source.fuel == 5.0  # unchanged


def test_spore_damage_applies_within_radius():
    player = _make_player(fighter=Fighter(hp=10), sanity=SanityComponent(max_sanity=100))
    player.place(5, 5)
    spore = Entity(5, 6, char='"', color=(0, 0, 0), name="Spore", render_order=RenderOrder.HAZARD, hazard=make_spore_zone(radius=1, severity=3.0))
    engine = FakeEngine(player)

    tick_spore_damage(spore, engine)

    assert player.fighter.hp == 7
    assert player.sanity.current == 98.5  # severity * 0.5 drained
    assert any("Spores" in m for m in engine.message_log.messages)


def test_spore_damage_kills_player_and_sets_game_over():
    player = _make_player(fighter=Fighter(hp=2), sanity=SanityComponent(max_sanity=100))
    player.place(5, 5)
    spore = Entity(5, 6, char='"', color=(0, 0, 0), name="Spore", render_order=RenderOrder.HAZARD, hazard=make_spore_zone(radius=1, severity=3.0))
    engine = FakeEngine(player)

    tick_spore_damage(spore, engine)

    assert player.fighter.hp == 0
    assert engine.game_over


def test_spore_damage_no_effect_outside_radius():
    player = _make_player(fighter=Fighter(hp=10))
    player.place(0, 0)
    spore = Entity(10, 10, char='"', color=(0, 0, 0), name="Spore", render_order=RenderOrder.HAZARD, hazard=make_spore_zone(radius=1, severity=3.0))
    engine = FakeEngine(player)

    tick_spore_damage(spore, engine)

    assert player.fighter.hp == 10


def test_spore_damage_skips_hp_when_no_fighter_component():
    player = _make_player(sanity=SanityComponent(max_sanity=100))
    player.place(5, 5)
    spore = Entity(5, 5, char='"', color=(0, 0, 0), name="Spore", render_order=RenderOrder.HAZARD, hazard=make_spore_zone(radius=0, severity=3.0))
    engine = FakeEngine(player)

    tick_spore_damage(spore, engine)  # should not raise despite player.fighter is None

    assert player.sanity.current == 98.5


def test_unstable_floor_sets_event_flag_after_threshold_steps():
    player = _make_player()
    player.place(2, 2)
    floor_hazard = Entity(2, 2, char="=", color=(0, 0, 0), name="Unstable Floor", render_order=RenderOrder.HAZARD, hazard=make_unstable_floor(collapse_threshold=3, event_flag="floor_collapsed"))
    engine = FakeEngine(player)

    tick_unstable_floor(floor_hazard, engine)
    assert "floor_collapsed" not in engine.event_flags
    tick_unstable_floor(floor_hazard, engine)
    assert "floor_collapsed" not in engine.event_flags
    tick_unstable_floor(floor_hazard, engine)
    assert "floor_collapsed" in engine.event_flags


class _ScriptedRng:
    """Feeds fixed .random() results in order -- lets a heater's burst roll
    be pinned to "safe" or "burst" instead of depending on real randomness."""

    def __init__(self, values):
        self._values = list(values)

    def random(self):
        return self._values.pop(0)


def test_heater_bursts_then_stays_dormant_through_its_grace_period():
    player = _make_player(fighter=Fighter(hp=100))
    player.place(5, 5)
    base_color = (230, 110, 40)
    heater = Entity(
        5,
        6,
        char="&",
        color=base_color,
        name="Combusting Heater",
        render_order=RenderOrder.HAZARD,
        hazard=make_heat_zone(radius=1, severity=5.0, grace_period=3, burst_chance=1.0),
    )
    engine = FakeEngine(player)

    # Starts live (no prior burst to be dormant from) -- bursts immediately
    # since burst_chance=1.0, then reverts to its base color.
    tick_heater_burst(heater, engine)
    assert player.fighter.hp == 95
    assert heater.color == base_color

    # Three dormant grace turns: no damage, no color change.
    for _ in range(3):
        tick_heater_burst(heater, engine)
    assert player.fighter.hp == 95
    assert heater.color == base_color

    # Grace elapsed -- live again, and bursts again immediately.
    tick_heater_burst(heater, engine)
    assert player.fighter.hp == 90


def test_heater_shows_danger_color_while_live_and_rolling_before_bursting():
    player = _make_player(fighter=Fighter(hp=100))
    player.place(5, 5)
    base_color = (230, 110, 40)
    heater = Entity(
        5,
        6,
        char="&",
        color=base_color,
        name="Combusting Heater",
        render_order=RenderOrder.HAZARD,
        hazard=make_heat_zone(radius=1, severity=5.0, grace_period=7, burst_chance=0.25),
    )
    engine = FakeEngine(player)
    engine.rng = _ScriptedRng([0.9, 0.9, 0.1])  # two safe rolls, then a burst

    tick_heater_burst(heater, engine)
    assert player.fighter.hp == 100  # rolled safe
    assert heater.color != base_color  # darker/pinker while live and rolling

    tick_heater_burst(heater, engine)
    assert player.fighter.hp == 100  # rolled safe again
    assert heater.color != base_color

    tick_heater_burst(heater, engine)
    assert player.fighter.hp == 95  # this roll bursts
    assert heater.color == base_color  # reverts once dormant again
    assert heater.hazard.data["grace_remaining"] == 7


def test_heater_burst_resets_clock_even_when_player_out_of_radius():
    player = _make_player(fighter=Fighter(hp=100))
    player.place(0, 0)
    heater = Entity(
        5,
        5,
        char="&",
        color=(230, 110, 40),
        name="Combusting Heater",
        render_order=RenderOrder.HAZARD,
        hazard=make_heat_zone(radius=1, severity=5.0, grace_period=7, burst_chance=1.0),
    )
    engine = FakeEngine(player)

    tick_heater_burst(heater, engine)

    assert player.fighter.hp == 100  # too far away to be hurt
    assert heater.hazard.data["grace_remaining"] == 7  # clock still resets


def test_impact_zone_stays_always_on():
    player = _make_player(fighter=Fighter(hp=100))
    player.place(5, 5)
    wall = Entity(
        5,
        6,
        char="#",
        color=(0, 0, 0),
        name="Shifting Wall",
        render_order=RenderOrder.HAZARD,
        hazard=make_impact_zone(radius=1, severity=4.0),
    )
    engine = FakeEngine(player)

    for _ in range(3):
        tick_proximity_damage(wall, engine)

    assert player.fighter.hp == 88  # every tick still deals damage, no cycling


def test_unstable_floor_only_counts_steps_while_player_present():
    player = _make_player()
    player.place(0, 0)  # not on the hazard tile
    floor_hazard = Entity(9, 9, char="=", color=(0, 0, 0), name="Unstable Floor", render_order=RenderOrder.HAZARD, hazard=make_unstable_floor(collapse_threshold=1, event_flag="floor_collapsed"))
    engine = FakeEngine(player)

    tick_unstable_floor(floor_hazard, engine)

    assert "floor_collapsed" not in engine.event_flags
