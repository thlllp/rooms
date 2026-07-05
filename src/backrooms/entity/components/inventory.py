from __future__ import annotations

from typing import TYPE_CHECKING

from backrooms.entity.components.base_component import BaseComponent

if TYPE_CHECKING:
    from backrooms.entity.entity import Entity


class Inventory(BaseComponent):
    """Held items are Entity objects, same as anything on the map -- picking
    one up just moves it from GameMap.entities into this list."""

    def __init__(self, capacity: int = 10) -> None:
        self.capacity = capacity
        self.items: list["Entity"] = []
