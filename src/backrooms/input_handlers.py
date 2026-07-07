from __future__ import annotations

from typing import TYPE_CHECKING

import tcod.event

from backrooms.actions import (
    Action,
    AutoExploreAction,
    BarterAction,
    BumpAction,
    CraftAction,
    EscapeAction,
    PickupAction,
    ToggleCharacterScreenAction,
    ToggleInventoryAction,
    ToggleLightAction,
    ToggleLookModeAction,
    TravelToAction,
    UseItemAction,
    WaitAction,
)

if TYPE_CHECKING:
    from backrooms.engine import Engine
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
    tcod.event.KeySym.KP_8: (0, -1),
    tcod.event.KeySym.KP_2: (0, 1),
    tcod.event.KeySym.KP_4: (-1, 0),
    tcod.event.KeySym.KP_6: (1, 0),
    tcod.event.KeySym.KP_7: (-1, -1),
    tcod.event.KeySym.KP_9: (1, -1),
    tcod.event.KeySym.KP_1: (-1, 1),
    tcod.event.KeySym.KP_3: (1, 1),
}

WAIT_KEYS = {tcod.event.KeySym.PERIOD, tcod.event.KeySym.KP_5}
CHARACTER_SCREEN_KEYS = {tcod.event.KeySym.C, tcod.event.KeySym.TAB}
LOOK_KEYS = {tcod.event.KeySym.X}
INVENTORY_KEYS = {tcod.event.KeySym.I}
PICKUP_KEYS = {tcod.event.KeySym.G}
LIGHT_KEYS = {tcod.event.KeySym.F}
AUTO_EXPLORE_KEYS = {tcod.event.KeySym.HOME}
CRAFT_KEYS = {tcod.event.KeySym.R}

# Top-row number keys (not the numpad -- those are already movement) select
# an inventory slot while the inventory screen is open.
INVENTORY_SLOT_KEYS = {
    tcod.event.KeySym.N1: 0,
    tcod.event.KeySym.N2: 1,
    tcod.event.KeySym.N3: 2,
    tcod.event.KeySym.N4: 3,
    tcod.event.KeySym.N5: 4,
    tcod.event.KeySym.N6: 5,
    tcod.event.KeySym.N7: 6,
    tcod.event.KeySym.N8: 7,
    tcod.event.KeySym.N9: 8,
}

# Same layout as INVENTORY_SLOT_KEYS, kept as its own constant since it's
# used by an unrelated screen (main.py's pre-game class selection).
CLASS_SELECT_KEYS = dict(INVENTORY_SLOT_KEYS)


class EventHandler(tcod.event.EventDispatch[Action]):
    """Translates raw tcod events into Action objects for a given actor (the
    player). Holds the engine only so the shared number-key row can be routed
    to whichever modal screen is open (the barter screen vs. the inventory)."""

    def __init__(self, actor: "Entity", engine: "Engine") -> None:
        self.actor = actor
        self.engine = engine

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
        if key in CHARACTER_SCREEN_KEYS:
            return ToggleCharacterScreenAction(self.actor)
        if key in LOOK_KEYS:
            return ToggleLookModeAction(self.actor)
        if key in INVENTORY_KEYS:
            return ToggleInventoryAction(self.actor)
        if key in PICKUP_KEYS:
            return PickupAction(self.actor)
        if key in LIGHT_KEYS:
            return ToggleLightAction(self.actor)
        if key in AUTO_EXPLORE_KEYS:
            return AutoExploreAction(self.actor)
        if key in CRAFT_KEYS:
            return CraftAction(self.actor)
        if key in INVENTORY_SLOT_KEYS:
            # The number row means "pick offer N" while the barter screen is
            # open, and "use/equip slot N" otherwise -- the two never coexist
            # (both are modal), and main.MODE_ALLOWED_ACTIONS gates each so a
            # stray number key does nothing outside its own screen.
            slot = INVENTORY_SLOT_KEYS[key]
            if self.engine.show_barter:
                return BarterAction(self.actor, slot)
            return UseItemAction(self.actor, slot)
        if key in MOVE_KEYS:
            dx, dy = MOVE_KEYS[key]
            return BumpAction(self.actor, dx, dy)
        if key in WAIT_KEYS:
            return WaitAction(self.actor)
        return None

    def ev_mousebuttondown(self, event: tcod.event.MouseButtonDown) -> Action | None:
        # event.position is only in tile coordinates once main.py has run the
        # raw event through context.convert_event -- pixel coordinates alone
        # can't be mapped to a map tile without knowing the tileset/window
        # size, which this class has no access to.
        if event.button != tcod.event.MouseButton.LEFT:
            return None
        x, y = event.integer_position
        return TravelToAction(self.actor, x, y)
