import datetime

from scheduler.executor import TaskExecutor, default_actions
from scheduler.models import Task
from scheduler.scheduler import Scheduler
from scheduler.users import User, UserRegistry

users = UserRegistry([User("alice", quota=3), User("bob", quota=5)])

tasks = [
    Task.from_dict(data)
    for data in [
        {"user": "alice", "time": "12:00", "action": "sync", "target": "/data/x"},
        {"user": "bob", "time": "12:00", "action": "backup", "target": "/srv/y"},
        {"user": "alice", "time": "12:00", "action": "delete", "target": "/tmp/z"},
    ]
]

executor = TaskExecutor(default_actions())


def run() -> None:
    Scheduler(tasks, users, executor, clock=datetime.datetime.now).run_due()
