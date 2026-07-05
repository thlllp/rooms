"""Crafting recipes: consumes a fixed set of held items (matched by name) and
produces a new one. Minimal -- no crafting station requirement, no
byproducts, just "have these, get that". Mirrors level_registry's
register()/registry pattern.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from backrooms.entity.entity import Entity


@dataclass(frozen=True)
class CraftingRecipe:
    name: str
    ingredients: tuple[str, ...]  # Entity.name values, one of each required
    result_factory: Callable[[], "Entity"]


CRAFTING_RECIPES: list[CraftingRecipe] = []


def register_recipe(recipe: CraftingRecipe) -> CraftingRecipe:
    CRAFTING_RECIPES.append(recipe)
    return recipe
