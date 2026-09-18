# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Regression tests for MRQ remote-submission eligibility filtering."""

import os
import sys
from types import ModuleType
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pytest


def _job(name: str, enabled: bool, shot_states: tuple[bool, ...]) -> SimpleNamespace:
    return SimpleNamespace(
        job_name=name,
        enabled=enabled,
        shot_info=[SimpleNamespace(enabled=shot_enabled) for shot_enabled in shot_states],
    )


@pytest.fixture
def remote_executor():
    """Import the plugin executor with Unreal's reflected APIs mocked."""
    plugin_py = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "unreal_plugin",
            "Content",
            "Python",
        )
    )

    unreal_mock = MagicMock()
    unreal_mock.uclass.return_value = lambda cls: cls
    unreal_mock.ufunction.return_value = lambda fn: fn
    unreal_mock.MoviePipelinePythonHostExecutor = type(
        "MoviePipelinePythonHostExecutor", (object,), {}
    )
    submitter_module = ModuleType("deadline.unreal_submitter.submitter")
    setattr(submitter_module, "UnrealMrqJobSubmitter", MagicMock())
    logger_module = ModuleType("deadline.unreal_logger")
    setattr(logger_module, "get_logger", MagicMock(return_value=MagicMock()))

    saved_unreal = sys.modules.get("unreal")
    saved_mod = sys.modules.pop("remote_executor", None)
    saved_submitter_module = sys.modules.get("deadline.unreal_submitter.submitter")
    saved_logger_module = sys.modules.get("deadline.unreal_logger")
    sys.modules["unreal"] = unreal_mock
    sys.modules["deadline.unreal_submitter.submitter"] = submitter_module
    sys.modules["deadline.unreal_logger"] = logger_module
    if plugin_py not in sys.path:
        sys.path.insert(0, plugin_py)
    try:
        import remote_executor as mod

        yield mod
    finally:
        sys.modules.pop("remote_executor", None)
        if saved_mod is not None:
            sys.modules["remote_executor"] = saved_mod
        if saved_unreal is not None:
            sys.modules["unreal"] = saved_unreal
        else:
            sys.modules.pop("unreal", None)
        if saved_submitter_module is not None:
            sys.modules["deadline.unreal_submitter.submitter"] = saved_submitter_module
        else:
            sys.modules.pop("deadline.unreal_submitter.submitter", None)
        if saved_logger_module is not None:
            sys.modules["deadline.unreal_logger"] = saved_logger_module
        else:
            sys.modules.pop("deadline.unreal_logger", None)


def test_execute_delayed_submits_only_enabled_jobs_with_enabled_shots(remote_executor):
    eligible_job = _job("Eligible", enabled=True, shot_states=(True,))
    disabled_job = _job("Disabled", enabled=False, shot_states=(True,))
    all_shots_disabled_job = _job("AllShotsDisabled", enabled=True, shot_states=(False, False))
    unpopulated_shots_job = _job("UnpopulatedShots", enabled=True, shot_states=())
    queue = MagicMock()
    queue.get_jobs.return_value = [
        eligible_job,
        disabled_job,
        all_shots_disabled_job,
        unpopulated_shots_job,
    ]

    executor = remote_executor.MoviePipelineDeadlineCloudRemoteExecutor()
    executor.check_dirty_packages = MagicMock(return_value=True)
    executor.check_maps = MagicMock(return_value=True)
    submitter = MagicMock()

    with patch.object(remote_executor, "UnrealMrqJobSubmitter", return_value=submitter):
        executor.execute_delayed(queue)

    executor.check_maps.assert_called_once_with([eligible_job, unpopulated_shots_job])
    assert submitter.add_job.call_args_list == [call(eligible_job), call(unpopulated_shots_job)]
    submitter.submit_jobs.assert_called_once_with()


def test_execute_delayed_finishes_when_no_jobs_are_eligible(remote_executor):
    disabled_job = _job("Disabled", enabled=False, shot_states=(True,))
    all_shots_disabled_job = _job("AllShotsDisabled", enabled=True, shot_states=(False, False))
    queue = MagicMock()
    queue.get_jobs.return_value = [disabled_job, all_shots_disabled_job]

    executor = remote_executor.MoviePipelineDeadlineCloudRemoteExecutor()
    executor.on_executor_finished_impl = MagicMock()
    executor.check_dirty_packages = MagicMock()
    executor.check_maps = MagicMock()

    with patch.object(remote_executor, "UnrealMrqJobSubmitter") as submitter_class:
        executor.execute_delayed(queue)

    executor.on_executor_finished_impl.assert_called_once_with()
    executor.check_dirty_packages.assert_not_called()
    executor.check_maps.assert_not_called()
    submitter_class.assert_not_called()
