from backrooms.actions import PickupAction, UseItemAction
from backrooms.entity.components.consumable import make_sanity_restore_item
from backrooms.entity.components.inventory import Inventory
from backrooms.entity.components.sanity import SanityComponent
from backrooms.entity.entity import Entity, RenderOrder
from backrooms.world.game_map import GameMap
from backrooms.world import tile_types


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


def _make_player(**kwargs):
    return Entity(0, 0, char="@", color=(255, 255, 255), name="Player", render_order=RenderOrder.PLAYER, **kwargs)


def _make_map_with_player_on_floor(player):
    game_map = GameMap(5, 5)
    game_map.tiles[:, :] = tile_types.FLOOR
    game_map.entities.add(player)
    return game_map


def _make_item():
    return Entity(
        0, 0, char="!", color=(255, 255, 255), name="Almond Water Bottle",
        render_order=RenderOrder.ITEM, consumable=make_sanity_restore_item(30.0),
    )


def test_pickup_moves_item_from_map_into_inventory():
    player = _make_player(inventory=Inventory(capacity=10))
    game_map = _make_map_with_player_on_floor(player)
    item = _make_item()
    item.place(player.x, player.y)
    game_map.entities.add(item)
    engine = FakeEngine(player, game_map)

    PickupAction(player).perform(engine)

    assert item not in game_map.entities
    assert item in player.inventory.items
    assert any("pick up" in m for m in engine.message_log.messages)


def test_pickup_with_nothing_here_is_a_free_no_op():
    player = _make_player(inventory=Inventory(capacity=10))
    game_map = _make_map_with_player_on_floor(player)
    engine = FakeEngine(player, game_map)

    action = PickupAction(player)
    action.perform(engine)

    assert action.costs_turn is False
    assert any("nothing here" in m for m in engine.message_log.messages)


def test_pickup_respects_capacity():
    player = _make_player(inventory=Inventory(capacity=1))
    game_map = _make_map_with_player_on_floor(player)
    already_held = _make_item()
    player.inventory.items.append(already_held)
    item = _make_item()
    item.place(player.x, player.y)
    game_map.entities.add(item)
    engine = FakeEngine(player, game_map)

    action = PickupAction(player)
    action.perform(engine)

    assert action.costs_turn is False
    assert item in game_map.entities  # left on the ground
    assert len(player.inventory.items) == 1


def test_use_item_restores_sanity_and_removes_from_inventory():
    player = _make_player(inventory=Inventory(capacity=10), sanity=SanityComponent(max_sanity=100))
    player.sanity.current = 50
    game_map = _make_map_with_player_on_floor(player)
    item = _make_item()
    player.inventory.items.append(item)
    engine = FakeEngine(player, game_map)
    engine.show_inventory = True

    UseItemAction(player, 0).perform(engine)

    assert player.sanity.current == 80
    assert item not in player.inventory.items
    assert engine.show_inventory is False
    assert any("calm" in m for m in engine.message_log.messages)


def test_use_item_invalid_slot_is_a_free_no_op():
    player = _make_player(inventory=Inventory(capacity=10))
    game_map = _make_map_with_player_on_floor(player)
    engine = FakeEngine(player, game_map)
    engine.show_inventory = True

    action = UseItemAction(player, 5)
    action.perform(engine)

    assert action.costs_turn is False
    assert engine.show_inventory is True  # untouched, nothing was used
