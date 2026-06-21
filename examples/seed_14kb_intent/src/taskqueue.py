# SPDX-License-Identifier: GPL-3.0-or-later
"""A deterministic in-memory priority task queue (seed intent — real, untested).

Priority is (priority_value, insertion_index): lower priority_value runs first;
ties break by insertion order, so ordering is fully deterministic. This module is
genuine executable mass; what it lacks is corroborating evidence (tests/CI), which
is exactly what CMAR's void graph reports and autofill materializes.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(order=False)
class Task:
    name: str
    priority: int = 100
    payload: dict = field(default_factory=dict)


class TaskQueue:
    """Stable priority queue: pop() returns the lowest (priority, insertion) task."""

    def __init__(self) -> None:
        self._items: list[tuple[int, int, Task]] = []
        self._counter = 0

    def __len__(self) -> int:
        return len(self._items)

    def push(self, task: Task) -> None:
        if not isinstance(task, Task):
            raise TypeError("push expects a Task")
        self._items.append((task.priority, self._counter, task))
        self._counter += 1
        # keep deterministic order without depending on heap tie-behaviour
        self._items.sort(key=lambda t: (t[0], t[1]))

    def push_many(self, tasks: list[Task]) -> None:
        for t in tasks:
            self.push(t)

    def peek(self) -> Task | None:
        return self._items[0][2] if self._items else None

    def pop(self) -> Task:
        if not self._items:
            raise IndexError("pop from empty queue")
        return self._items.pop(0)[2]

    def drain(self) -> list[Task]:
        out = []
        while self._items:
            out.append(self.pop())
        return out

    def names(self) -> list[str]:
        return [t[2].name for t in self._items]
