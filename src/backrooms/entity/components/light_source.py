from __future__ import annotations

from typing import TYPE_CHECKING

from backrooms.constants import Color
from backrooms.entity.components.base_component import BaseComponent

if TYPE_CHECKING:
    from backrooms.engine import Engine
    from backrooms.entity.entity import Entity


class LightSourceComponent(BaseComponent):
    def __init__(self, max_fuel: float = 100.0, radius: int = 4, burn_rate: float = 1.0, *, is_lit: bool = True) -> None:
        self.max_fuel = max_fuel
        self.fuel = max_fuel
        self.radius = radius
        self.burn_rate = burn_rate
        self.is_lit = is_lit


def tick_light_fuel(entity: "Entity", engine: "Engine") -> None:
    light = entity.light_source
    if light is None or not light.is_lit or light.fuel <= 0:
        return
    light.fuel = max(0.0, light.fuel - light.burn_rate)
    if light.fuel == 0:
        light.is_lit = False
        engine.message_log.add_message("Your light sputters out.", color=Color.WARNING)
