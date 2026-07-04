from __future__ import annotations

from typing import TYPE_CHECKING

import tcod.event

from backrooms.actions import Action, EscapeAction, MovementAction, WaitAction

if TYPE_CHECKING:
    from backrooms.entity.entity import Entity

MOVE_KEYS = {
    tcod.event.KeySym.UP: (0, -1),
    tcod.event.KeySym.K: (0, -1),
    tcod.event.KeySym.DOWN: (0, 1),
    tcod.event.KeySym.J: (0, 1),
    tcod.event.KeySym.LEFT: (-1, 0),
    tcod.event.KeySym.H: (-1, 0),
    tcod.event.KeySym.RIGHT: (1, 0),
    tcod.event.KeySym.L: (1, 0),
    tcod.event.KeySym.Y: (-1, -1),
    tcod.event.KeySym.U: (1, -1),
    tcod.event.KeySym.B: (-1, 1),
    tcod.event.KeySym.N: (1, 1),
}

WAIT_KEYS = {tcod.event.KeySym.PERIOD, tcod.event.KeySym.KP_5}


class EventHandler(tcod.event.EventDispatch[Action]):
    """Translates raw tcod events into Action objects for a given actor (the player)."""

    def __init__(self, actor: "Entity") -> None:
        self.actor = actor

    def ev_quit(self, event: tcod.event.Quit) -> Action | None:
        raise SystemExit()

    def ev_undefined(self, event: tcod.event.Event) -> Action | None:
        return None

    def ev_pixelsizechanged(self, event: tcod.event.Event) -> Action | None:
        return None

    def ev_displayscalechanged(self, event: tcod.event.Event) -> Action | None:
        return None

    def ev_keydown(self, event: tcod.event.KeyDown) -> Action | None:
        key = event.sym

        if key == tcod.event.KeySym.ESCAPE:
            return EscapeAction(self.actor)
        if key in MOVE_KEYS:
            dx, dy = MOVE_KEYS[key]
            return MovementAction(self.actor, dx, dy)
        if key in WAIT_KEYS:
            return WaitAction(self.actor)
        return None
