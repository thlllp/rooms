from backrooms.actions import BumpAction, SalvageAction
from backrooms.entity.components.attributes import AttributesComponent
from backrooms.entity.components.inventory import Inventory
from backrooms.entity.components.salvageable import SalvageableComponent
from backrooms.entity.entity import Entity, RenderOrder
from backrooms.world import tile_types
from backrooms.world.game_map import GameMap


class FakeLog:
    def __init__(self):
        self.messages = []

    def add_message(self, text, color=None):
        self.messages.append(text)


class FakeEngine:
    def __init__(self, player, game_map):
        self.player = player
        self.game_map = game_map
        self.message_log = FakeLog()
        self.look_mode = False


def _make_player(*, strength=5, inventory_capacity=10):
    return Entity(
        5, 5, char="@", color=(255, 255, 255), name="Player", blocks_movement=True, render_order=RenderOrder.PLAYER,
        attributes=AttributesComponent(strength=strength), inventory=Inventory(capacity=inventory_capacity),
    )


def _make_chair_leg():
    return Entity(0, 0, char="/", color=(150, 110, 70), name="Chair Leg", render_order=RenderOrder.ITEM)


def _make_wooden_chair(*, strength_required=5):
    return Entity(
        6, 5, char="C", color=(150, 110, 70), name="Wooden Chair", blocks_movement=True,
        render_order=RenderOrder.HAZARD,
        salvageable=SalvageableComponent(result_factory=_make_chair_leg, strength_required=strength_required),
    )


def _make_map_with(*entities):
    game_map = GameMap(10, 10, wall_tile=tile_types.WALL)
    game_map.tiles[:, :] = tile_types.FLOOR
    for entity in entities:
        game_map.entities.add(entity)
    return game_map


def test_salvage_succeeds_and_adds_item_to_inventory_when_strong_enough():
    player = _make_player(strength=5)
    chair = _make_wooden_chair(strength_required=5)
    game_map = _make_map_with(player, chair)
    engine = FakeEngine(player, game_map)

    SalvageAction(player, target=chair).perform(engine)

    assert chair not in game_map.entities
    assert any(item.name == "Chair Leg" for item in player.inventory.items)
    assert any("wrench" in m for m in engine.message_log.messages)


def test_salvage_fails_and_leaves_furniture_standing_when_too_weak():
    player = _make_player(strength=4)
    chair = _make_wooden_chair(strength_required=5)
    game_map = _make_map_with(player, chair)
    engine = FakeEngine(player, game_map)

    SalvageAction(player, target=chair).perform(engine)

    assert chair in game_map.entities  # still there to try again later
    assert not player.inventory.items
    assert any("can't wrench" in m for m in engine.message_log.messages)


def test_salvage_drops_on_ground_when_pack_is_full():
    player = _make_player(strength=5, inventory_capacity=0)
    chair = _make_wooden_chair(strength_required=5)
    game_map = _make_map_with(player, chair)
    engine = FakeEngine(player, game_map)

    SalvageAction(player, target=chair).perform(engine)

    assert not player.inventory.items
    assert any(e.name == "Chair Leg" for e in game_map.entities)
    assert any("pack is full" in m for m in engine.message_log.messages)


def test_bump_into_salvageable_furniture_routes_to_salvage_instead_of_moving():
    player = _make_player(strength=5)
    chair = _make_wooden_chair(strength_required=5)
    game_map = _make_map_with(player, chair)
    engine = FakeEngine(player, game_map)

    BumpAction(player, 1, 0).perform(engine)

    assert (player.x, player.y) == (5, 5)  # never moved into the furniture's tile
    assert any(item.name == "Chair Leg" for item in player.inventory.items)
