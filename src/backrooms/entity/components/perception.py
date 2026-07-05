from __future__ import annotations

from backrooms.entity.components.base_component import BaseComponent


class PerceptionComponent(BaseComponent):
    """A single stat, `acuity`, currently applied as a flat bonus to FOV
    radius (see Engine.update_fov). Kept as its own component -- not folded
    into Fighter or SanityComponent -- because it's neither purely physical
    nor purely mental, and it's the natural place to hang future perception-
    gated checks (spotting hidden hazards, resisting stealthed entities,
    reduced flicker/hallucination confusion, ...) without overloading an
    existing component's meaning."""

    def __init__(self, acuity: int = 0) -> None:
        self.acuity = acuity
