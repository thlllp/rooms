from __future__ import annotations

from typing import TYPE_CHECKING

from backrooms.constants import Color
from backrooms.entity.components.base_component import BaseComponent

if TYPE_CHECKING:
    from backrooms.engine import Engine
    from backrooms.entity.entity import Entity


class Inventory(BaseComponent):
    """Held items are Entity objects, same as anything on the map -- picking
    one up just moves it from GameMap.entities into this list."""

    def __init__(self, capacity: int = 10) -> None:
        self.capacity = capacity
        self.items: list["Entity"] = []


def effective_capacity(entity: "Entity") -> int:
    """How many items `entity` can actually hold: its base Inventory.capacity
    plus whatever worn gear adds (a back-slot backpack, see
    EquipmentComponent.capacity_bonus). Computed fresh rather than mutating
    Inventory.capacity on equip/unequip, so it can never drift out of sync with
    what's worn. Lives here (not in actions) so both the pickup/equip paths and
    hazard drops share one definition. Returns 0 for an entity with no
    inventory."""
    if entity.inventory is None:
        return 0
    bonus = entity.equipment.capacity_bonus() if entity.equipment is not None else 0
    return entity.inventory.capacity + bonus


def store_or_drop(
    player: "Entity", item: "Entity", drop_x: int, drop_y: int, engine: "Engine", *, stored_message: str, dropped_message: str
) -> None:
    """Give `item` to the player if the pack has room, else drop it on the
    map at (drop_x, drop_y) -- the shared "a find has to land somewhere"
    resolution behind furniture salvage (actions.SalvageAction), containers
    (actions.OpenContainerAction), and debris piles (actions.SearchDebrisAction),
    so the capacity check and the place-on-floor fallback can't drift between
    them. Logs stored_message on
    a successful stow, dropped_message when the pack was full. Callers pass
    the drop tile explicitly since it differs (the debris/furniture's own
    tile), and phrase their own messages since the flavor differs."""
    if player.inventory is not None and len(player.inventory.items) < effective_capacity(player):
        player.inventory.items.append(item)
        engine.message_log.add_message(stored_message, color=Color.WHITE)
    else:
        item.place(drop_x, drop_y)
        engine.game_map.entities.add(item)
        engine.message_log.add_message(dropped_message, color=Color.WHITE)
