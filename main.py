import datetime
from typing import Final

from scheduler.models import Task
from scheduler.users import User, UserRegistry

TIME_FORMAT: Final = "%H:%M"

users = UserRegistry([User("alice", quota=3), User("bob", quota=5)])

tasks = [
    Task.from_dict(data)
    for data in [
        {"user": "alice", "time": "12:00", "action": "sync", "target": "/data/x"},
        {"user": "bob", "time": "12:00", "action": "backup", "target": "/srv/y"},
        {"user": "alice", "time": "12:00", "action": "delete", "target": "/tmp/z"},
    ]
]


def run() -> None:
    now = datetime.datetime.now().strftime(TIME_FORMAT)
    for task in tasks:
        if task.time != now:
            continue
        if not users.can_execute(task.user):
            print(f"{task.user} has exceeded quota.")
            continue
        print(f"Executing {task.action} on {task.target} for {task.user}")
        users.record_execution(task.user)
