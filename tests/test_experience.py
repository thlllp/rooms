import pytest

from backrooms.entity.components.experience import ExperienceComponent


def test_xp_to_next_level_scales_with_level():
    xp = ExperienceComponent(level=1, base_xp_to_level=20, level_up_factor=1.5)
    assert xp.xp_to_next_level == 20
    xp.level = 2
    assert xp.xp_to_next_level == round(20 * 1.5)
    xp.level = 3
    assert xp.xp_to_next_level == round(20 * 1.5**2)


def test_gain_xp_below_threshold_does_not_level():
    xp = ExperienceComponent(base_xp_to_level=20)
    levels_gained = xp.gain_xp(19)
    assert levels_gained == 0
    assert xp.level == 1
    assert xp.current_xp == 19


def test_gain_xp_at_exact_threshold_levels_up():
    xp = ExperienceComponent(base_xp_to_level=20)
    levels_gained = xp.gain_xp(20)
    assert levels_gained == 1
    assert xp.level == 2
    assert xp.current_xp == 0


def test_gain_xp_carries_remainder_into_next_level():
    xp = ExperienceComponent(base_xp_to_level=20, level_up_factor=1.5)
    levels_gained = xp.gain_xp(25)
    assert levels_gained == 1
    assert xp.level == 2
    assert xp.current_xp == 5  # 25 - 20
    assert xp.xp_to_next_level == round(20 * 1.5)


def test_gain_xp_can_award_multiple_levels_at_once():
    xp = ExperienceComponent(base_xp_to_level=20, level_up_factor=1.0)  # flat 20/level for simple math
    levels_gained = xp.gain_xp(65)
    assert levels_gained == 3
    assert xp.level == 4
    assert xp.current_xp == 5


def test_award_xp_applies_stat_bonuses_and_full_heals(monkeypatch):
    from backrooms.entity.components.fighter import Fighter
    from backrooms.entity.components.perception import PerceptionComponent
    from backrooms.entity.entity import Entity, RenderOrder
    from backrooms.systems import experience_system

    player = Entity(
        0,
        0,
        char="@",
        color=(255, 255, 255),
        name="Player",
        render_order=RenderOrder.PLAYER,
        fighter=Fighter(hp=5, endurance=1, power=1),
        perception=PerceptionComponent(acuity=1),
        experience=ExperienceComponent(base_xp_to_level=20),
    )
    player.fighter.hp = 2  # simulate prior damage

    class FakeLog:
        def __init__(self):
            self.messages = []

        def add_message(self, text, color=None):
            self.messages.append(text)

    class FakeEngine:
        def __init__(self):
            self.player = player
            self.message_log = FakeLog()

    engine = FakeEngine()
    experience_system.award_xp(engine, 20)

    assert player.experience.level == 2
    assert player.fighter.max_hp == 5 + experience_system.LEVEL_UP_HP_BONUS
    assert player.fighter.hp == player.fighter.max_hp  # full heal on level up
    assert player.fighter.power == 1 + experience_system.LEVEL_UP_POWER_BONUS
    assert player.perception.acuity == 1 + experience_system.LEVEL_UP_PERCEPTION_BONUS
    assert any("Level 2" in m for m in engine.message_log.messages)


def test_award_xp_does_nothing_when_player_has_no_experience_component():
    from backrooms.entity.entity import Entity, RenderOrder
    from backrooms.systems import experience_system

    player = Entity(0, 0, char="@", color=(255, 255, 255), name="Player", render_order=RenderOrder.PLAYER)

    class FakeEngine:
        def __init__(self):
            self.player = player
            self.message_log = None  # would raise if touched

    experience_system.award_xp(FakeEngine(), 999)  # should not raise
