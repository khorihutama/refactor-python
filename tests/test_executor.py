from scheduler.executor import TaskExecutor
from scheduler.models import Task


class RecordingAction:
    def __init__(self) -> None:
        self.seen: list[Task] = []

    def execute(self, task: Task) -> None:
        self.seen.append(task)


def test_dispatches_to_registered_action() -> None:
    action = RecordingAction()
    task = Task("alice", "12:00", "archive", "/data/x", {"level": 9})
    TaskExecutor({"archive": action}).execute(task)
    assert action.seen == [task]
