from dataclasses import dataclass, field
from typing import Any


@dataclass
class Task:
    user: str
    time: str
    action: str
    target: str
    params: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        return cls(
            user=data["user"],
            time=data["time"],
            action=data["action"],
            target=data["target"],
            params=dict(data.get("params", {})),
        )
