import backrooms.data.registrations  # noqa: F401 -- populates LEVEL_REGISTRY
from backrooms.engine import Engine
from backrooms.entity.components.fighter import Fighter
from backrooms.entity.components.hunger import HungerComponent
from backrooms.entity.entity import Entity, RenderOrder
from backrooms.systems.rest_system import INN_HP_RESTORE, INN_HUNGER_RESTORE, process_rest
from backrooms.world.game_map import GameMap
from backrooms.world.tile_types import FLOOR, INN_FLOOR, ZoneEffect


def _make_player(*, max_hp: int = 20, hp: int = 20, hunger: float = 100.0) -> Entity:
    player = Entity(0, 0, char="@", color=(255, 255, 255), name="Player", blocks_movement=True, render_order=RenderOrder.PLAYER)
    player.fighter = Fighter(hp=max_hp)
    player.fighter.hp = hp
    player.hunger = HungerComponent(max_hunger=100.0)
    player.hunger.current = hunger
    return player


def test_hunger_restore_clamps_at_max():
    hunger = HungerComponent(max_hunger=100.0)
    hunger.current = 90.0
    hunger.restore(50.0)
    assert hunger.current == 100.0


class _StubMap:
    """Minimal stand-in for GameMap.has_zone_effect, so process_rest can be
    tested without generating a real map."""

    def __init__(self, inn: bool) -> None:
        self._inn = inn

    def has_zone_effect(self, x: int, y: int, effect: ZoneEffect) -> bool:
        return self._inn and effect is ZoneEffect.INN


class _StubEngine:
    def __init__(self, player: Entity, *, inn: bool) -> None:
        self.player = player
        self.game_map = _StubMap(inn)


def test_process_rest_heals_hp_and_hunger_on_inn_tile():
    player = _make_player(max_hp=20, hp=5, hunger=50.0)
    engine = _StubEngine(player, inn=True)

    process_rest(engine)

    assert player.fighter.hp == 5 + INN_HP_RESTORE
    assert player.hunger.current == 50.0 + INN_HUNGER_RESTORE


def test_process_rest_does_nothing_off_the_inn_tile():
    player = _make_player(max_hp=20, hp=5, hunger=50.0)
    engine = _StubEngine(player, inn=False)

    process_rest(engine)

    assert player.fighter.hp == 5
    assert player.hunger.current == 50.0


def test_settlement_generation_carves_out_an_inn_room():
    engine = Engine(player=_make_player(), seed=3, start_level_id="level_2_settlement")
    game_map = engine.game_map

    assert ((game_map.tiles["zone_effects"] & ZoneEffect.INN) != 0).any()


def test_inn_floor_is_also_a_safe_zone_for_sanity():
    # The inn is a small area within the settlement, not a wholesale
    # replacement of its floor -- sanity should keep recovering there too.
    assert bool(INN_FLOOR["zone_effects"] & ZoneEffect.SAFE)
    assert not bool(FLOOR["zone_effects"] & ZoneEffect.INN)
