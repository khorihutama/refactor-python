import asyncio
import dataclasses
import datetime
import logging
from collections.abc import Sequence

import pytest

from scheduler.executor import TaskExecutor, default_actions
from scheduler.models import Task
from scheduler.scheduler import POLL_SECONDS, Scheduler
from scheduler.users import User, UserRegistry

TASKS = [
    Task("alice", "12:00", "sync", "/data/x"),
    Task("bob", "12:00", "backup", "/srv/y"),
    Task("alice", "12:00", "delete", "/tmp/z"),
]


class FakeClock:
    def __init__(self, hour: int, minute: int) -> None:
        self.now = datetime.datetime(2026, 1, 1, hour, minute)

    def __call__(self) -> datetime.datetime:
        return self.now


def make(
    clock: FakeClock, tasks: Sequence[Task] = TASKS, alice_quota: int = 3
) -> tuple[Scheduler, UserRegistry]:
    users = UserRegistry([User("alice", alice_quota), User("bob", 5)])
    executor = TaskExecutor(default_actions())
    return Scheduler(tasks, users, executor, clock), users


@pytest.fixture(autouse=True)
def capture_info_logs(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)


def test_runs_all_due_tasks(caplog: pytest.LogCaptureFixture) -> None:
    scheduler, users = make(FakeClock(12, 0))
    asyncio.run(scheduler.run_due())
    assert caplog.messages == [
        "Executing sync on /data/x for alice",
        "Executing backup on /srv/y for bob",
        "Executing delete on /tmp/z for alice",
    ]
    assert users.get("alice").executed == 2
    assert users.get("bob").executed == 1


def test_nothing_runs_outside_scheduled_minute(
    caplog: pytest.LogCaptureFixture,
) -> None:
    scheduler, users = make(FakeClock(12, 1))
    asyncio.run(scheduler.run_due())
    assert caplog.messages == []
    assert users.get("alice").executed == 0


def test_quota_exceeded_skips_task(caplog: pytest.LogCaptureFixture) -> None:
    scheduler, users = make(FakeClock(12, 0), alice_quota=1)
    asyncio.run(scheduler.run_due())
    assert caplog.messages == [
        "Executing sync on /data/x for alice",
        "Executing backup on /srv/y for bob",
        "alice has exceeded quota.",
    ]
    assert caplog.records[-1].levelno == logging.WARNING
    assert users.get("alice").executed == 1


def test_second_run_same_day_does_nothing(caplog: pytest.LogCaptureFixture) -> None:
    scheduler, users = make(FakeClock(12, 0))
    asyncio.run(scheduler.run_due())
    caplog.clear()
    asyncio.run(scheduler.run_due())
    assert caplog.messages == []
    assert users.get("alice").executed == 2
    assert users.get("bob").executed == 1


def test_runs_again_next_day(caplog: pytest.LogCaptureFixture) -> None:
    clock = FakeClock(12, 0)
    scheduler, users = make(clock)
    asyncio.run(scheduler.run_due())
    caplog.clear()
    clock.now += datetime.timedelta(days=1)
    asyncio.run(scheduler.run_due())
    assert caplog.messages == [
        "Executing sync on /data/x for alice",
        "Executing backup on /srv/y for bob",
        "alice has exceeded quota.",
    ]
    assert users.get("alice").executed == 3
    assert users.get("bob").executed == 2


def test_quota_warning_once_per_day(caplog: pytest.LogCaptureFixture) -> None:
    scheduler, _ = make(FakeClock(12, 0), alice_quota=0)
    asyncio.run(scheduler.run_due())
    asyncio.run(scheduler.run_due())
    assert caplog.messages.count("alice has exceeded quota.") == 2  # two alice tasks


def test_unknown_user_logged_and_skipped(caplog: pytest.LogCaptureFixture) -> None:
    bad = dataclasses.replace(TASKS[0], user="carol")
    scheduler, users = make(FakeClock(12, 0), tasks=[bad, TASKS[1]])
    asyncio.run(scheduler.run_due())
    assert caplog.messages == [
        "Unknown user carol; skipping task.",
        "Executing backup on /srv/y for bob",
    ]
    assert caplog.records[0].levelno == logging.ERROR
    assert users.get("bob").executed == 1


def test_unknown_action_logged_and_skipped(caplog: pytest.LogCaptureFixture) -> None:
    bad = dataclasses.replace(TASKS[0], action="rename")
    scheduler, users = make(FakeClock(12, 0), tasks=[bad, TASKS[1]])
    asyncio.run(scheduler.run_due())
    assert caplog.messages == [
        "Unknown action rename; skipping task.",
        "Executing backup on /srv/y for bob",
    ]
    assert caplog.records[0].levelno == logging.ERROR
    assert users.get("alice").executed == 0


def test_run_forever_checks_every_poll_interval(
    caplog: pytest.LogCaptureFixture,
) -> None:
    scheduler, users = make(FakeClock(12, 0))
    sleeps: list[float] = []

    class Stop(Exception):
        pass

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        if len(sleeps) == 2:
            raise Stop

    with pytest.raises(Stop):
        asyncio.run(scheduler.run_forever(sleep=fake_sleep))
    assert sleeps == [POLL_SECONDS, POLL_SECONDS]
    assert users.get("alice").executed == 2  # second check same minute: no rerun


class YieldingAction:
    """Gives control back to the event loop, like real I/O would."""

    def __init__(self) -> None:
        self.ran: list[str] = []

    async def execute(self, task: Task) -> None:
        await asyncio.sleep(0)
        self.ran.append(task.target)


def test_concurrent_tasks_cannot_overspend_quota(
    caplog: pytest.LogCaptureFixture,
) -> None:
    action = YieldingAction()
    users = UserRegistry([User("alice", 1)])
    tasks = [Task("alice", "12:00", "sync", "/a"), Task("alice", "12:00", "sync", "/b")]
    executor = TaskExecutor({"sync": action})
    asyncio.run(Scheduler(tasks, users, executor, FakeClock(12, 0)).run_due())
    assert action.ran == ["/a"]
    assert users.get("alice").executed == 1
    assert "alice has exceeded quota." in caplog.messages


class FailingAction:
    async def execute(self, task: Task) -> None:
        raise RuntimeError("disk full")


def test_failing_task_is_logged_and_others_still_run(
    caplog: pytest.LogCaptureFixture,
) -> None:
    actions = {**default_actions(), "sync": FailingAction()}
    users = UserRegistry([User("alice", 3), User("bob", 5)])
    scheduler = Scheduler(TASKS, users, TaskExecutor(actions), FakeClock(12, 0))
    asyncio.run(scheduler.run_due())
    assert "Task sync on /data/x for alice failed." in caplog.messages
    assert "Executing backup on /srv/y for bob" in caplog.messages
    assert "Executing delete on /tmp/z for alice" in caplog.messages
