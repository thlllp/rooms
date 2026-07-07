import backrooms.data.registrations  # noqa: F401 -- populates LEVEL_REGISTRY
from backrooms.engine import Engine
from backrooms.entity.entity import Entity, RenderOrder


def _make_player():
    return Entity(0, 0, char="@", color=(255, 255, 255), name="Player", blocks_movement=True, render_order=RenderOrder.PLAYER)


def test_dev_mode_off_prints_nothing(capsys):
    Engine(player=_make_player(), seed=1, dev_mode=False)
    captured = capsys.readouterr()
    assert captured.out == ""


def test_dev_mode_on_prints_overview_on_load(capsys):
    Engine(player=_make_player(), seed=1, dev_mode=True)
    captured = capsys.readouterr()
    assert "DEV MODE" in captured.out
    assert "Entrance (spawn point):" in captured.out
    assert "Exits:" in captured.out
    assert "Points of interest / NPCs" in captured.out


def test_dev_mode_reprints_on_level_transition(capsys):
    engine = Engine(player=_make_player(), seed=1, dev_mode=True)
    capsys.readouterr()  # discard the initial-boot print
    engine.load_level("level_1_office")
    captured = capsys.readouterr()
    assert "level_1_office" in captured.out


def test_exit_rule_cross_references_hazard_source(capsys):
    # An EVENT_FLAG_SET exit rule is annotated with the hazard(s) that set its
    # flag. Several hazards can now share one flag (Unstable Floor and Weak
    # Floorboards both set "floor_collapsed"), and game_map.entities is an
    # unordered set, so assert the source appears somewhere in the annotation
    # rather than as the first one after "source: ".
    Engine(player=_make_player(), seed=1, dev_mode=True)
    captured = capsys.readouterr()
    assert "Unstable Floor@" in captured.out


def test_entrances_reachable_from_is_empty_for_entry_level(capsys):
    """Nothing transitions back into level_0_office -- level_1_office's only
    rule loops into a fresh instance of itself, and _incoming_levels()
    deliberately excludes a level's own self-loop."""
    Engine(player=_make_player(), seed=1, dev_mode=True)
    captured = capsys.readouterr()
    assert "Entrances (reachable from): (none -- only reached as the initial level)" in captured.out
