import asyncio
import datetime
import logging
from collections.abc import Awaitable, Callable, Sequence
from typing import Final

from scheduler.executor import TaskExecutor
from scheduler.models import TIME_FORMAT, Task
from scheduler.users import UserRegistry

logger = logging.getLogger(__name__)

POLL_SECONDS: Final = 30


Clock = Callable[[], datetime.datetime]
Sleep = Callable[[float], Awaitable[None]]


class Scheduler:
    def __init__(
        self,
        tasks: Sequence[Task],
        users: UserRegistry,
        executor: TaskExecutor,
        clock: Clock,
    ) -> None:
        self._tasks = tasks
        self._users = users
        self._executor = executor
        self._clock = clock
        # Task index -> last date it was handled (run or skipped).
        # shortcut: kept in memory only, so a restart in the same minute runs again; persist it if that matters.
        self._last_handled: dict[int, datetime.date] = {}

    async def run_due(self) -> None:
        """Run every task due this minute concurrently; a failing task is logged."""
        due = self._take_due()
        results = await asyncio.gather(
            *(self._run_one(task) for task in due), return_exceptions=True
        )
        for task, result in zip(due, results, strict=True):
            if isinstance(result, Exception):
                logger.error(
                    "Task %s on %s for %s failed.",
                    task.action,
                    task.target,
                    task.user,
                    exc_info=result,
                )

    async def run_forever(self, sleep: Sleep = asyncio.sleep) -> None:
        """Check for due tasks every POLL_SECONDS until interrupted (Ctrl+C)."""
        logger.info("Scheduler started; checking every %s seconds.", POLL_SECONDS)
        while True:
            await self.run_due()
            await sleep(POLL_SECONDS)

    def _take_due(self) -> list[Task]:
        now = self._clock()
        current_time, today = now.strftime(TIME_FORMAT), now.date()
        due = []
        for index, task in enumerate(self._tasks):
            if task.time != current_time or self._last_handled.get(index) == today:
                continue
            self._last_handled[index] = today
            due.append(task)
        return due

    async def _run_one(self, task: Task) -> None:
        if task.user not in self._users:
            logger.error("Unknown user %s; skipping task.", task.user)
            return
        if not self._executor.supports(task.action):
            logger.error("Unknown action %s; skipping task.", task.action)
            return
        if not self._users.can_execute(task.user):
            logger.warning("%s has exceeded quota.", task.user)
            return
        # Reserve quota before the first await, so concurrent tasks of one user
        # cannot all pass the check. A failed action still uses its quota.
        self._users.record_execution(task.user)
        await self._executor.execute(task)
