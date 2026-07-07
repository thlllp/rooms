from pathlib import Path

SCREEN_WIDTH = 120
SCREEN_HEIGHT = 70

MAP_WIDTH = 120
MAP_HEIGHT = 60

UI_PANEL_HEIGHT = SCREEN_HEIGHT - MAP_HEIGHT

TILE_WIDTH = 16
TILE_HEIGHT = 16

TILESET_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "tilesets" / "VeraMono.ttf"

DEFAULT_FOV_RADIUS = 6

# When the player carries no lit light source, FOV still extends this far
# (matches "unsettling dim awareness" rather than true blindness).
UNLIT_FOV_RADIUS = 3

WINDOW_TITLE = "Backrooms"


class Color:
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GREY = (120, 120, 120)
    DARK_GREY = (60, 60, 60)

    WALL_DARK = (30, 30, 24)
    WALL_LIT = (95, 90, 60)
    FLOOR_DARK = (18, 18, 14)
    FLOOR_LIT = (140, 130, 90)
    COLUMN = (120, 113, 82)
    STAIRS = (230, 230, 90)
    DOOR = (170, 110, 60)
    # Bright orange-amber, deliberately far from both floor palettes'
    # muted tan/grey tones (FLOOR_LIT/GARAGE_FLOOR_LIT) so it actually
    # stands out rather than nearly matching the tile it sits on.
    DEBRIS = (230, 140, 40)

    # Level 2's "giant car garage" look -- neutral grey/concrete instead of
    # the office levels' warm wallpaper/carpet tones.
    GARAGE_WALL_DARK = (28, 28, 28)
    GARAGE_WALL_LIT = (100, 100, 102)
    GARAGE_FLOOR_DARK = (20, 20, 20)
    GARAGE_FLOOR_LIT = (128, 128, 130)

    # A settlement's door (leads to a small safe sublevel) and its floor (a
    # warm, lived-in tone, distinct from the garage's grey concrete -- see
    # tile_types.SETTLEMENT_DOOR/SETTLEMENT_FLOOR), plus the sign that marks
    # one out on the map before you reach it.
    SETTLEMENT_DOOR = (90, 200, 140)
    SETTLEMENT_FLOOR_DARK = (26, 22, 14)
    SETTLEMENT_FLOOR_LIT = (150, 120, 70)
    SIGN = (210, 190, 140)

    # A small inn room within a settlement -- warmer/brighter than the
    # settlement's own floor so it reads as a distinct, cozier spot (see
    # tile_types.INN_FLOOR).
    INN_FLOOR_DARK = (30, 20, 12)
    INN_FLOOR_LIT = (180, 130, 70)

    # Level 3's "pipeworks" look -- brown tile flooring, walls a muted
    # grey/brown amalgamation (neither the office levels' wallpaper nor the
    # garage's flat concrete grey).
    PIPEWORKS_WALL_DARK = (28, 24, 20)
    PIPEWORKS_WALL_LIT = (95, 82, 68)
    PIPEWORKS_FLOOR_DARK = (32, 20, 12)
    PIPEWORKS_FLOOR_LIT = (140, 95, 55)

    PLAYER = (230, 230, 200)

    MESSAGE_LOG = (200, 200, 200)
    NOCLIP_FLAVOR = (170, 90, 200)
    WARNING = (230, 180, 60)
    HAZARD = (200, 60, 60)
    SPORE_PINK = (219, 84, 130)
    SPORE_CORE = (255, 20, 147)  # brighter/more saturated than SPORE_PINK -- marks the source tile

    SANITY_BAR_FULL = (90, 160, 90)
    SANITY_BAR_LOW = (160, 60, 60)
    SANITY_BAR_EMPTY = (40, 40, 40)

    HP_BAR_FULL = (150, 40, 40)
    HUNGER_BAR_FULL = (170, 120, 50)
    FUEL_BAR_FULL = (210, 140, 40)

    # Look mode: a warm-tinted backdrop behind the two look-mode text rows so
    # they read as a distinct highlighted block instead of blending into the
    # panel's plain black, plus near-white/high-contrast text on top of it
    # (the panel's usual WARNING/GREY tones are too dim against pure black).
    LOOK_BG = (55, 45, 15)
    LOOK_TEXT = (255, 235, 150)
    LOOK_FLAVOR_TEXT = (235, 230, 215)

    # Click-to-travel preview (see rendering/ui.render_travel_path): the
    # clicked destination tile gets the brighter of the two, the route
    # leading to it a dimmer shade of the same blue so the two read as one
    # highlight rather than two unrelated colors.
    TRAVEL_TARGET_BG = (70, 130, 190)
    TRAVEL_PATH_BG = (30, 55, 80)
