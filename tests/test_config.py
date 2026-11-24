import json
import logging
from pathlib import Path
from typing import Any

import pytest

import main
from scheduler.config import load_config
from scheduler.scheduler import Scheduler

VALID: dict[str, Any] = {
    "users": {"alice": {"quota": 3}},
    "tasks": [
        {
            "user": "alice",
            "time": "12:00",
            "action": "sync",
            "target": "/data/x",
            "params": {"retries": 2},
        }
    ],
}


def write(tmp_path: Path, data: Any) -> Path:
    path = tmp_path / "tasks.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_loads_users_and_tasks(tmp_path: Path) -> None:
    users, tasks = load_config(write(tmp_path, VALID))
    assert users.get("alice").quota == 3
    assert tasks[0].params == {"retries": 2}


def test_repo_tasks_json_is_valid() -> None:
    users, tasks = load_config(Path("tasks.json"))
    assert "alice" in users and "bob" in users
    assert [task.action for task in tasks] == ["sync", "backup", "delete"]


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ([], "must be a JSON object"),
        ({"users": {}}, "'tasks' list"),
        ({**VALID, "tasks": ["x"]}, "every task must be a JSON object"),
        ({**VALID, "users": {"alice": {"quota": -1}}}, "non-negative integer"),
        ({**VALID, "users": {"alice": {"quota": True}}}, "non-negative integer"),
        ({**VALID, "users": {"alice": 3}}, "non-negative integer"),
    ],
)
def test_rejects_bad_config(tmp_path: Path, data: Any, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        load_config(write(tmp_path, data))


def test_main_returns_1_on_missing_file(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    assert main.main([str(tmp_path / "missing.json")]) == 1
    assert "Cannot load config" in caplog.text


def test_main_returns_1_on_invalid_json(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    path = tmp_path / "tasks.json"
    path.write_text("{not json", encoding="utf-8")
    assert main.main([str(path)]) == 1


def test_main_stops_cleanly_on_ctrl_c(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    async def interrupted(self: Scheduler) -> None:
        raise KeyboardInterrupt

    caplog.set_level(logging.INFO)
    monkeypatch.setattr(Scheduler, "run_forever", interrupted)
    assert main.main(["tasks.json"]) == 0
    assert "Scheduler stopped." in caplog.text
