from backrooms.actions import AttackAction
from backrooms.entity.components.fighter import Fighter
from backrooms.entity.entity import Entity, RenderOrder
from backrooms.world.game_map import GameMap


class FakeLog:
    def __init__(self):
        self.messages = []

    def add_message(self, text, color=None):
        self.messages.append(text)


class FixedRng:
    """Stubs engine.rng.random() to always return a fixed value, so a hit or
    a miss can be forced deterministically instead of depending on a seed."""

    def __init__(self, value):
        self.value = value

    def random(self):
        return self.value


class RaisingRng:
    """Fails the test if engine.rng.random() is ever called -- used to prove
    a zero-power attack short-circuits to the harmless-bump message before
    any hit-chance roll happens."""

    def random(self):
        raise AssertionError("rng.random() should not have been called")


class FakeEngine:
    def __init__(self, rng):
        self.message_log = FakeLog()
        self.rng = rng
        self.game_map = GameMap(20, 20)
        self.game_over = False
        self.player = None  # AttackAction only compares `target is engine.player` for message color

    def kill_entity(self, entity):
        self.game_over = True
        self.message_log.add_message("Everything goes quiet.")


def _make_fighter_entity(name, *, power=0, hp=10):
    return Entity(
        0, 0, char="@", color=(255, 255, 255), name=name, render_order=RenderOrder.ACTOR, fighter=Fighter(hp=hp, power=power)
    )


def test_attack_hits_and_deals_damage_when_roll_succeeds():
    attacker = _make_fighter_entity("Attacker", power=5)
    defender = _make_fighter_entity("Defender", hp=10)
    engine = FakeEngine(FixedRng(0.0))  # 0.0 is always < any hit_chance -- guaranteed hit

    AttackAction(attacker, 1, 0, target=defender).perform(engine)

    assert defender.fighter.hp == 5
    assert any("hits" in m for m in engine.message_log.messages)


def test_attack_misses_and_deals_no_damage_when_roll_fails():
    attacker = _make_fighter_entity("Attacker", power=5)
    defender = _make_fighter_entity("Defender", hp=10)
    engine = FakeEngine(FixedRng(0.99))  # 0.99 exceeds MAX_HIT_CHANCE (0.95) -- guaranteed miss

    AttackAction(attacker, 1, 0, target=defender).perform(engine)

    assert defender.fighter.hp == 10  # untouched
    assert any("misses" in m for m in engine.message_log.messages)


def test_zero_power_attack_bumps_harmlessly_without_rolling():
    attacker = _make_fighter_entity("Attacker", power=0)
    defender = _make_fighter_entity("Defender", hp=10)
    engine = FakeEngine(RaisingRng())  # would fail the test if a roll were attempted

    AttackAction(attacker, 1, 0, target=defender).perform(engine)

    assert defender.fighter.hp == 10
    assert any("harmlessly" in m for m in engine.message_log.messages)


def test_attack_kills_target_on_lethal_hit():
    attacker = _make_fighter_entity("Attacker", power=100)
    defender = _make_fighter_entity("Defender", hp=10)
    engine = FakeEngine(FixedRng(0.0))

    AttackAction(attacker, 1, 0, target=defender).perform(engine)

    assert defender.fighter.hp == 0
    assert engine.game_over
