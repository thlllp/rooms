from backrooms.actions import BumpAction, SearchDebrisAction, available_interactions
from backrooms.entity.components.debris import DebrisComponent
from backrooms.entity.components.hazard import LootEntry
from backrooms.entity.components.inventory import Inventory
from backrooms.entity.components.sanity import SanityComponent
from backrooms.entity.entity import Entity, RenderOrder
from backrooms.world import tile_types
from backrooms.world.game_map import GameMap


class FakeLog:
    def __init__(self):
        self.messages = []

    def add_message(self, text, color=None):
        self.messages.append(text)


class StubRng:
    """Pins both rolls a debris search makes: `roll` is what
    engine.rng.random() returns (compared against DebrisComponent.good_chance
    to pick the outcome branch), `index` is which pool entry pick_loot's
    choices() call always returns."""

    def __init__(self, *, roll=0.0, index=0):
        self.roll = roll
        self.index = index

    def random(self):
        return self.roll

    def choices(self, population, weights=None, k=1):
        return [population[self.index]]


class FakeEngine:
    def __init__(self, player, game_map, *, roll=0.0, pick_index=0):
        self.player = player
        self.game_map = game_map
        self.message_log = FakeLog()
        self.rng = StubRng(roll=roll, index=pick_index)
        self.look_mode = False


def _make_player(*, inventory_capacity=10, sanity_max=100.0):
    return Entity(
        5, 5, char="@", color=(255, 255, 255), name="Player", blocks_movement=True, render_order=RenderOrder.PLAYER,
        inventory=Inventory(capacity=inventory_capacity), sanity=SanityComponent(max_sanity=sanity_max),
    )


def _make_rag():
    return Entity(0, 0, char="r", color=(200, 200, 200), name="Rag", render_order=RenderOrder.ITEM)


def _make_duct_tape():
    return Entity(0, 0, char="=", color=(210, 200, 60), name="Duct Tape", render_order=RenderOrder.ITEM)


def _make_debris_pile():
    return Entity(
        6, 5, char="%", color=(120, 100, 80), name="Debris Pile", blocks_movement=True, render_order=RenderOrder.HAZARD,
        debris=DebrisComponent(item_factories=(LootEntry(_make_rag), LootEntry(_make_duct_tape, weight=0.1)), good_chance=0.6, sanity_penalty=10.0),
    )


def _make_map_with(*entities):
    game_map = GameMap(10, 10, wall_tile=tile_types.WALL)
    game_map.tiles[:, :] = tile_types.FLOOR
    for entity in entities:
        game_map.entities.add(entity)
    return game_map


def test_searching_debris_on_good_roll_yields_a_pooled_item_and_removes_the_pile():
    player = _make_player()
    pile = _make_debris_pile()
    game_map = _make_map_with(player, pile)
    engine = FakeEngine(player, game_map, roll=0.0, pick_index=1)  # roll < good_chance -> success; -> Duct Tape

    SearchDebrisAction(player, target=pile).perform(engine)

    assert pile not in game_map.entities  # one-shot, consumed either way
    assert any(item.name == "Duct Tape" for item in player.inventory.items)
    assert player.sanity.current == 100.0  # untouched on a good outcome
    assert any("dig through the Debris Pile and find a Duct Tape" in m for m in engine.message_log.messages)


def test_searching_debris_on_bad_roll_drains_sanity_instead():
    player = _make_player()
    pile = _make_debris_pile()
    game_map = _make_map_with(player, pile)
    engine = FakeEngine(player, game_map, roll=0.99)  # roll >= good_chance -> bad outcome

    SearchDebrisAction(player, target=pile).perform(engine)

    assert pile not in game_map.entities
    assert not player.inventory.items
    assert player.sanity.current == 90.0
    assert any("unsettles you" in m for m in engine.message_log.messages)


def test_searching_a_full_pack_drops_the_find_on_the_ground():
    player = _make_player(inventory_capacity=0)
    pile = _make_debris_pile()
    game_map = _make_map_with(player, pile)
    engine = FakeEngine(player, game_map, roll=0.0, pick_index=0)  # -> Rag

    SearchDebrisAction(player, target=pile).perform(engine)

    assert pile not in game_map.entities
    assert not player.inventory.items
    assert any(e.name == "Rag" for e in game_map.entities)  # left on the floor
    assert any("pack is full" in m for m in engine.message_log.messages)


def test_debris_pile_blocks_movement_and_bumping_it_searches_instead_of_moving():
    player = _make_player()
    pile = _make_debris_pile()
    game_map = _make_map_with(player, pile)
    engine = FakeEngine(player, game_map, roll=0.0, pick_index=0)

    BumpAction(player, 1, 0).perform(engine)  # pile is at (6, 5), player at (5, 5)

    assert (player.x, player.y) == (5, 5)  # never walked onto/through the pile
    assert any(item.name == "Rag" for item in player.inventory.items)


def test_available_interactions_offers_search_for_debris():
    player = _make_player()
    pile = _make_debris_pile()
    engine = FakeEngine(player, _make_map_with(player, pile))

    options = available_interactions(player, engine, 6, 5)

    assert len(options) == 1
    assert options[0].label == "Search Debris Pile"
    assert isinstance(options[0].action, SearchDebrisAction)
