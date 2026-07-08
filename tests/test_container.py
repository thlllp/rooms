import backrooms.data.registrations  # noqa: F401 -- populates factories/registry
from backrooms.actions import BumpAction, OpenContainerAction
from backrooms.entity.components.container import ContainerComponent
from backrooms.entity.components.hazard import LootEntry
from backrooms.entity.components.inventory import Inventory
from backrooms.entity.entity import Entity, RenderOrder
from backrooms.world import tile_types
from backrooms.world.game_map import GameMap


class FakeLog:
    def __init__(self):
        self.messages = []

    def add_message(self, text, color=None):
        self.messages.append(text)


class StubRng:
    """Weighted pick is deterministic here: choices() always returns the
    pool entry at `index`, so a test can name exactly which item comes out."""

    def __init__(self, index=0):
        self.index = index

    def choices(self, population, weights=None, k=1):
        return [population[self.index]]


class FakeEngine:
    def __init__(self, player, game_map, *, pick_index=0):
        self.player = player
        self.game_map = game_map
        self.message_log = FakeLog()
        self.rng = StubRng(pick_index)
        self.look_mode = False


def _make_player(*, inventory_capacity=10):
    return Entity(
        5, 5, char="@", color=(255, 255, 255), name="Player", blocks_movement=True, render_order=RenderOrder.PLAYER,
        inventory=Inventory(capacity=inventory_capacity),
    )


def _make_nails():
    return Entity(0, 0, char=";", color=(170, 170, 180), name="Nails", render_order=RenderOrder.ITEM)


def _make_nailgun():
    return Entity(0, 0, char="7", color=(210, 180, 60), name="Nailgun", render_order=RenderOrder.ITEM)


def _make_toolbox():
    return Entity(
        6, 5, char="t", color=(180, 60, 50), name="Toolbox", blocks_movement=True, render_order=RenderOrder.HAZARD,
        container=ContainerComponent(loot_pool=(LootEntry(_make_nails), LootEntry(_make_nailgun, weight=0.1))),
    )


def _make_map_with(*entities):
    game_map = GameMap(10, 10, wall_tile=tile_types.WALL)
    game_map.tiles[:, :] = tile_types.FLOOR
    for entity in entities:
        game_map.entities.add(entity)
    return game_map


def test_opening_a_container_yields_a_pooled_item_and_removes_the_container():
    player = _make_player()
    toolbox = _make_toolbox()
    game_map = _make_map_with(player, toolbox)
    engine = FakeEngine(player, game_map, pick_index=1)  # -> Nailgun

    OpenContainerAction(player, target=toolbox).perform(engine)

    assert toolbox not in game_map.entities  # one-shot, consumed
    assert any(item.name == "Nailgun" for item in player.inventory.items)
    assert any("open the Toolbox and find a Nailgun" in m for m in engine.message_log.messages)


def test_opening_a_full_pack_drops_the_find_on_the_ground():
    player = _make_player(inventory_capacity=0)
    toolbox = _make_toolbox()
    game_map = _make_map_with(player, toolbox)
    engine = FakeEngine(player, game_map, pick_index=0)  # -> Nails

    OpenContainerAction(player, target=toolbox).perform(engine)

    assert toolbox not in game_map.entities  # still emptied even if it didn't fit
    assert not player.inventory.items
    assert any(e.name == "Nails" for e in game_map.entities)  # left on the floor
    assert any("stays on the ground" in m for m in engine.message_log.messages)


def test_bumping_a_container_opens_it_instead_of_moving():
    player = _make_player()
    toolbox = _make_toolbox()
    game_map = _make_map_with(player, toolbox)
    engine = FakeEngine(player, game_map, pick_index=0)

    BumpAction(player, 1, 0).perform(engine)  # toolbox is at (6, 5), player at (5, 5)

    assert (player.x, player.y) == (5, 5)  # never moved onto the toolbox tile
    assert any(item.name == "Nails" for item in player.inventory.items)


def test_real_toolbox_pool_is_the_expected_tools():
    toolbox = backrooms.data.registrations._spawn_toolbox()
    names = {entry.factory().name for entry in toolbox.container.loot_pool}
    assert names == {"Nails", "Scissors", "Sewing Kit", "Nailgun"}


def test_toolboxes_can_spawn_on_levels_1_22_and_2_and_3():
    from backrooms.world.level_registry import LEVEL_REGISTRY

    def has_toolbox(level_id):
        level = LEVEL_REGISTRY[level_id]
        entries = level.hazard_table + level.furniture_table
        return any(entry.factory().name == "Toolbox" for entry in entries)

    assert has_toolbox("level_1_22")  # original placement
    assert has_toolbox("level_2_garage")  # newly added
    assert has_toolbox("level_3_pipeworks")  # newly added
