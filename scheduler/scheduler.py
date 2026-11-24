import datetime
from collections.abc import Callable, Sequence
from typing import Final

from scheduler.executor import TaskExecutor
from scheduler.models import Task
from scheduler.users import UserRegistry

TIME_FORMAT: Final = "%H:%M"

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

    def run_due(self) -> None:
        now = self._clock().strftime(TIME_FORMAT)
        for task in self._tasks:
            if task.time != now:
                continue
            if not self._users.can_execute(task.user):
                print(f"{task.user} has exceeded quota.")
                continue
            self._executor.execute(task)
            self._users.record_execution(task.user)
