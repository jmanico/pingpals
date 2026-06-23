"""Bounded retry + per-channel circuit breaker + bounded DLQ (issue 052, NFR-1.5/1.6).

Each reminder has a maximum attempt count; retries use exponential backoff with jitter. A
per-channel circuit breaker suspends sends after a consecutive-failure threshold and fails closed
(no further attempts until reset) rather than retrying continuously. Exhausted messages move to a
bounded dead-letter store; DLQ saturation raises an alert and never silently drops a reminder.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 5
    base_delay: float = 1.0
    max_delay: float = 60.0

    def backoff(self, attempt: int, jitter: Callable[[], float] = random.random) -> float:
        """Exponential backoff with jitter, bounded by ``max_delay`` (attempt is 0-based)."""
        raw = min(self.max_delay, self.base_delay * (2 ** attempt))
        return raw * (0.5 + 0.5 * jitter())  # 50–100% of the slot — never zero, never unbounded

    def is_exhausted(self, attempt: int) -> bool:
        return attempt >= self.max_attempts


@dataclass
class _BreakerState:
    consecutive_failures: int = 0
    open: bool = False


class CircuitBreaker:
    """Per-channel breaker — trips after ``threshold`` consecutive failures, fails closed."""

    def __init__(self, threshold: int = 5) -> None:
        self._threshold = threshold
        self._channels: dict[str, _BreakerState] = {}

    def _state(self, channel: str) -> _BreakerState:
        return self._channels.setdefault(channel, _BreakerState())

    def allow(self, channel: str) -> bool:
        return not self._state(channel).open  # AC-03: open breaker blocks attempts

    def record_success(self, channel: str) -> None:
        self._channels[channel] = _BreakerState()

    def record_failure(self, channel: str) -> None:
        st = self._state(channel)
        st.consecutive_failures += 1
        if st.consecutive_failures >= self._threshold:
            st.open = True  # trip (AC-02)

    def reset(self, channel: str) -> None:
        self._channels[channel] = _BreakerState()


class DeadLetterFull(Exception):
    """The bounded DLQ is full — an operational alert is raised; the reminder is not dropped."""


@dataclass
class DeadLetterQueue:
    max_size: int = 1000
    on_alert: Callable[[str], None] = lambda _msg: None
    _items: list[dict] = field(default_factory=list)

    def add(self, item: dict) -> None:
        if len(self._items) >= self.max_size:
            self.on_alert("dead-letter queue saturated")  # AC-04: alert, never silent drop
            raise DeadLetterFull("DLQ full")
        self._items.append(item)

    def __len__(self) -> int:
        return len(self._items)
