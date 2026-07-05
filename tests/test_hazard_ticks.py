import random

from backrooms.entity.components.fighter import Fighter
from backrooms.entity.components.hazard import (
    make_debris_pile,
    make_spore_zone,
    make_unstable_floor,
    tick_debris_pile,
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


def _spawn_loot():
    return Entity(0, 0, char="!", color=(0, 0, 0), name="Loot", render_order=RenderOrder.ITEM)


def test_debris_pile_grants_item_on_good_outcome():
    player = _make_player(sanity=SanityComponent(max_sanity=100))
    player.place(5, 5)
    pile = Entity(
        5,
        5,
        char="%",
        color=(0, 0, 0),
        name="Debris Pile",
        render_order=RenderOrder.HAZARD,
        hazard=make_debris_pile(item_factories=(_spawn_loot,), good_chance=1.0, sanity_penalty=10.0),
    )
    engine = FakeEngine(player)
    engine.game_map.entities.add(pile)

    tick_debris_pile(pile, engine)

    assert pile not in engine.game_map.entities
    assert any(e.name == "Loot" for e in engine.game_map.entities)
    assert player.sanity.current == 100  # untouched


def test_debris_pile_drains_sanity_on_bad_outcome():
    player = _make_player(sanity=SanityComponent(max_sanity=100))
    player.place(5, 5)
    pile = Entity(
        5,
        5,
        char="%",
        color=(0, 0, 0),
        name="Debris Pile",
        render_order=RenderOrder.HAZARD,
        hazard=make_debris_pile(item_factories=(_spawn_loot,), good_chance=0.0, sanity_penalty=15.0),
    )
    engine = FakeEngine(player)
    engine.game_map.entities.add(pile)

    tick_debris_pile(pile, engine)

    assert pile not in engine.game_map.entities
    assert player.sanity.current == 85.0


def test_debris_pile_does_nothing_until_player_steps_on_it():
    player = _make_player(sanity=SanityComponent(max_sanity=100))
    player.place(0, 0)
    pile = Entity(
        5,
        5,
        char="%",
        color=(0, 0, 0),
        name="Debris Pile",
        render_order=RenderOrder.HAZARD,
        hazard=make_debris_pile(item_factories=(_spawn_loot,), good_chance=1.0),
    )
    engine = FakeEngine(player)
    engine.game_map.entities.add(pile)

    tick_debris_pile(pile, engine)

    assert pile in engine.game_map.entities
    assert player.sanity.current == 100


def test_unstable_floor_only_counts_steps_while_player_present():
    player = _make_player()
    player.place(0, 0)  # not on the hazard tile
    floor_hazard = Entity(9, 9, char="=", color=(0, 0, 0), name="Unstable Floor", render_order=RenderOrder.HAZARD, hazard=make_unstable_floor(collapse_threshold=1, event_flag="floor_collapsed"))
    engine = FakeEngine(player)

    tick_unstable_floor(floor_hazard, engine)

    assert "floor_collapsed" not in engine.event_flags
