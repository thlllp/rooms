from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backrooms.entity.entity import Entity


class BaseComponent:
    """Marker base: every component gets an `entity` back-reference, set by
    Entity.__init__ at construction time rather than passed in explicitly."""

    entity: "Entity"
