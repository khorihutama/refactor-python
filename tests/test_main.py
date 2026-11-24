"""Characterization tests for main.run(); behavior changes update them in the same commit."""

import copy
import dataclasses
import datetime
import logging
from types import SimpleNamespace

import pytest

import main

ORIGINAL_USERS = copy.deepcopy(main.users)


@pytest.fixture(autouse=True)
def fresh_users(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "users", copy.deepcopy(ORIGINAL_USERS))


@pytest.fixture(autouse=True)
def capture_info_logs(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)


def set_clock(monkeypatch: pytest.MonkeyPatch, hour: int, minute: int) -> None:
    fixed = datetime.datetime(2026, 1, 1, hour, minute)
    fake = SimpleNamespace(datetime=SimpleNamespace(now=lambda: fixed))
    monkeypatch.setattr(main, "datetime", fake)


def test_runs_all_due_tasks(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    set_clock(monkeypatch, 12, 0)
    main.run()
    assert caplog.messages == [
        "Executing sync on /data/x for alice",
        "Executing backup on /srv/y for bob",
        "Executing delete on /tmp/z for alice",
    ]
    assert main.users.get("alice").executed == 2
    assert main.users.get("bob").executed == 1


def test_nothing_runs_outside_scheduled_minute(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    set_clock(monkeypatch, 12, 1)
    main.run()
    assert caplog.messages == []
    assert main.users.get("alice").executed == 0
    assert main.users.get("bob").executed == 0


def test_quota_exceeded_skips_task(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    main.users.get("alice").quota = 1
    set_clock(monkeypatch, 12, 0)
    main.run()
    assert caplog.messages == [
        "Executing sync on /data/x for alice",
        "Executing backup on /srv/y for bob",
        "alice has exceeded quota.",
    ]
    assert caplog.records[-1].levelno == logging.WARNING
    assert main.users.get("alice").executed == 1


def test_second_run_same_minute_runs_again(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # Current behavior; step 7 (once per day) changes it.
    set_clock(monkeypatch, 12, 0)
    main.run()
    caplog.clear()
    main.run()
    assert caplog.messages == [
        "Executing sync on /data/x for alice",
        "Executing backup on /srv/y for bob",
        "alice has exceeded quota.",
    ]
    assert main.users.get("alice").executed == 3
    assert main.users.get("bob").executed == 2


def test_unknown_user_logged_and_skipped(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    bad = dataclasses.replace(main.tasks[0], user="carol")
    monkeypatch.setattr(main, "tasks", [bad, main.tasks[1]])
    set_clock(monkeypatch, 12, 0)
    main.run()
    assert caplog.messages == [
        "Unknown user carol; skipping task.",
        "Executing backup on /srv/y for bob",
    ]
    assert caplog.records[0].levelno == logging.ERROR
    assert main.users.get("bob").executed == 1


def test_unknown_action_logged_and_skipped(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    bad = dataclasses.replace(main.tasks[0], action="rename")
    monkeypatch.setattr(main, "tasks", [bad, main.tasks[1]])
    set_clock(monkeypatch, 12, 0)
    main.run()
    assert caplog.messages == [
        "Unknown action rename; skipping task.",
        "Executing backup on /srv/y for bob",
    ]
    assert caplog.records[0].levelno == logging.ERROR
    assert main.users.get("alice").executed == 0
