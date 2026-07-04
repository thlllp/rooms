import pytest

from backrooms.entity.components.sanity import SanityComponent


def test_drain_clamps_at_zero():
    sanity = SanityComponent(max_sanity=100)
    sanity.drain(150)
    assert sanity.current == 0.0


def test_restore_clamps_at_max():
    sanity = SanityComponent(max_sanity=100)
    sanity.drain(10)
    sanity.restore(50)
    assert sanity.current == 100.0


@pytest.mark.parametrize(
    "value,expected_band",
    [
        (100, "normal"),
        (70, "normal"),
        (69.999, "mild"),
        (40, "mild"),
        (39.999, "severe"),
        (15, "severe"),
        (14.999, "critical"),
        (0, "critical"),
    ],
)
def test_band_boundaries_are_exact(value, expected_band):
    sanity = SanityComponent(max_sanity=100)
    sanity.current = value
    assert sanity.band.name == expected_band


def test_band_flags_escalate_with_severity():
    sanity = SanityComponent(max_sanity=100)

    sanity.current = 100
    assert not sanity.band.perception_distortion
    assert not sanity.band.hallucinations
    assert not sanity.band.forced_event_eligible

    sanity.current = 50
    assert sanity.band.perception_distortion
    assert not sanity.band.hallucinations

    sanity.current = 20
    assert sanity.band.hallucinations
    assert not sanity.band.forced_event_eligible

    sanity.current = 5
    assert sanity.band.forced_event_eligible


def test_is_pacing_in_loop_requires_full_history_window():
    sanity = SanityComponent(max_sanity=100, history_window=4, repeat_ratio_threshold=0.5)
    sanity.record_position(0, 0)
    sanity.record_position(1, 0)
    assert not sanity.is_pacing_in_loop()  # history not yet full


def test_is_pacing_in_loop_detects_low_unique_ratio():
    sanity = SanityComponent(max_sanity=100, history_window=4, repeat_ratio_threshold=0.5)
    for pos in [(0, 0), (1, 0), (0, 0), (1, 0)]:  # 2 unique / 4 = 0.5, not < 0.5
        sanity.record_position(*pos)
    assert not sanity.is_pacing_in_loop()

    sanity.record_position(0, 0)  # window becomes [(1,0),(0,0),(1,0),(0,0)] -> still 0.5
    assert not sanity.is_pacing_in_loop()

    sanity2 = SanityComponent(max_sanity=100, history_window=5, repeat_ratio_threshold=0.5)
    for pos in [(0, 0), (1, 0), (0, 0), (1, 0), (0, 0)]:  # 2 unique / 5 = 0.4 < 0.5
        sanity2.record_position(*pos)
    assert sanity2.is_pacing_in_loop()


def test_combined_drain_sources_sum(monkeypatch):
    """Exercise process_sanity's summation with fixed mock inputs rather than
    real procgen/entities -- isolates the arithmetic from world state."""
    from backrooms.entity.entity import Entity, RenderOrder
    from backrooms.systems import sanity_system
    from backrooms.world.game_map import GameMap
    from backrooms.world.level_registry import LevelDefinition

    player = Entity(5, 5, char="@", color=(255, 255, 255), name="Player", render_order=RenderOrder.PLAYER, sanity=SanityComponent())
    game_map = GameMap(10, 10)

    class FakeEngine:
        def __init__(self):
            self.player = player
            self.game_map = game_map
            self.current_level_id = "test_level"
            self.message_log = _FakeLog()

    class _FakeLog:
        def __init__(self):
            self.messages = []

        def add_message(self, text, color=None):
            self.messages.append(text)

    level_def = LevelDefinition(id="test_level", display_name="Test", generator=lambda ctx: game_map, ambient_sanity_drain=1.0, darkness_factor=2.0)
    monkeypatch.setitem(sanity_system.LEVEL_REGISTRY, "test_level", level_def)

    engine = FakeEngine()
    starting = player.sanity.current
    sanity_system.process_sanity(engine)

    # No light source (always unlit this milestone) -> UNLIT_DARKNESS_DRAIN * darkness_factor(2.0)
    expected_drain = level_def.ambient_sanity_drain + sanity_system.UNLIT_DARKNESS_DRAIN * level_def.darkness_factor
    assert player.sanity.current == pytest.approx(starting - expected_drain)
