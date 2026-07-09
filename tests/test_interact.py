from backrooms.actions import (
    Action,
    AttackAction,
    EscapeAction,
    InteractAction,
    InteractOption,
    OpenBarterAction,
    OpenContainerAction,
    OpenInteractMenuAction,
    PickupAction,
    SalvageAction,
    TalkAction,
    available_interactions,
)
from backrooms.entity.components.barter import BarterComponent
from backrooms.entity.components.container import ContainerComponent
from backrooms.entity.components.dialogue import DialogueComponent
from backrooms.entity.components.fighter import Fighter
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
        self.look_cursor = (player.x, player.y)
        self.show_interact = False
        self.interact_options = []
        self.show_barter = False
        self.barter_partner = None
        self.barter_greeting = ""


def _make_player(*, x=5, y=5, inventory_capacity=10):
    return Entity(
        x, y, char="@", color=(255, 255, 255), name="Player", blocks_movement=True,
        render_order=RenderOrder.PLAYER, inventory=Inventory(capacity=inventory_capacity),
    )


def _make_map_with(*entities):
    game_map = GameMap(10, 10, wall_tile=tile_types.WALL)
    game_map.tiles[:, :] = tile_types.FLOOR
    for entity in entities:
        game_map.entities.add(entity)
    return game_map


def _make_hollow():
    return Entity(
        6, 5, char="h", color=(255, 255, 255), name="Hollow", blocks_movement=True,
        render_order=RenderOrder.ACTOR, fighter=Fighter(hp=10, power=1),
    )


def _make_wanderer():
    return Entity(
        6, 5, char="w", color=(255, 255, 255), name="Wanderer", blocks_movement=True,
        render_order=RenderOrder.ACTOR, dialogue=DialogueComponent(lines=("Hello.",)),
    )


def _make_elder():
    return Entity(
        6, 5, char="e", color=(255, 255, 255), name="Elder", blocks_movement=True,
        render_order=RenderOrder.ACTOR, barter=BarterComponent(offers=()),
    )


def _make_chair_leg():
    return Entity(0, 0, char="/", color=(150, 110, 70), name="Chair Leg", render_order=RenderOrder.ITEM)


def _make_wooden_chair():
    return Entity(
        6, 5, char="C", color=(150, 110, 70), name="Wooden Chair", blocks_movement=True,
        render_order=RenderOrder.HAZARD, salvageable=SalvageableComponent(result_factory=_make_chair_leg, strength_required=5),
    )


def _make_toolbox():
    return Entity(
        6, 5, char="=", color=(150, 110, 70), name="Toolbox", blocks_movement=True,
        render_order=RenderOrder.HAZARD, container=ContainerComponent(loot_pool=()),
    )


def _make_rag():
    return Entity(5, 5, char="r", color=(200, 200, 200), name="Rag", render_order=RenderOrder.ITEM)


def test_available_interactions_offers_attack_for_fighter():
    player = _make_player()
    hollow = _make_hollow()
    engine = FakeEngine(player, _make_map_with(player, hollow))

    options = available_interactions(player, engine, 6, 5)

    assert len(options) == 1
    assert options[0].label == "Attack Hollow"
    assert isinstance(options[0].action, AttackAction)
    assert options[0].action._target is hollow


def test_available_interactions_offers_talk_for_dialogue_entity():
    player = _make_player()
    wanderer = _make_wanderer()
    engine = FakeEngine(player, _make_map_with(player, wanderer))

    options = available_interactions(player, engine, 6, 5)

    assert len(options) == 1
    assert options[0].label == "Talk to Wanderer"
    assert isinstance(options[0].action, TalkAction)


def test_available_interactions_offers_trade_for_barter_entity():
    player = _make_player()
    elder = _make_elder()
    engine = FakeEngine(player, _make_map_with(player, elder))

    options = available_interactions(player, engine, 6, 5)

    assert len(options) == 1
    assert options[0].label == "Trade with Elder"
    assert isinstance(options[0].action, OpenBarterAction)


def test_available_interactions_offers_salvage_for_salvageable_furniture():
    player = _make_player()
    chair = _make_wooden_chair()
    engine = FakeEngine(player, _make_map_with(player, chair))

    options = available_interactions(player, engine, 6, 5)

    assert len(options) == 1
    assert options[0].label == "Salvage Wooden Chair"
    assert isinstance(options[0].action, SalvageAction)


def test_available_interactions_offers_open_for_container():
    player = _make_player()
    toolbox = _make_toolbox()
    engine = FakeEngine(player, _make_map_with(player, toolbox))

    options = available_interactions(player, engine, 6, 5)

    assert len(options) == 1
    assert options[0].label == "Open Toolbox"
    assert isinstance(options[0].action, OpenContainerAction)


def test_available_interactions_offers_pickup_only_on_players_own_tile():
    player = _make_player()
    rag = _make_rag()
    engine = FakeEngine(player, _make_map_with(player, rag))

    on_player_tile = available_interactions(player, engine, 5, 5)
    assert len(on_player_tile) == 1
    assert on_player_tile[0].label == "Pick up Rag"
    assert isinstance(on_player_tile[0].action, PickupAction)

    # Move the item one tile away -- no adjacent-tile pickup exists (matches
    # the G key, which only ever reads the player's own tile).
    rag.place(6, 5)
    elsewhere = available_interactions(player, engine, 6, 5)
    assert elsewhere == []


def test_available_interactions_combines_multiple_entities_on_one_tile():
    player = _make_player()
    toolbox = _make_toolbox()
    rag = Entity(6, 5, char="r", color=(200, 200, 200), name="Rag", render_order=RenderOrder.ITEM)
    engine = FakeEngine(player, _make_map_with(player, toolbox, rag))

    options = available_interactions(player, engine, 6, 5)

    # The Rag isn't on the player's own tile, so only the container shows up
    # -- pickup still requires standing on the item (see the test above).
    assert [o.label for o in options] == ["Open Toolbox"]


def test_open_interact_menu_does_nothing_outside_look_mode():
    player = _make_player()
    hollow = _make_hollow()
    engine = FakeEngine(player, _make_map_with(player, hollow))
    engine.look_mode = False
    engine.look_cursor = (6, 5)

    OpenInteractMenuAction(player).perform(engine)

    assert engine.show_interact is False
    assert engine.interact_options == []


def test_open_interact_menu_rejects_cursor_too_far_away():
    player = _make_player()
    engine = FakeEngine(player, _make_map_with(player))
    engine.look_mode = True
    engine.look_cursor = (player.x + 2, player.y)

    OpenInteractMenuAction(player).perform(engine)

    assert engine.show_interact is False
    assert "too far away" in engine.message_log.messages[0]


def test_open_interact_menu_reports_nothing_to_interact_with():
    player = _make_player()
    engine = FakeEngine(player, _make_map_with(player))
    engine.look_mode = True
    engine.look_cursor = (player.x + 1, player.y)

    OpenInteractMenuAction(player).perform(engine)

    assert engine.show_interact is False
    assert "nothing here" in engine.message_log.messages[0]


def test_open_interact_menu_opens_with_options_when_adjacent_and_populated():
    player = _make_player()
    hollow = _make_hollow()
    engine = FakeEngine(player, _make_map_with(player, hollow))
    engine.look_mode = True
    engine.look_cursor = (6, 5)

    action = OpenInteractMenuAction(player)
    action.perform(engine)

    assert engine.show_interact is True
    assert action.costs_turn is False
    assert [o.label for o in engine.interact_options] == ["Attack Hollow"]


class RecordingAction(Action):
    def __init__(self, entity, *, costs_turn=True):
        super().__init__(entity)
        self.costs_turn = costs_turn
        self.performed = False

    def perform(self, engine):
        self.performed = True


def test_interact_action_performs_selected_option_and_closes_menu():
    player = _make_player()
    engine = FakeEngine(player, _make_map_with(player))
    recorded = RecordingAction(player, costs_turn=False)
    engine.show_interact = True
    engine.interact_options = [InteractOption("Do a thing", recorded)]

    action = InteractAction(player, 0)
    action.perform(engine)

    assert recorded.performed is True
    assert engine.show_interact is False
    assert engine.interact_options == []
    assert action.costs_turn is False


def test_interact_action_out_of_range_index_is_a_free_noop():
    player = _make_player()
    engine = FakeEngine(player, _make_map_with(player))
    recorded = RecordingAction(player)
    engine.show_interact = True
    engine.interact_options = [InteractOption("Do a thing", recorded)]

    action = InteractAction(player, 5)
    action.perform(engine)

    assert recorded.performed is False
    assert engine.show_interact is False
    assert action.costs_turn is False


def test_escape_closes_interact_menu_before_look_mode():
    player = _make_player()
    engine = FakeEngine(player, _make_map_with(player))
    engine.look_mode = True
    engine.show_interact = True
    engine.interact_options = [InteractOption("x", RecordingAction(player))]

    EscapeAction(player).perform(engine)
    assert engine.show_interact is False
    assert engine.interact_options == []
    assert engine.look_mode is True

    EscapeAction(player).perform(engine)
    assert engine.look_mode is False
