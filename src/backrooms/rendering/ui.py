from __future__ import annotations

from typing import TYPE_CHECKING

from backrooms.constants import Color
from backrooms.world.level_registry import LEVEL_REGISTRY

if TYPE_CHECKING:
    import tcod.console

    from backrooms.engine import Engine

SANITY_BAND_COLOR = {
    "normal": Color.SANITY_BAR_FULL,
    "mild": Color.WARNING,
    "severe": Color.SANITY_BAR_LOW,
    "critical": Color.HAZARD,
}

TILE_LABELS = {
    "wall": "Wall",
    "floor": "Floor",
    "stairs_down": "Stairway Down",
    "door_exit": "Door",
    "garage_wall": "Concrete Wall",
    "garage_floor": "Concrete Floor",
    "settlement_door": "Door",
    "settlement_floor": "Floor",
    "inn_floor": "Inn Floor",
    "pipeworks_wall": "Pipe-Lined Wall",
    "pipeworks_floor": "Tiled Floor",
    "remodeled_wall": "Drywall",
    "remodeled_floor": "Plywood Subfloor",
    "cold_wall": "Frosted Wall",
    "cold_floor": "Iced Floor",
    "flooded_wall": "Water-Stained Wall",
    "flooded_floor": "Flooded Floor",
}

# Flavor text pools for look mode, keyed by tile_id. Several lines per kind
# so identical tiles don't all read the same -- see _tile_flavor for how one
# is picked per-position.
TILE_DESCRIPTIONS: dict[str, tuple[str, ...]] = {
    "wall": (
        "Water-damaged wallpaper, the pattern almost recognizable.",
        "Yellowed and warm to the touch, like it's running a low fever.",
        "A faint electrical hum comes from somewhere inside it.",
        "The seams don't quite line up if you look too closely.",
    ),
    "floor": (
        "Damp, mustard-colored carpet that squelches faintly underfoot.",
        "The carpet pattern seems to drift when you're not looking at it.",
        "Worn smooth in a path that leads nowhere in particular.",
        "Faintly sticky, and smells like old rain.",
    ),
    "stairs_down": (
        "A plain stairway leading down, out of place in a building with no other floors.",
        "The steps are bare concrete, the only surface here that isn't carpet or wallpaper.",
    ),
    "door_exit": (
        "A plain door set into the wall, unremarkable except that it wasn't there before.",
        "Unmarked, unlabeled, and slightly ajar.",
        "The handle is cold. Everything else in this place is room-temperature.",
        "It looks like every other door you've never seen in a building like this.",
    ),
    "garage_wall": (
        "Bare grey concrete, streaked with a long-dried water stain.",
        "A faded parking-lane number stenciled at eye height, the digit illegible.",
        "Cold to the touch, and perfectly silent.",
        "A rusted conduit runs along it and disappears into the concrete.",
    ),
    "garage_floor": (
        "Grey concrete, cracked in a long spiderweb pattern.",
        "A dark oil stain, long since dried, in the shape of nothing in particular.",
        "Faint tire marks curve toward a wall and stop.",
        "A painted parking line, faded almost to nothing.",
    ),
    "settlement_door": (
        "Someone's reinforced this door from the other side.",
        "A door that actually looks like it was built by a person, on purpose.",
    ),
    "settlement_floor": (
        "Swept clean. Someone's been keeping this place up.",
        "Warm underfoot, somehow -- the first surface here that feels lived-in.",
        "Someone's laid out mismatched rugs to cover the worst of the floor.",
    ),
    "inn_floor": (
        "A few threadbare bedrolls and a pot that's always warm.",
        "Someone's turned this room into somewhere to actually rest.",
        "It smells like food, faintly. You feel steadier just standing here.",
    ),
    "pipeworks_wall": (
        "Brown rust bleeds down the grey concrete in long streaks.",
        "A cluster of pipes disappears into the wall and never comes back out.",
        "Warm to the touch, and it hums faintly, like something's moving inside.",
        "Grey and brown in patches, like it was patched together from two different buildings.",
    ),
    "pipeworks_floor": (
        "Brown ceramic tile, cracked in a grid where the pipes run underneath.",
        "Warm underfoot -- something down there is still running.",
        "A faint metallic smell rises from between the tiles.",
        "Condensation beads along a seam and drips somewhere out of sight.",
    ),
    "remodeled_wall": (
        "Fresh drywall, taped at the seams but never painted.",
        "Someone's pencil marks and a stud line, like the work stopped mid-measure.",
        "The primer's still tacky in places. Nobody's touched it in a long time.",
        "Smooth, pale, and blank -- too new for a building this quiet.",
    ),
    "remodeled_floor": (
        "Bare plywood subfloor, the tongue-and-groove seams still exposed.",
        "Sawdust drifts in the corners. The tools that made it are nowhere in sight.",
        "It flexes very slightly underfoot, like it was never quite finished.",
        "Chalk snap-lines cross the boards toward a wall that isn't there.",
    ),
    "cold_wall": (
        "Frost furs the wallpaper in feathered white crystals.",
        "It's cold enough to burn. Your breath fogs and hangs in the air.",
        "A faint static prickle runs up your arm as you near it.",
        "The wall creaks -- and you're no longer sure it's where it was a moment ago.",
    ),
    "cold_floor": (
        "A skin of ice over the carpet, crunching underfoot.",
        "So cold it aches through your shoes. Nothing grows here, nothing lasts.",
        "Your light seems thinner here, like the dark is drinking it.",
        "Rime spreads from your footprints in slow, branching lines.",
    ),
    "flooded_wall": (
        "Black mold blooms across the swollen, peeling wallpaper.",
        "Water seeps down it in dark sheets and pools at the base.",
        "The drywall has gone soft and bulging, ready to sag inward.",
        "Old tide-lines stripe it, each one higher than the last.",
    ),
    "flooded_floor": (
        "Ankle-deep water, brown and still, with an oily sheen on top.",
        "Something rotten rises off the standing water in a warm reek.",
        "The water laps at your shins. You don't want it in any open cut.",
        "Ripples spread from your steps and don't quite settle again.",
    ),
}


def _tile_flavor(tile_id: str, x: int, y: int) -> str | None:
    """Deterministic per-position pick so the text stays put across frames
    while the look cursor rests on one tile, instead of flickering each
    render. Uses a plain integer hash rather than Python's `hash()` since
    `tile_id` is a str and str hashing is randomized per-process."""
    pool = TILE_DESCRIPTIONS.get(tile_id)
    if not pool:
        return None
    index = (x * 73856093 ^ y * 19349663) % len(pool)
    return pool[index]


def render_message_log(console: "tcod.console.Console", engine: "Engine", *, x: int, y: int, height: int) -> None:
    for i, (text, color) in enumerate(engine.message_log.tail(height)):
        console.print(x, y + i, text, fg=color)


def render_sanity_bar(console: "tcod.console.Console", engine: "Engine", *, x: int, y: int, width: int) -> None:
    sanity = engine.player.sanity
    if sanity is None:
        return

    ratio = max(0.0, min(1.0, sanity.current / sanity.max_sanity)) if sanity.max_sanity else 0.0
    filled_width = round(width * ratio)
    bar_color = SANITY_BAND_COLOR[sanity.band.name]

    console.draw_rect(x=x, y=y, width=width, height=1, ch=ord(" "), bg=Color.SANITY_BAR_EMPTY)
    if filled_width > 0:
        console.draw_rect(x=x, y=y, width=filled_width, height=1, ch=ord(" "), bg=bar_color)

    label = f"SANITY {int(sanity.current)}/{int(sanity.max_sanity)}"
    console.print(x + 1, y, label, fg=Color.WHITE)


def render_hp_bar(console: "tcod.console.Console", engine: "Engine", *, x: int, y: int, width: int) -> None:
    fighter = engine.player.fighter
    if fighter is None:
        return

    ratio = max(0.0, min(1.0, fighter.hp / fighter.max_hp)) if fighter.max_hp else 0.0
    filled_width = round(width * ratio)

    console.draw_rect(x=x, y=y, width=width, height=1, ch=ord(" "), bg=Color.SANITY_BAR_EMPTY)
    if filled_width > 0:
        console.draw_rect(x=x, y=y, width=filled_width, height=1, ch=ord(" "), bg=Color.HP_BAR_FULL)

    label = f"HP {int(fighter.hp)}/{fighter.max_hp}"
    console.print(x + 1, y, label, fg=Color.WHITE)


def render_hunger_bar(console: "tcod.console.Console", engine: "Engine", *, x: int, y: int, width: int) -> None:
    hunger = engine.player.hunger
    if hunger is None:
        return

    ratio = max(0.0, min(1.0, hunger.current / hunger.max_hunger)) if hunger.max_hunger else 0.0
    filled_width = round(width * ratio)

    console.draw_rect(x=x, y=y, width=width, height=1, ch=ord(" "), bg=Color.SANITY_BAR_EMPTY)
    if filled_width > 0:
        console.draw_rect(x=x, y=y, width=filled_width, height=1, ch=ord(" "), bg=Color.HUNGER_BAR_FULL)

    label = f"HUNGER {int(hunger.current)}/{int(hunger.max_hunger)}"
    console.print(x + 1, y, label, fg=Color.WHITE)


def render_fuel_bar(console: "tcod.console.Console", engine: "Engine", *, x: int, y: int, width: int) -> None:
    light = engine.player.light_source
    if light is None:
        return

    ratio = max(0.0, min(1.0, light.fuel / light.max_fuel)) if light.max_fuel else 0.0
    filled_width = round(width * ratio)

    console.draw_rect(x=x, y=y, width=width, height=1, ch=ord(" "), bg=Color.SANITY_BAR_EMPTY)
    if filled_width > 0:
        console.draw_rect(x=x, y=y, width=filled_width, height=1, ch=ord(" "), bg=Color.FUEL_BAR_FULL)

    state = "lit" if light.is_lit else "out"
    label = f"FUEL {int(light.fuel)}/{int(light.max_fuel)} ({state})"
    console.print(x + 1, y, label, fg=Color.WHITE)


def render_level_banner(console: "tcod.console.Console", engine: "Engine") -> None:
    """Small boxed label in the map's top-right corner naming the current
    level -- drawn over the map itself, not the bottom UI panel, since it
    needs to stay visible regardless of panel_height/look-mode layout."""
    text = LEVEL_REGISTRY[engine.current_level_id].display_name
    width = len(text) + 4
    height = 3
    x = console.width - width - 1
    y = 1

    console.draw_frame(x=x, y=y, width=width, height=height, clear=True, fg=Color.WHITE, bg=Color.BLACK, decoration="+-+| |+-+")
    console.print(x + 2, y + 1, text, fg=Color.WHITE)


def describe_tile(engine: "Engine", x: int, y: int) -> str:
    """Text shown by look mode. Deliberately reads only what the player
    already legitimately knows: unexplored tiles reveal nothing, explored-
    but-not-visible tiles reveal only the remembered tile (no entities, since
    entity presence isn't part of the fog-of-war memory), and only currently
    visible tiles reveal what's standing there -- by `.name`, same as normal
    rendering, so this can't be used to unmask a hallucination (fakes already
    render with the generic name "???", same as everything else)."""
    game_map = engine.game_map
    if not game_map.in_bounds(x, y):
        return "Out of bounds."
    if not game_map.explored[x, y]:
        return "You haven't been here."

    tile_id = game_map.tile_id_at(x, y)
    label = TILE_LABELS.get(tile_id, tile_id or "Unknown")

    if not game_map.visible[x, y]:
        return f"{label} (remembered)."

    occupants = [e.name for e in game_map.entities_at(x, y) if e is not engine.player]
    if occupants:
        return f"{label} -- {', '.join(occupants)}."
    return f"{label}."


def tile_flavor_line(engine: "Engine", x: int, y: int) -> str:
    """Second look-mode line: tile flavor text, or '' if not applicable.
    Always called (even when it'll be blank) so render_ui can reserve a
    fixed two-line block for look mode and the message log below it doesn't
    jitter depending on whether the tile has flavor text."""
    game_map = engine.game_map
    if not game_map.in_bounds(x, y) or not game_map.explored[x, y]:
        return ""
    tile_id = game_map.tile_id_at(x, y)
    return _tile_flavor(tile_id, x, y) or ""


def render_look_cursor(console: "tcod.console.Console", engine: "Engine") -> None:
    x, y = engine.look_cursor
    if 0 <= x < console.width and 0 <= y < console.height:
        console.rgb[x, y]["bg"] = Color.WARNING
        console.rgb[x, y]["fg"] = Color.BLACK


def render_travel_path(console: "tcod.console.Console", engine: "Engine") -> None:
    """While engine.traveling is set, tints the remaining route to
    engine.travel_target (dim blue) and the destination tile itself
    (brighter blue). Reads engine.travel_path -- refreshed once per tick by
    systems.auto_explore.step_travel as it moves the player -- rather than
    recomputing the route itself, so a full BFS doesn't run twice per tick
    (once for movement, once again here for the preview). Only tints bg, so
    entities/hazards drawn afterward still show their own glyph on top
    undisturbed."""
    path = engine.travel_path
    if not path:
        return

    for x, y in path[:-1]:
        if 0 <= x < console.width and 0 <= y < console.height:
            console.rgb[x, y]["bg"] = Color.TRAVEL_PATH_BG

    target_x, target_y = path[-1]
    if 0 <= target_x < console.width and 0 <= target_y < console.height:
        console.rgb[target_x, target_y]["bg"] = Color.TRAVEL_TARGET_BG


def render_look_background(console: "tcod.console.Console", *, y: int, width: int) -> None:
    """Highlighted backdrop behind the two look-mode text rows -- makes them
    read as a distinct block instead of blending into the panel's black."""
    console.draw_rect(x=0, y=y, width=width, height=2, ch=ord(" "), bg=Color.LOOK_BG)


def render_look_line(console: "tcod.console.Console", engine: "Engine", *, x: int, y: int) -> None:
    cx, cy = engine.look_cursor
    console.print(x, y, f"LOOK ({cx},{cy}): {describe_tile(engine, cx, cy)}", fg=Color.LOOK_TEXT, bg=Color.LOOK_BG)


def render_look_flavor_line(console: "tcod.console.Console", engine: "Engine", *, x: int, y: int) -> None:
    cx, cy = engine.look_cursor
    text = tile_flavor_line(engine, cx, cy)
    if text:
        console.print(x, y, text, fg=Color.LOOK_FLAVOR_TEXT, bg=Color.LOOK_BG)


def render_ui(console: "tcod.console.Console", engine: "Engine", *, panel_height: int) -> None:
    map_height = console.height - panel_height
    console.draw_rect(x=0, y=map_height, width=console.width, height=panel_height, ch=ord(" "), bg=Color.BLACK)
    render_sanity_bar(console, engine, x=1, y=map_height, width=30)
    render_hp_bar(console, engine, x=1, y=map_height + 1, width=30)
    render_hunger_bar(console, engine, x=1, y=map_height + 2, width=30)
    render_fuel_bar(console, engine, x=1, y=map_height + 3, width=30)

    log_y = map_height + 4
    log_height = panel_height - 4
    if engine.look_mode:
        render_look_background(console, y=log_y, width=console.width)
        render_look_line(console, engine, x=1, y=log_y)
        log_y += 1
        log_height -= 1
        render_look_flavor_line(console, engine, x=1, y=log_y)
        log_y += 1
        log_height -= 1
    render_message_log(console, engine, x=1, y=log_y, height=log_height)

    console.print(console.width - 15, map_height, "[C] Character", fg=Color.GREY)
    console.print(console.width - 15, map_height + 1, "[X] Look", fg=Color.GREY)
    console.print(console.width - 15, map_height + 2, "[I] Inventory", fg=Color.GREY)
    console.print(console.width - 15, map_height + 3, "[G] Pick up", fg=Color.GREY)
    console.print(console.width - 15, map_height + 4, "[F] Light", fg=Color.GREY)
    console.print(console.width - 15, map_height + 5, "[Home] Explore", fg=Color.GREY)


def render_character_screen(console: "tcod.console.Console", engine: "Engine") -> None:
    """A full-console modal, toggled by ToggleCharacterScreenAction. Replaces
    the map/entity draw entirely for the frame it's open -- renderer.render_all
    branches to this instead of the normal draw when engine.show_character_screen
    is set, so the caller doesn't need to know this is a distinct rendering mode."""
    console.clear(ch=ord(" "), fg=Color.WHITE, bg=Color.BLACK)

    player = engine.player
    width = min(50, console.width - 4)
    # `title=` and a custom `decoration=` are mutually exclusive in tcod, and
    # the bundled TTF lacks Unicode box-drawing glyphs -- so use the ASCII
    # decoration and print the title separately instead.
    console.draw_frame(
        x=2,
        y=1,
        width=width,
        height=console.height - 2,
        clear=True,
        fg=Color.WHITE,
        bg=Color.BLACK,
        decoration="+-+| |+-+",
    )
    console.print(4, 1, f" {player.name} ", fg=Color.WHITE, bg=Color.BLACK)

    lines: list[tuple[str, tuple[int, int, int]]] = []

    if player.experience is not None:
        xp = player.experience
        lines.append((f"Level     {xp.level}", Color.WHITE))
        lines.append((f"XP        {xp.current_xp}/{xp.xp_to_next_level}", Color.GREY))
    else:
        lines.append(("Level     --", Color.GREY))

    lines.append(("", Color.WHITE))

    if player.attributes is not None:
        a = player.attributes
        lines.append((f"Endurance {a.endurance}", Color.GREY))
        lines.append((f"Willpower {a.willpower}", Color.GREY))
        lines.append((f"Dexterity {a.dexterity}  (hit/dodge chance)", Color.GREY))
        lines.append((f"Strength  {a.strength}  (melee damage)", Color.GREY))
        lines.append((f"Luck      {a.luck}", Color.GREY))
    else:
        lines.append(("Stats     --", Color.GREY))

    lines.append(("", Color.WHITE))

    if player.fighter is not None:
        lines.append((f"HP        {int(player.fighter.hp)}/{player.fighter.max_hp}", Color.WHITE))
        lines.append((f"Mitigation {player.fighter.endurance}  (physical damage mitigation)", Color.GREY))
        lines.append((f"Power     {player.fighter.power}  (physical damage dealt)", Color.GREY))
    else:
        lines.append(("HP        --", Color.GREY))

    lines.append(("", Color.WHITE))

    if player.sanity is not None:
        sanity = player.sanity
        lines.append((f"Sanity    {int(sanity.current)}/{int(sanity.max_sanity)}  ({sanity.band.name})", SANITY_BAND_COLOR[sanity.band.name]))
        lines.append((f"Willpower {sanity.willpower:g}  (sanity-drain mitigation)", Color.GREY))
    else:
        lines.append(("Sanity    --", Color.GREY))

    lines.append(("", Color.WHITE))

    if player.perception is not None:
        lines.append((f"Perception {player.perception.acuity}  (view radius bonus)", Color.GREY))
    else:
        lines.append(("Perception --", Color.GREY))

    lines.append(("", Color.WHITE))

    if player.quickness is not None:
        lines.append((f"Quickness {player.quickness.value:g}  (actions per turn)", Color.GREY))
    else:
        lines.append(("Quickness --", Color.GREY))

    lines.append(("", Color.WHITE))

    light = player.light_source
    if light is not None:
        state = "lit" if light.is_lit else "out"
        lines.append((f"Light     {int(light.fuel)}/{int(light.max_fuel)} fuel  ({state}, radius {light.radius})", Color.WARNING))
    else:
        lines.append(("Light     no light source", Color.GREY))

    for i, (text, color) in enumerate(lines):
        console.print(4, 3 + i, text, fg=color)

    console.print(4, console.height - 3, "[C/Tab/Esc] Close", fg=Color.GREY)


def render_inventory_screen(console: "tcod.console.Console", engine: "Engine") -> None:
    """A full-console modal, toggled by ToggleInventoryAction. Number keys
    1-9 select a row to use (see input_handlers.INVENTORY_SLOT_KEYS) --
    the row number printed here is exactly the slot UseItemAction expects."""
    console.clear(ch=ord(" "), fg=Color.WHITE, bg=Color.BLACK)

    player = engine.player
    width = min(50, console.width - 4)
    console.draw_frame(
        x=2,
        y=1,
        width=width,
        height=console.height - 2,
        clear=True,
        fg=Color.WHITE,
        bg=Color.BLACK,
        decoration="+-+| |+-+",
    )
    console.print(4, 1, " Inventory ", fg=Color.WHITE, bg=Color.BLACK)

    held = player.inventory.items if player.inventory is not None else []
    equipped = player.equipment.equipped_items() if player.equipment is not None else []
    combined = held + equipped
    if not combined:
        console.print(4, 3, "(empty)", fg=Color.GREY)
    else:
        for i, item in enumerate(combined):
            suffix = " [worn]" if i >= len(held) else ""
            console.print(4, 3 + i, f"{i + 1}) {item.name}{suffix}", fg=Color.WHITE)

    console.print(4, console.height - 3, "[1-9] Use/Equip  [I/Esc] Close", fg=Color.GREY)


def render_barter_screen(console: "tcod.console.Console", engine: "Engine") -> None:
    """A full-console modal, opened by bumping a community Elder (see
    actions.BumpAction). Number keys 1-9 buy the matching row (see
    input_handlers.INVENTORY_SLOT_KEYS -> actions.BarterAction). Prices are
    this level's, already scaled by LevelDefinition.barter_price_multiplier, so
    the same good reads as more or fewer currency items in different
    communities."""
    console.clear(ch=ord(" "), fg=Color.WHITE, bg=Color.BLACK)

    partner = engine.barter_partner
    barter = partner.barter if partner is not None else None
    width = min(56, console.width - 4)
    console.draw_frame(
        x=2,
        y=1,
        width=width,
        height=console.height - 2,
        clear=True,
        fg=Color.WHITE,
        bg=Color.BLACK,
        decoration="+-+| |+-+",
    )
    title = f" {partner.name} " if partner is not None else " Barter "
    console.print(4, 1, title, fg=Color.WHITE, bg=Color.BLACK)

    if barter is None:
        console.print(4, 3, "(no one to trade with)", fg=Color.GREY)
        console.print(4, console.height - 3, "[Esc] Close", fg=Color.GREY)
        return

    if engine.barter_greeting:
        console.print(4, 3, f'"{engine.barter_greeting}"', fg=Color.GREY)

    held = engine.player.inventory.items if engine.player.inventory is not None else []
    on_hand = sum(1 for item in held if item.name == barter.currency_item_name)
    console.print(4, 5, f"You carry {on_hand} {barter.currency_item_name}.", fg=Color.WHITE)

    multiplier = LEVEL_REGISTRY[engine.current_level_id].barter_price_multiplier
    if not barter.offers:
        console.print(4, 7, "The stock is bare. Nothing left to trade.", fg=Color.GREY)
    else:
        for i, offer in enumerate(barter.offers):
            price = barter.price_for(offer, multiplier=multiplier)
            affordable = on_hand >= price
            # A factory call just to read the good's name is cheap and keeps
            # the display name as the single source of truth (the item itself),
            # rather than duplicating names into the offer table.
            name = offer.result_factory().name
            color = Color.WHITE if affordable else Color.GREY
            marker = "" if affordable else "  (can't afford)"
            console.print(4, 7 + i, f"{i + 1}) {name} -- {price} {barter.currency_item_name}{marker}", fg=color)

    console.print(4, console.height - 3, "[1-9] Trade  [Esc] Close", fg=Color.GREY)
