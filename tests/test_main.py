"""Characterization tests: pin the current behavior of main.run() before refactoring."""

import copy
import dataclasses
import datetime
from types import SimpleNamespace

import pytest

import main

ORIGINAL_USERS = copy.deepcopy(main.users)


@pytest.fixture(autouse=True)
def fresh_users(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "users", copy.deepcopy(ORIGINAL_USERS))


def set_clock(monkeypatch: pytest.MonkeyPatch, hour: int, minute: int) -> None:
    fixed = datetime.datetime(2026, 1, 1, hour, minute)
    fake = SimpleNamespace(datetime=SimpleNamespace(now=lambda: fixed))
    monkeypatch.setattr(main, "datetime", fake)


def test_runs_all_due_tasks(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    set_clock(monkeypatch, 12, 0)
    main.run()
    assert capsys.readouterr().out.splitlines() == [
        "Executing sync on /data/x for alice",
        "Executing backup on /srv/y for bob",
        "Executing delete on /tmp/z for alice",
    ]
    assert main.users.get("alice").executed == 2
    assert main.users.get("bob").executed == 1


def test_nothing_runs_outside_scheduled_minute(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    set_clock(monkeypatch, 12, 1)
    main.run()
    assert capsys.readouterr().out == ""
    assert main.users.get("alice").executed == 0
    assert main.users.get("bob").executed == 0


def test_quota_exceeded_skips_task(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    main.users.get("alice").quota = 1
    set_clock(monkeypatch, 12, 0)
    main.run()
    assert capsys.readouterr().out.splitlines() == [
        "Executing sync on /data/x for alice",
        "Executing backup on /srv/y for bob",
        "alice has exceeded quota.",
    ]
    assert main.users.get("alice").executed == 1


def test_second_run_same_minute_runs_again(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Current behavior; step 7 (once per day) changes it.
    set_clock(monkeypatch, 12, 0)
    main.run()
    capsys.readouterr()
    main.run()
    assert capsys.readouterr().out.splitlines() == [
        "Executing sync on /data/x for alice",
        "Executing backup on /srv/y for bob",
        "alice has exceeded quota.",
    ]
    assert main.users.get("alice").executed == 3
    assert main.users.get("bob").executed == 2


def test_unknown_user_crashes(monkeypatch: pytest.MonkeyPatch) -> None:
    # Current behavior; step 6 (log and skip) changes it.
    monkeypatch.setattr(
        main, "tasks", [dataclasses.replace(main.tasks[0], user="carol")]
    )
    set_clock(monkeypatch, 12, 0)
    with pytest.raises(KeyError):
        main.run()


def test_unknown_action_still_runs(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Current behavior; step 6 (log and skip) changes it.
    monkeypatch.setattr(
        main, "tasks", [dataclasses.replace(main.tasks[0], action="rename")]
    )
    set_clock(monkeypatch, 12, 0)
    main.run()
    assert capsys.readouterr().out == "Executing rename on /data/x for alice\n"
    assert main.users.get("alice").executed == 1
