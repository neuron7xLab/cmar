# SPDX-License-Identifier: GPL-3.0-or-later
"""A deterministic, synchronous event bus (seed intent — real, untested).

Handlers are invoked in registration order; publishing returns the ordered list of
handler results. No threads, no clocks — fully deterministic, like the rest of the
seed. This is executable mass awaiting corroboration.
"""

from __future__ import annotations

from collections.abc import Callable


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[str, list[Callable[[dict], object]]] = {}
        self._log: list[tuple[str, int]] = []

    def subscribe(self, topic: str, handler: Callable[[dict], object]) -> None:
        if not topic:
            raise ValueError("topic must be non-empty")
        self._subs.setdefault(topic, []).append(handler)

    def unsubscribe(self, topic: str, handler: Callable[[dict], object]) -> bool:
        handlers = self._subs.get(topic, [])
        if handler in handlers:
            handlers.remove(handler)
            return True
        return False

    def topics(self) -> list[str]:
        return sorted(self._subs)

    def publish(self, topic: str, event: dict | None = None) -> list[object]:
        event = event or {}
        results = [h(event) for h in self._subs.get(topic, [])]
        self._log.append((topic, len(results)))
        return results

    def history(self) -> list[tuple[str, int]]:
        return list(self._log)


def fanout(topic: str, handlers: list[Callable[[dict], object]], event: dict) -> list[object]:
    bus = EventBus()
    for h in handlers:
        bus.subscribe(topic, h)
    return bus.publish(topic, event)
