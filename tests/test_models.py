import pytest

from scheduler.models import Task

BASE = {"user": "alice", "time": "12:00", "action": "sync", "target": "/data/x"}


def test_from_dict_reads_params() -> None:
    task = Task.from_dict({**BASE, "params": {"retries": 2}})
    assert task == Task("alice", "12:00", "sync", "/data/x", {"retries": 2})


def test_from_dict_params_default_empty() -> None:
    assert Task.from_dict(BASE).params == {}


def test_from_dict_missing_field_raises() -> None:
    with pytest.raises(KeyError):
        Task.from_dict({"user": "alice"})
