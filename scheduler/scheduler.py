import datetime
import logging
import time
from collections.abc import Callable, Sequence
from typing import Final

from scheduler.executor import TaskExecutor
from scheduler.models import TIME_FORMAT, Task
from scheduler.users import UserRegistry

logger = logging.getLogger(__name__)

POLL_SECONDS: Final = 30


Clock = Callable[[], datetime.datetime]


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

    def run_due(self) -> None:
        now = self._clock()
        current_time, today = now.strftime(TIME_FORMAT), now.date()
        for index, task in enumerate(self._tasks):
            if task.time != current_time or self._last_handled.get(index) == today:
                continue
            self._last_handled[index] = today
            self._run_one(task)

    def run_forever(self, sleep: Callable[[float], None] = time.sleep) -> None:
        """Check for due tasks every POLL_SECONDS until interrupted (Ctrl+C)."""
        logger.info("Scheduler started; checking every %s seconds.", POLL_SECONDS)
        while True:
            self.run_due()
            sleep(POLL_SECONDS)

    def _run_one(self, task: Task) -> None:
        if task.user not in self._users:
            logger.error("Unknown user %s; skipping task.", task.user)
            return
        if not self._executor.supports(task.action):
            logger.error("Unknown action %s; skipping task.", task.action)
            return
        if not self._users.can_execute(task.user):
            logger.warning("%s has exceeded quota.", task.user)
            return
        self._executor.execute(task)
        self._users.record_execution(task.user)
