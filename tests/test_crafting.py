import pytest

import backrooms.actions as actions
from backrooms.actions import CraftAction
from backrooms.entity.components.inventory import Inventory
from backrooms.entity.components.tool import make_sewing_kit
from backrooms.entity.entity import Entity, RenderOrder
from backrooms.world.crafting import CraftingRecipe


class FakeLog:
    def __init__(self):
        self.messages = []

    def add_message(self, text, color=None):
        self.messages.append(text)


class FakeEngine:
    def __init__(self, player):
        self.player = player
        self.message_log = FakeLog()


def _make_player():
    return Entity(0, 0, char="@", color=(255, 255, 255), name="Player", render_order=RenderOrder.PLAYER, inventory=Inventory(capacity=10))


def _make_sewing_kit(*, max_uses=5):
    return Entity(0, 0, char="k", color=(200, 190, 170), name="Sewing Kit", render_order=RenderOrder.ITEM, tool=make_sewing_kit(max_uses=max_uses))


def _make_thread():
    return Entity(0, 0, char="-", color=(200, 200, 200), name="Thread", render_order=RenderOrder.ITEM)


def _make_patched_shirt():
    return Entity(0, 0, char="s", color=(150, 70, 60), name="Patched Shirt", render_order=RenderOrder.ITEM)


def _recipe_requiring_sewing_kit():
    return CraftingRecipe(
        name="Patched Shirt", ingredients=("Thread",), result_factory=_make_patched_shirt, required_tool="Sewing Kit"
    )


def test_recipe_with_no_ingredients_is_rejected_at_construction():
    # A zero-ingredient recipe would match every craft press and append its
    # result each time without consuming anything -- an infinite item printer.
    with pytest.raises(ValueError):
        CraftingRecipe(name="Nothing", ingredients=(), result_factory=_make_patched_shirt)


def test_recipe_whose_required_tool_is_also_an_ingredient_is_rejected():
    # CraftAction would remove the tool item as the ingredient, then try to
    # spend a charge on the already-removed item -> ValueError mid-craft.
    with pytest.raises(ValueError):
        CraftingRecipe(
            name="Bad", ingredients=("Sewing Kit",), result_factory=_make_patched_shirt, required_tool="Sewing Kit"
        )


def test_crafting_with_required_tool_consumes_one_charge_but_keeps_the_tool(monkeypatch):
    monkeypatch.setattr(actions, "CRAFTING_RECIPES", [_recipe_requiring_sewing_kit()])
    player = _make_player()
    kit = _make_sewing_kit(max_uses=5)
    thread = _make_thread()
    player.inventory.items.extend([kit, thread])
    engine = FakeEngine(player)

    CraftAction(player).perform(engine)

    assert kit in player.inventory.items  # tool survives, unlike an ingredient
    assert kit.tool.charges.remaining == 4
    assert any(item.name == "Patched Shirt" for item in player.inventory.items)
    assert not any(item.name == "Thread" for item in player.inventory.items)  # ingredient consumed


def test_crafting_without_required_tool_held_does_not_match_the_recipe(monkeypatch):
    monkeypatch.setattr(actions, "CRAFTING_RECIPES", [_recipe_requiring_sewing_kit()])
    player = _make_player()
    player.inventory.items.append(_make_thread())  # thread but no sewing kit
    engine = FakeEngine(player)

    CraftAction(player).perform(engine)

    assert not any(item.name == "Patched Shirt" for item in player.inventory.items)
    assert any(item.name == "Thread" for item in player.inventory.items)  # untouched


def test_sewing_kit_is_discarded_once_its_last_charge_is_used(monkeypatch):
    monkeypatch.setattr(actions, "CRAFTING_RECIPES", [_recipe_requiring_sewing_kit()])
    player = _make_player()
    kit = _make_sewing_kit(max_uses=1)
    thread = _make_thread()
    player.inventory.items.extend([kit, thread])
    engine = FakeEngine(player)

    CraftAction(player).perform(engine)

    assert kit not in player.inventory.items
    assert any("used up" in m for m in engine.message_log.messages)
