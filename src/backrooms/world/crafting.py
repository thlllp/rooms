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
    # Entity.name of a held tool (see entity.components.tool.ToolComponent)
    # that must ALSO be present, unlike `ingredients` -- it's required but
    # never consumed as a raw material. Instead CraftAction ticks one charge
    # off its ToolComponent per successful craft (see the Sewing Kit),
    # discarding it once depleted. None (every current recipe) means no
    # tool is required at all.
    required_tool: str | None = None

    def __post_init__(self) -> None:
        # Two invariants CraftAction relies on but can't recover from at
        # runtime, so reject a bad recipe loudly at registration instead:
        # (1) A recipe with no ingredients would match every craft attempt
        #     (the "all ingredients held" check is vacuously true) and append
        #     its result each press without removing anything -- an infinite
        #     item printer that also overflows inventory capacity.
        # (2) A required_tool that also names an ingredient makes CraftAction
        #     remove the tool item as that ingredient, then try to spend a
        #     charge on the already-removed item -- a ValueError mid-craft.
        if not self.ingredients:
            raise ValueError(f"CraftingRecipe {self.name!r} must have at least one ingredient")
        if self.required_tool is not None and self.required_tool in self.ingredients:
            raise ValueError(
                f"CraftingRecipe {self.name!r} required_tool {self.required_tool!r} cannot also be an ingredient"
            )


CRAFTING_RECIPES: list[CraftingRecipe] = []


def register_recipe(recipe: CraftingRecipe) -> CraftingRecipe:
    CRAFTING_RECIPES.append(recipe)
    return recipe
