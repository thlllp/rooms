from backrooms.actions import MAX_HIT_CHANCE, MIN_HIT_CHANCE, _hit_chance
from backrooms.entity.components.attributes import (
    BASELINE_ATTRIBUTE,
    AttributesComponent,
    attribute_value,
    endurance_mitigation_from_endurance,
    max_hp_from_endurance,
    max_sanity_from_willpower,
    power_from_strength,
    willpower_mitigation_from_willpower,
)
from backrooms.entity.entity import Entity, RenderOrder


def _make_entity(**kwargs):
    return Entity(0, 0, char="@", color=(255, 255, 255), name="Entity", render_order=RenderOrder.PLAYER, **kwargs)


def test_attributes_component_defaults():
    attrs = AttributesComponent()
    assert attrs.endurance == 5
    assert attrs.willpower == 5
    assert attrs.dexterity == 5
    assert attrs.strength == 5
    assert attrs.luck == 5


def test_derivation_at_baseline_reproduces_original_constants():
    # Baseline attribute value (5) must fall out to exactly what this file's
    # constants hardcoded before AttributesComponent existed.
    assert max_hp_from_endurance(5) == 20
    assert endurance_mitigation_from_endurance(5) == 1
    assert max_sanity_from_willpower(5) == 100
    assert willpower_mitigation_from_willpower(5) == 0.3
    assert power_from_strength(5) == 1


def test_derivation_at_non_baseline_values():
    assert max_hp_from_endurance(8) == 32
    assert endurance_mitigation_from_endurance(9) == 1  # 9 // 5
    assert endurance_mitigation_from_endurance(10) == 2  # 10 // 5
    assert max_sanity_from_willpower(8) == 160
    assert willpower_mitigation_from_willpower(8) == 0.48
    assert power_from_strength(10) == 2  # 10 // 5
    assert power_from_strength(4) == 0  # below the divisor -- harmless bump territory


def test_hit_chance_equal_dexterity_is_base_rate():
    attacker = _make_entity(attributes=AttributesComponent(dexterity=5))
    defender = _make_entity(attributes=AttributesComponent(dexterity=5))
    assert _hit_chance(attacker, defender) == 0.85


def test_hit_chance_clamps_at_large_positive_delta():
    attacker = _make_entity(attributes=AttributesComponent(dexterity=50))
    defender = _make_entity(attributes=AttributesComponent(dexterity=5))
    assert _hit_chance(attacker, defender) == MAX_HIT_CHANCE


def test_hit_chance_clamps_at_large_negative_delta():
    attacker = _make_entity(attributes=AttributesComponent(dexterity=5))
    defender = _make_entity(attributes=AttributesComponent(dexterity=50))
    assert _hit_chance(attacker, defender) == MIN_HIT_CHANCE


def test_attribute_value_falls_back_to_baseline_without_attributes_component():
    entity = _make_entity()
    assert entity.attributes is None
    assert attribute_value(entity, "dexterity") == BASELINE_ATTRIBUTE
