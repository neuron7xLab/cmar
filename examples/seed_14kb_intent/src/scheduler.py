# SPDX-License-Identifier: GPL-3.0-or-later
"""A small deterministic scheduler over the task queue (seed intent — untested).

Runs tasks in priority order, applying a pure handler, accumulating a transcript.
Deterministic by construction: no clocks, no randomness, no I/O.
"""

from __future__ import annotations

from collections.abc import Callable

from .taskqueue import Task, TaskQueue


def default_handler(task: Task) -> str:
    return f"ran:{task.name}:p{task.priority}"


class Scheduler:
    def __init__(self, handler: Callable[[Task], str] | None = None) -> None:
        self.handler = handler or default_handler
        self.transcript: list[str] = []

    def run(self, queue: TaskQueue, limit: int | None = None) -> list[str]:
        n = 0
        while len(queue) and (limit is None or n < limit):
            task = queue.pop()
            self.transcript.append(self.handler(task))
            n += 1
        return list(self.transcript)

    def reset(self) -> None:
        self.transcript.clear()


def schedule(names_with_priority: list[tuple[str, int]]) -> list[str]:
    """Convenience: build a queue from (name, priority) pairs and run it."""
    q = TaskQueue()
    q.push_many([Task(name=n, priority=p) for n, p in names_with_priority])
    return Scheduler().run(q)
