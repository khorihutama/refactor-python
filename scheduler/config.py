import json
from pathlib import Path
from typing import Any

from scheduler.models import Task
from scheduler.users import User, UserRegistry


def _load_user(name: str, spec: Any) -> User:
    quota = spec.get("quota") if isinstance(spec, dict) else None
    if not isinstance(quota, int) or isinstance(quota, bool) or quota < 0:
        raise ValueError(f"user {name!r} needs a non-negative integer 'quota'")
    return User(name, quota)


def load_config(path: Path) -> tuple[UserRegistry, list[Task]]:
    """Read users and tasks from a JSON file; raises OSError or ValueError."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("config must be a JSON object")
    users, tasks = data.get("users"), data.get("tasks")
    if not isinstance(users, dict) or not isinstance(tasks, list):
        raise ValueError("config needs a 'users' object and a 'tasks' list")
    if not all(isinstance(task, dict) for task in tasks):
        raise ValueError("every task must be a JSON object")
    registry = UserRegistry(_load_user(name, spec) for name, spec in users.items())
    return registry, [Task.from_dict(task) for task in tasks]
