from pathlib import Path

SCREEN_WIDTH = 90
SCREEN_HEIGHT = 55

MAP_WIDTH = 90
MAP_HEIGHT = 45

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

    PLAYER = (230, 230, 200)

    MESSAGE_LOG = (200, 200, 200)
    NOCLIP_FLAVOR = (170, 90, 200)
    WARNING = (230, 180, 60)
    HAZARD = (200, 60, 60)

    SANITY_BAR_FULL = (90, 160, 90)
    SANITY_BAR_LOW = (160, 60, 60)
    SANITY_BAR_EMPTY = (40, 40, 40)
