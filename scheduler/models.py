import datetime
from dataclasses import dataclass, field
from typing import Any, Final

TIME_FORMAT: Final = "%H:%M"


def _require_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"task field {key!r} must be a non-empty string")
    return value


def _check_time(value: str) -> None:
    try:
        valid = datetime.datetime.strptime(value, TIME_FORMAT).strftime(TIME_FORMAT)
    except ValueError:
        valid = None
    if valid != value:
        raise ValueError(f"task time {value!r} must be HH:MM, e.g. '09:00'")


@dataclass
class Task:
    user: str
    time: str
    action: str
    target: str
    params: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        user, time, action, target = (
            _require_str(data, key) for key in ("user", "time", "action", "target")
        )
        _check_time(time)
        params = data.get("params", {})
        if not isinstance(params, dict):
            raise ValueError("task field 'params' must be an object")
        return cls(user, time, action, target, dict(params))
