# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import subprocess
from types import SimpleNamespace

import pytest

from test.end_to_end import conftest


def make_session(use_installed_worker):
    return SimpleNamespace(
        config=SimpleNamespace(
            getoption=lambda option: {
                "--no-prerun-checks": False,
                "--use-installed-worker": use_installed_worker,
            }[option]
        )
    )


@pytest.mark.parametrize("action", ["start", "stop", "restart"])
def test_manage_installed_worker_service(monkeypatch, action):
    calls = []

    def record_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(conftest.sys, "platform", "win32")
    monkeypatch.setattr(conftest.subprocess, "run", record_run)

    conftest.manage_installed_worker_service(action)

    command, kwargs = calls[0]
    assert command[:4] == [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
    ]
    assert f"{action.capitalize()}-Service -Name 'DeadlineWorker'" in command[4]
    assert kwargs == {"capture_output": True, "text": True}


def test_manage_installed_worker_service_requires_windows(monkeypatch):
    monkeypatch.setattr(conftest.sys, "platform", "linux")

    with pytest.raises(RuntimeError, match="only supported on Windows"):
        conftest.manage_installed_worker_service("restart")


def test_manage_installed_worker_service_reports_failure(monkeypatch):
    monkeypatch.setattr(conftest.sys, "platform", "win32")
    monkeypatch.setattr(
        conftest.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 1, "", "access denied"),
    )

    with pytest.raises(RuntimeError, match="access denied"):
        conftest.manage_installed_worker_service("restart")


def test_prerun_allows_installed_worker(monkeypatch):
    monkeypatch.setattr(
        conftest,
        "_find_leftover_processes",
        lambda: [{"category": "deadline-worker-agent"}],
    )

    conftest.pytest_sessionstart(make_session(use_installed_worker=True))


def test_prerun_rejects_worker_by_default(monkeypatch):
    exits = []
    monkeypatch.setattr(
        conftest,
        "_find_leftover_processes",
        lambda: [
            {
                "category": "deadline-worker-agent",
                "pid": 123,
                "name": "deadline-worker-agent.exe",
                "cmdline_short": "deadline-worker-agent",
            }
        ],
    )
    monkeypatch.setattr(
        conftest.pytest,
        "exit",
        lambda message, returncode: exits.append((message, returncode)),
    )

    conftest.pytest_sessionstart(make_session(use_installed_worker=False))

    assert len(exits) == 1
    assert exits[0][1] == 3
