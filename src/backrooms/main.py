from __future__ import annotations

import argparse

import tcod
import tcod.event

import backrooms.data.registrations  # noqa: F401  (side effect: populates LEVEL_REGISTRY)
from backrooms.constants import (
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TILE_HEIGHT,
    TILE_WIDTH,
    TILESET_PATH,
    Color,
    WINDOW_TITLE,
)
from backrooms.actions import (
    AutoExploreAction,
    BumpAction,
    EscapeAction,
    ToggleCharacterScreenAction,
    ToggleInventoryAction,
    ToggleLookModeAction,
    UseItemAction,
)
from backrooms.data.player_classes import PLAYER_CLASSES, PlayerClass, build_player
from backrooms.engine import MODAL_FLAGS, Engine
from backrooms.input_handlers import CLASS_SELECT_KEYS, EventHandler
from backrooms.rendering.renderer import render_all
from backrooms.world.level_registry import LEVEL_REGISTRY

# HP/sanity given to the player when --dev-level is used -- not literally
# infinite, just large enough that no realistic damage/drain source could
# exhaust it in one dev session, without needing take_damage/drain
# themselves to know anything about a "god mode".
DEV_INVINCIBLE_POOL = 999_999

# Which action types are legal while a given modal screen is open. Keyed by
# exactly the flags in engine.MODAL_FLAGS (asserted below) -- adding a new
# modal means one new dict entry here plus adding its flag name to
# MODAL_FLAGS, instead of a new hand-written isinstance check in the event
# loop that's easy to get wrong (this table is what replaced the bug where
# show_character_screen was never reset on a level transition).
MODE_ALLOWED_ACTIONS: dict[str, tuple[type, ...]] = {
    "show_character_screen": (ToggleCharacterScreenAction, EscapeAction),
    "look_mode": (BumpAction, ToggleLookModeAction, EscapeAction),
    "show_inventory": (UseItemAction, ToggleInventoryAction, EscapeAction),
}
assert set(MODE_ALLOWED_ACTIONS) == set(MODAL_FLAGS), "MODE_ALLOWED_ACTIONS must cover exactly Engine.MODAL_FLAGS"

AUTO_EXPLORE_STEPS_PER_SECOND = 45
AUTO_EXPLORE_STEP_INTERVAL = 1.0 / AUTO_EXPLORE_STEPS_PER_SECOND


def _is_action_allowed(engine: Engine, action) -> bool:
    if engine.game_over:
        return isinstance(action, EscapeAction)

    active_mode = next((flag for flag in MODAL_FLAGS if getattr(engine, flag)), None)
    if active_mode is not None:
        return isinstance(action, MODE_ALLOWED_ACTIONS[active_mode])

    return not isinstance(action, UseItemAction)  # number keys do nothing outside the inventory screen


def _perform_if_allowed(engine: Engine, action) -> None:
    """Shared by the normal input loop and the auto-explore interrupt path,
    so an action that interrupts a run is actually performed -- gated by
    _is_action_allowed and costing a turn exactly like any other action --
    instead of the interrupt just being silently swallowed."""
    if not _is_action_allowed(engine, action):
        return
    action.perform(engine)
    if not engine.game_over and action.costs_turn:
        engine.advance_turn()


def _select_player_class(console: "tcod.console.Console", context: "tcod.context.Context") -> PlayerClass:
    """Blocking pre-game screen: pick one of PLAYER_CLASSES with a number
    key, same layout as the inventory's slot keys (see CLASS_SELECT_KEYS)."""
    while True:
        console.clear(ch=ord(" "), fg=Color.WHITE, bg=Color.BLACK)
        console.print(4, 2, "Choose your character", fg=Color.WHITE)
        for i, player_class in enumerate(PLAYER_CLASSES):
            row = 4 + i * 2
            console.print(4, row, f"[{i + 1}] {player_class.display_name}", fg=Color.WHITE)
            console.print(8, row + 1, player_class.description, fg=Color.GREY)
        context.present(console)

        for event in tcod.event.wait():
            if isinstance(event, tcod.event.Quit):
                raise SystemExit()
            if isinstance(event, tcod.event.KeyDown):
                index = CLASS_SELECT_KEYS.get(event.sym)
                if index is not None and index < len(PLAYER_CLASSES):
                    return PLAYER_CLASSES[index]


def main() -> None:
    parser = argparse.ArgumentParser(description="Backrooms")
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Dev mode: print each level's entrance/exits/entities to stdout on load.",
    )
    parser.add_argument(
        "--dev-level",
        choices=sorted(LEVEL_REGISTRY),
        default=None,
        help="Dev mode: start on this level id instead of the normal entry level, with effectively infinite HP/sanity.",
    )
    args = parser.parse_args()

    tileset = tcod.tileset.load_truetype_font(str(TILESET_PATH), TILE_WIDTH, TILE_HEIGHT)
    with tcod.context.new(
        columns=SCREEN_WIDTH,
        rows=SCREEN_HEIGHT,
        tileset=tileset,
        title=WINDOW_TITLE,
    ) as context:
        console = context.new_console(order="F")

        player_class = _select_player_class(console, context)
        player = build_player(player_class)
        if args.dev_level is not None:
            if player.fighter is not None:
                player.fighter.max_hp = DEV_INVINCIBLE_POOL
                player.fighter.hp = DEV_INVINCIBLE_POOL
            if player.sanity is not None:
                player.sanity.max_sanity = DEV_INVINCIBLE_POOL
                player.sanity.current = DEV_INVINCIBLE_POOL
        engine = Engine(player=player, dev_mode=args.dev, start_level_id=args.dev_level)
        if args.dev_level is not None:
            engine.message_log.add_message(
                f"DEV MODE: started on '{args.dev_level}', HP/sanity effectively infinite.", color=Color.WARNING
            )
        event_handler = EventHandler(actor=player)

        while True:
            render_all(console, engine)
            context.present(console)

            if engine.auto_exploring:
                # tcod.event.wait's own timeout blocks up to one step
                # interval and returns early the instant a real event
                # arrives -- no manual clock/sleep bookkeeping needed, and no
                # busy-loop re-rendering between steps. Only an action that
                # would actually be legal right now interrupts the run (and
                # is still actually performed via _perform_if_allowed) --
                # e.g. a stray number key outside the inventory screen is a
                # no-op either way and shouldn't silently cancel the run.
                for event in tcod.event.wait(AUTO_EXPLORE_STEP_INTERVAL):
                    action = event_handler.dispatch(event)
                    if action is None or not _is_action_allowed(engine, action):
                        continue
                    engine.auto_exploring = False
                    # AutoExploreAction itself just toggles the mode back on
                    # -- pressing Home again should stop the run, not
                    # immediately restart it.
                    if not isinstance(action, AutoExploreAction):
                        _perform_if_allowed(engine, action)
                if engine.auto_exploring:
                    engine.step_auto_explore()
                continue

            for event in tcod.event.wait():
                action = event_handler.dispatch(event)
                if action is None:
                    continue
                _perform_if_allowed(engine, action)


if __name__ == "__main__":
    main()
