import pytest

from backrooms.actions import AttackAction
from backrooms.entity.components.charges import Charges
from backrooms.entity.components.equipment import EquipmentComponent
from backrooms.entity.components.equippable import EquippableComponent
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


def _make_fighter_entity(name, *, power=0, hp=10, equipment=None):
    return Entity(
        0, 0, char="@", color=(255, 255, 255), name=name, render_order=RenderOrder.ACTOR,
        fighter=Fighter(hp=hp, power=power), equipment=equipment,
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


def _wielding(weapon):
    equipment = EquipmentComponent()
    equipment.slots["right_hand"] = weapon
    return equipment


def _chair_leg(*, max_uses=6):
    return Entity(
        0, 0, char="/", color=(150, 110, 70), name="Chair Leg", render_order=RenderOrder.ITEM,
        equippable=EquippableComponent(slot="right_hand", power_bonus=2, max_uses=max_uses),
    )


def test_wielded_weapon_adds_its_power_bonus_to_the_attack():
    weapon = _chair_leg()
    attacker = _make_fighter_entity("Attacker", power=1)
    attacker.equipment = _wielding(weapon)
    defender = _make_fighter_entity("Defender", hp=10)
    engine = FakeEngine(FixedRng(0.0))

    AttackAction(attacker, 1, 0, target=defender).perform(engine)

    assert defender.fighter.hp == 7  # 10 - (1 power + 2 weapon bonus)


def test_connecting_hit_ticks_down_only_the_wielded_weapon_not_other_equipped_items():
    weapon = _chair_leg(max_uses=6)
    # A worn item with no power_bonus at all (e.g. a Mask) never contributed
    # to this swing, so it must not lose a charge just because the attacker
    # also happens to be wearing something.
    mask = Entity(
        0, 0, char="[", color=(90, 90, 100), name="Mask", render_order=RenderOrder.ITEM,
        equippable=EquippableComponent(slot="face", spore_resistance=1.0, max_uses=6),
    )
    attacker = _make_fighter_entity("Attacker", power=1)
    attacker.equipment = _wielding(weapon)
    attacker.equipment.slots["face"] = mask
    defender = _make_fighter_entity("Defender", hp=10)
    engine = FakeEngine(FixedRng(0.0))

    AttackAction(attacker, 1, 0, target=defender).perform(engine)

    assert weapon.equippable.charges.remaining == 5
    assert mask.equippable.charges.remaining == 6  # untouched -- it wasn't the weapon


def test_weapon_breaks_and_unequips_after_its_last_connecting_hit():
    weapon = _chair_leg(max_uses=1)
    attacker = _make_fighter_entity("Attacker", power=1)
    attacker.equipment = _wielding(weapon)
    defender = _make_fighter_entity("Defender", hp=10)
    engine = FakeEngine(FixedRng(0.0))

    AttackAction(attacker, 1, 0, target=defender).perform(engine)

    assert attacker.equipment.slots["right_hand"] is None
    assert any("breaks apart" in m for m in engine.message_log.messages)


def test_a_miss_does_not_consume_a_weapon_charge():
    weapon = _chair_leg(max_uses=1)
    attacker = _make_fighter_entity("Attacker", power=1)
    attacker.equipment = _wielding(weapon)
    defender = _make_fighter_entity("Defender", hp=10)
    engine = FakeEngine(FixedRng(0.99))  # guaranteed miss

    AttackAction(attacker, 1, 0, target=defender).perform(engine)

    assert weapon.equippable.charges.remaining == 1  # untouched
    assert attacker.equipment.slots["right_hand"] is weapon  # still equipped


def test_zero_charge_weapon_is_rejected_at_construction():
    # A max_uses<=0 pool would deliver its effect once (0 -> -1 still trips the
    # depleted check) and then vanish -- reject it rather than ship that trap.
    with pytest.raises(ValueError):
        Charges(0)
    with pytest.raises(ValueError):
        EquippableComponent(slot="right_hand", power_bonus=2, max_uses=0)
