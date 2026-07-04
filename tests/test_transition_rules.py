import random
from collections import Counter

import pytest

from backrooms.world.level_registry import (
    DestinationOption,
    TransitionContext,
    TransitionRule,
    TriggerKind,
)


def _ctx(**overrides):
    defaults = dict(
        player_sanity=100,
        turns_in_level=100,
        event_flags=set(),
        tile_under_player_id=None,
        rng=random.Random(0),
    )
    defaults.update(overrides)
    return TransitionContext(**defaults)


@pytest.mark.parametrize(
    "sanity,threshold,expected",
    [(10, 15, True), (15, 15, False), (16, 15, False)],
)
def test_sanity_below_boundary(sanity, threshold, expected):
    rule = TransitionRule(
        trigger=TriggerKind.SANITY_BELOW,
        sanity_threshold=threshold,
        destinations=(DestinationOption("dest"),),
    )
    assert rule.is_satisfied(_ctx(player_sanity=sanity)) is expected


@pytest.mark.parametrize(
    "sanity,threshold,expected",
    [(90, 70, True), (70, 70, False), (69, 70, False)],
)
def test_sanity_above_boundary(sanity, threshold, expected):
    rule = TransitionRule(
        trigger=TriggerKind.SANITY_ABOVE,
        sanity_threshold=threshold,
        destinations=(DestinationOption("dest"),),
    )
    assert rule.is_satisfied(_ctx(player_sanity=sanity)) is expected


@pytest.mark.parametrize(
    "turns,threshold,expected",
    [(299, 300, False), (300, 300, True), (301, 300, True)],
)
def test_turn_count_elapsed_boundary(turns, threshold, expected):
    rule = TransitionRule(
        trigger=TriggerKind.TURN_COUNT_ELAPSED,
        turn_threshold=threshold,
        destinations=(DestinationOption("dest"),),
    )
    assert rule.is_satisfied(_ctx(turns_in_level=turns)) is expected


def test_event_flag_set():
    rule = TransitionRule(
        trigger=TriggerKind.EVENT_FLAG_SET,
        event_flag="floor_collapsed",
        destinations=(DestinationOption("dest"),),
    )
    assert rule.is_satisfied(_ctx(event_flags=set())) is False
    assert rule.is_satisfied(_ctx(event_flags={"floor_collapsed"})) is True


def test_feature_stepped_on():
    rule = TransitionRule(
        trigger=TriggerKind.FEATURE_STEPPED_ON,
        feature_tile_id="exit_pad",
        destinations=(DestinationOption("dest"),),
    )
    assert rule.is_satisfied(_ctx(tile_under_player_id="floor")) is False
    assert rule.is_satisfied(_ctx(tile_under_player_id="exit_pad")) is True


def test_random_chance_per_turn_is_deterministic_under_seeded_rng():
    rule = TransitionRule(
        trigger=TriggerKind.RANDOM_CHANCE_PER_TURN,
        chance_per_turn=0.5,
        destinations=(DestinationOption("dest"),),
    )
    # random.Random(0).random() first call is a known constant (~0.844) -> above 0.5, should fail
    assert rule.is_satisfied(_ctx(rng=random.Random(0))) is False
    # random.Random(1).random() first call is ~0.134 -> below 0.5, should pass
    assert rule.is_satisfied(_ctx(rng=random.Random(1))) is True


def test_min_turns_in_level_gate():
    rule = TransitionRule(
        trigger=TriggerKind.SANITY_BELOW,
        sanity_threshold=100,  # always numerically satisfied
        min_turns_in_level=50,
        destinations=(DestinationOption("dest"),),
    )
    assert rule.is_satisfied(_ctx(player_sanity=0, turns_in_level=10)) is False
    assert rule.is_satisfied(_ctx(player_sanity=0, turns_in_level=50)) is True


def test_pick_destination_single_option_is_deterministic():
    rule = TransitionRule(
        trigger=TriggerKind.SANITY_BELOW,
        sanity_threshold=0,
        destinations=(DestinationOption("only_option"),),
    )
    assert rule.pick_destination(random.Random(123)) == "only_option"


def test_pick_destination_weighted_proportionality():
    rule = TransitionRule(
        trigger=TriggerKind.SANITY_BELOW,
        sanity_threshold=0,
        destinations=(
            DestinationOption("common", weight=9.0),
            DestinationOption("rare", weight=1.0),
        ),
    )
    rng = random.Random(42)
    counts = Counter(rule.pick_destination(rng) for _ in range(5000))
    ratio = counts["common"] / (counts["common"] + counts["rare"])
    assert 0.8 <= ratio <= 1.0  # expected ~0.9, generous tolerance to avoid flakiness
