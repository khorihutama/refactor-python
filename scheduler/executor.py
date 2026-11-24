import logging
from collections.abc import Mapping
from typing import Protocol

from scheduler.models import Task

logger = logging.getLogger(__name__)


class ActionStrategy(Protocol):
    def execute(self, task: Task) -> None: ...


def simulate(task: Task) -> None:
    logger.info("Executing %s on %s for %s", task.action, task.target, task.user)


# Actions are simulated only; a real implementation replaces the body of execute().
class SyncAction:
    def execute(self, task: Task) -> None:
        simulate(task)


class BackupAction:
    def execute(self, task: Task) -> None:
        simulate(task)


class DeleteAction:
    def execute(self, task: Task) -> None:
        simulate(task)


def default_actions() -> dict[str, ActionStrategy]:
    return {"sync": SyncAction(), "backup": BackupAction(), "delete": DeleteAction()}


class TaskExecutor:
    def __init__(self, actions: Mapping[str, ActionStrategy]) -> None:
        self._actions = actions

    def supports(self, action: str) -> bool:
        return action in self._actions

    def execute(self, task: Task) -> None:
        self._actions[task.action].execute(task)
