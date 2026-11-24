import pytest

from scheduler.models import Task

BASE = {"user": "alice", "time": "12:00", "action": "sync", "target": "/data/x"}


def test_from_dict_reads_params() -> None:
    task = Task.from_dict({**BASE, "params": {"retries": 2}})
    assert task == Task("alice", "12:00", "sync", "/data/x", {"retries": 2})


def test_from_dict_params_default_empty() -> None:
    assert Task.from_dict(BASE).params == {}


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"target": None}, "'target' must be a non-empty string"),
        ({"user": 7}, "'user' must be a non-empty string"),
        ({"time": "9:00"}, "must be HH:MM"),
        ({"time": "25:00"}, "must be HH:MM"),
        ({"params": [1, 2]}, "'params' must be an object"),
    ],
)
def test_from_dict_rejects_bad_fields(change: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        Task.from_dict({**BASE, **change})
