"""
WorkerPool
----------
Holds N Worker instances.

WorkerManager delegates to WorkerPool.
Increasing pool_size from 1 to 4 requires no other changes.
"""

from typing import List

from vaultcore.execution.worker.worker import Worker
from vaultcore.execution.task.task_manager import TaskManager
from vaultcore.execution.events.event_dispatcher import EventDispatcher


class WorkerPool:
    """Fixed-size pool of Worker threads."""

    def __init__(
        self,
        task_manager: TaskManager,
        dispatcher:   EventDispatcher,
        size:         int = 1,
    ) -> None:
        self._workers: List[Worker] = [
            Worker(
                worker_id    = i,
                task_manager = task_manager,
                dispatcher   = dispatcher,
            )
            for i in range(size)
        ]

    def start_all(self) -> None:
        for worker in self._workers:
            worker.start()

    def stop_all(self) -> None:
        for worker in self._workers:
            worker.stop()
