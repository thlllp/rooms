"""Generic consumable component, mirroring hazard.py's shape: a component
that just wraps an effect callable, plus factories for concrete effects, so
new consumable kinds are new factories rather than new component classes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from backrooms.constants import Color
from backrooms.entity.components.base_component import BaseComponent

if TYPE_CHECKING:
    from backrooms.engine import Engine
    from backrooms.entity.entity import Entity


class ConsumableComponent(BaseComponent):
    def __init__(self, use_effect: Callable[["Entity", "Engine"], None]) -> None:
        self.use_effect = use_effect

    def use(self, user: "Entity", engine: "Engine") -> None:
        self.use_effect(user, engine)


def make_sanity_restore_item(amount: float = 30.0) -> ConsumableComponent:
    def _use(user: "Entity", engine: "Engine") -> None:
        if user.sanity is None:
            engine.message_log.add_message("Nothing seems to happen.", color=Color.GREY)
            return
        before = user.sanity.current
        user.sanity.restore(amount)
        gained = user.sanity.current - before
        engine.message_log.add_message(f"A strange calm settles in. (+{gained:.0f} sanity)", color=Color.SANITY_BAR_FULL)

    return ConsumableComponent(_use)


def make_hp_restore_item(amount: float = 15.0) -> ConsumableComponent:
    def _use(user: "Entity", engine: "Engine") -> None:
        if user.fighter is None:
            engine.message_log.add_message("Nothing seems to happen.", color=Color.GREY)
            return
        before = user.fighter.hp
        user.fighter.heal(amount)
        gained = user.fighter.hp - before
        engine.message_log.add_message(f"You feel a little steadier. (+{gained:.0f} HP)", color=Color.HP_BAR_FULL)

    return ConsumableComponent(_use)


def make_hp_for_sanity_item(*, hp_amount: float = 20.0, sanity_cost: float = 10.0) -> ConsumableComponent:
    """Trade-off consumable: heals HP but drains sanity in exchange -- relief
    with a cost, matching Liquid Pain's flavor."""

    def _use(user: "Entity", engine: "Engine") -> None:
        if user.fighter is None:
            engine.message_log.add_message("Nothing seems to happen.", color=Color.GREY)
            return
        user.fighter.heal(hp_amount)
        if user.sanity is not None:
            user.sanity.drain(sanity_cost)
        engine.message_log.add_message(
            f"The pain fades, but something else creeps in. (+{hp_amount:.0f} HP, -{sanity_cost:.0f} sanity)",
            color=Color.WARNING,
        )

    return ConsumableComponent(_use)
