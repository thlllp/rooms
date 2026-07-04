from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from backrooms.entity.components.base_component import BaseComponent


@dataclass(frozen=True)
class SanityBand:
    name: str
    floor: int  # inclusive lower bound
    perception_distortion: bool = False
    hallucinations: bool = False
    forced_event_eligible: bool = False


# Ordered highest floor first -- SanityComponent.band walks this top-down.
SANITY_BANDS: tuple[SanityBand, ...] = (
    SanityBand("normal", floor=70),
    SanityBand("mild", floor=40, perception_distortion=True),
    SanityBand("severe", floor=15, perception_distortion=True, hallucinations=True),
    SanityBand("critical", floor=0, perception_distortion=True, hallucinations=True, forced_event_eligible=True),
)


class SanityComponent(BaseComponent):
    def __init__(self, max_sanity: int = 100, *, history_window: int = 12, repeat_ratio_threshold: float = 0.4) -> None:
        self.max_sanity = float(max_sanity)
        self.current = float(max_sanity)
        self._repeat_ratio_threshold = repeat_ratio_threshold
        # Rolling window of recently-visited tiles, used to detect "pacing in
        # a loop" (the Backrooms "the halls repeat" cue) -- lives here rather
        # than on Engine since it's sanity-system-private bookkeeping.
        self.position_history: deque[tuple[int, int]] = deque(maxlen=history_window)

    @property
    def band(self) -> SanityBand:
        for band in SANITY_BANDS:
            if self.current >= band.floor:
                return band
        return SANITY_BANDS[-1]

    def drain(self, amount: float) -> None:
        self.current = max(0.0, self.current - amount)

    def restore(self, amount: float) -> None:
        self.current = min(self.max_sanity, self.current + amount)

    def record_position(self, x: int, y: int) -> None:
        self.position_history.append((x, y))

    def is_pacing_in_loop(self) -> bool:
        history = self.position_history
        if len(history) < history.maxlen:
            return False
        unique_ratio = len(set(history)) / len(history)
        return unique_ratio < self._repeat_ratio_threshold
