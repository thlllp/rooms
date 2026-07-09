from backrooms.actions import PickupAction, UseItemAction
from backrooms.entity.components.consumable import make_sanity_restore_item
from backrooms.entity.components.equippable import EquippableComponent
from backrooms.entity.components.inventory import Inventory
from backrooms.entity.components.sanity import SanityComponent
from backrooms.entity.components.tool import make_fabric_cutter, make_sewing_kit
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


def _make_scissors():
    return Entity(
        0, 0, char="x", color=(180, 180, 190), name="Scissors",
        render_order=RenderOrder.ITEM, tool=make_fabric_cutter(_make_rag),
    )


def _make_rag():
    return Entity(0, 0, char="~", color=(200, 195, 180), name="Rag", render_order=RenderOrder.ITEM)


def _make_fabric_item(name="Flannel Shirt"):
    return Entity(0, 0, char="s", color=(150, 70, 60), name=name, render_order=RenderOrder.ITEM, contains_fabric=True)


def test_using_scissors_cuts_first_fabric_item_into_a_rag_and_stays_held():
    player = _make_player(inventory=Inventory(capacity=10))
    game_map = _make_map_with_player_on_floor(player)
    scissors = _make_scissors()
    shirt = _make_fabric_item()
    player.inventory.items.extend([scissors, shirt])
    engine = FakeEngine(player, game_map)
    engine.show_inventory = True

    UseItemAction(player, 0).perform(engine)  # slot 0 == scissors

    assert scissors in player.inventory.items  # tool isn't consumed
    assert shirt not in player.inventory.items  # cut up
    assert any(item.name == "Rag" for item in player.inventory.items)
    assert any("cut the Flannel Shirt" in m for m in engine.message_log.messages)


def test_using_scissors_with_nothing_fabric_held_is_a_no_op_message():
    player = _make_player(inventory=Inventory(capacity=10))
    game_map = _make_map_with_player_on_floor(player)
    scissors = _make_scissors()
    player.inventory.items.append(scissors)
    engine = FakeEngine(player, game_map)
    engine.show_inventory = True

    UseItemAction(player, 0).perform(engine)

    assert scissors in player.inventory.items
    assert len(player.inventory.items) == 1  # nothing added
    assert any("fabric" in m for m in engine.message_log.messages)


def test_using_scissors_with_nothing_to_cut_does_not_cost_a_turn():
    player = _make_player(inventory=Inventory(capacity=10))
    game_map = _make_map_with_player_on_floor(player)
    scissors = _make_scissors()
    player.inventory.items.append(scissors)
    engine = FakeEngine(player, game_map)
    engine.show_inventory = True

    action = UseItemAction(player, 0)
    action.perform(engine)

    assert action.costs_turn is False  # a no-op cut is free, like an empty slot


def test_using_sewing_kit_directly_is_a_free_no_op():
    player = _make_player(inventory=Inventory(capacity=10))
    game_map = _make_map_with_player_on_floor(player)
    kit = Entity(
        0, 0, char="k", color=(200, 190, 170), name="Sewing Kit",
        render_order=RenderOrder.ITEM, tool=make_sewing_kit(max_uses=5),
    )
    player.inventory.items.append(kit)
    engine = FakeEngine(player, game_map)
    engine.show_inventory = True

    action = UseItemAction(player, 0)
    action.perform(engine)

    assert action.costs_turn is False  # never does anything on direct use
    assert kit.tool.charges.remaining == 5  # direct use spends no charge


def test_successful_scissors_cut_still_costs_a_turn():
    player = _make_player(inventory=Inventory(capacity=10))
    game_map = _make_map_with_player_on_floor(player)
    scissors = _make_scissors()
    player.inventory.items.extend([scissors, _make_fabric_item()])
    engine = FakeEngine(player, game_map)
    engine.show_inventory = True

    action = UseItemAction(player, 0)
    action.perform(engine)

    assert action.costs_turn is True  # a real cut is an action, unlike a no-op


def test_scissors_cut_plain_clothing_before_functional_fabric_gear():
    # A player carrying both a plain shirt and an unequipped Hiking Bag (which
    # grants +10 capacity and is contains_fabric) must never lose the bag to a
    # mis-aimed cut just because it sits earlier in inventory order.
    player = _make_player(inventory=Inventory(capacity=10))
    game_map = _make_map_with_player_on_floor(player)
    scissors = _make_scissors()
    hiking_bag = Entity(
        0, 0, char="H", color=(70, 110, 80), name="Hiking Bag", render_order=RenderOrder.ITEM,
        contains_fabric=True, equippable=EquippableComponent(slot="back", capacity_bonus=10),
    )
    shirt = _make_fabric_item()
    player.inventory.items.extend([scissors, hiking_bag, shirt])  # bag ahead of shirt
    engine = FakeEngine(player, game_map)
    engine.show_inventory = True

    UseItemAction(player, 0).perform(engine)

    assert hiking_bag in player.inventory.items  # spared -- it grants a benefit
    assert shirt not in player.inventory.items  # the plain scrap took the blade


def test_scissors_still_cut_functional_gear_when_no_plain_scrap_is_left():
    player = _make_player(inventory=Inventory(capacity=10))
    game_map = _make_map_with_player_on_floor(player)
    scissors = _make_scissors()
    mask = Entity(
        0, 0, char="[", color=(90, 90, 100), name="Mask", render_order=RenderOrder.ITEM,
        contains_fabric=True, equippable=EquippableComponent(slot="face", spore_resistance=1.0),
    )
    player.inventory.items.extend([scissors, mask])  # only functional fabric on hand
    engine = FakeEngine(player, game_map)
    engine.show_inventory = True

    UseItemAction(player, 0).perform(engine)

    assert mask not in player.inventory.items  # still cuttable as a last resort
    assert any(item.name == "Rag" for item in player.inventory.items)
