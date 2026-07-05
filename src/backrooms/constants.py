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
