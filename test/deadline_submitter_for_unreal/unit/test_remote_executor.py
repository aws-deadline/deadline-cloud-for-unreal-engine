# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Regression tests for MRQ remote-submission eligibility filtering."""

import os
import sys
from types import ModuleType
from types import SimpleNamespace
from typing import Union
from unittest.mock import MagicMock, call, patch

import pytest


def _job(
    name: str,
    enabled: bool,
    shot_states: tuple[bool, ...],
    frames_per_task: Union[int, str] = 0,
    has_frames_parameter: bool = False,
    step_template_paths: tuple[str, ...] = (),
    has_parameter_definitions: bool = True,
    has_job_preset: bool = True,
) -> SimpleNamespace:
    job = SimpleNamespace(
        job_name=name,
        shot_info=[SimpleNamespace(enabled=shot_enabled) for shot_enabled in shot_states],
    )
    job.is_enabled = MagicMock(return_value=enabled)
    job.job_preset = (
        SimpleNamespace(
            steps=[
                SimpleNamespace(path_to_template=SimpleNamespace(file_path=path))
                for path in step_template_paths
            ]
        )
        if has_job_preset
        else None
    )
    if has_parameter_definitions:
        parameters = [SimpleNamespace(name="FramesPerTask", value=frames_per_task)]
        if has_frames_parameter:
            parameters.append(SimpleNamespace(name="Frames", value=None))
        job.get_parameter_definition_with_overrides = MagicMock(
            return_value=SimpleNamespace(parameters=parameters)
        )
    return job


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


def test_execute_delayed_submits_only_enabled_jobs_with_enabled_shots(remote_executor, tmp_path):
    dynamic_chunking_step_template = tmp_path / "dynamic_chunking_step.yml"
    dynamic_chunking_step_template_contents = """
parameterSpace:
  taskParameterDefinitions:
  - name: DynamicChunking
    type: CHUNK[INT]
    range: 1-10
""".strip()
    dynamic_chunking_step_template.write_text(dynamic_chunking_step_template_contents)

    eligible_job = _job("Eligible", enabled=True, shot_states=(True,))
    disabled_job = _job("Disabled", enabled=False, shot_states=(True,))
    all_shots_disabled_job = _job("AllShotsDisabled", enabled=True, shot_states=(False, False))
    frame_based_unpopulated_shots_job = _job(
        "FrameBasedUnpopulatedShots", enabled=True, shot_states=(), frames_per_task=10
    )
    dynamic_chunking_unpopulated_shots_job = _job(
        "DynamicChunkingUnpopulatedShots",
        enabled=True,
        shot_states=(),
        step_template_paths=(str(dynamic_chunking_step_template),),
    )
    generic_frames_unpopulated_shots_job = _job(
        "GenericFramesUnpopulatedShots",
        enabled=True,
        shot_states=(),
        has_frames_parameter=True,
    )
    shot_based_unpopulated_shots_job = _job(
        "ShotBasedUnpopulatedShots", enabled=True, shot_states=()
    )
    queue = MagicMock()
    queue.get_jobs.return_value = [
        eligible_job,
        disabled_job,
        all_shots_disabled_job,
        frame_based_unpopulated_shots_job,
        dynamic_chunking_unpopulated_shots_job,
        generic_frames_unpopulated_shots_job,
        shot_based_unpopulated_shots_job,
    ]

    executor = remote_executor.MoviePipelineDeadlineCloudRemoteExecutor()
    executor.check_dirty_packages = MagicMock(return_value=True)
    executor.check_maps = MagicMock(return_value=True)
    submitter = MagicMock()

    with patch.object(remote_executor, "UnrealMrqJobSubmitter", return_value=submitter):
        executor.execute_delayed(queue)

    executor.check_maps.assert_called_once_with(
        [
            eligible_job,
            frame_based_unpopulated_shots_job,
            dynamic_chunking_unpopulated_shots_job,
        ]
    )
    assert submitter.add_job.call_args_list == [
        call(eligible_job),
        call(frame_based_unpopulated_shots_job),
        call(dynamic_chunking_unpopulated_shots_job),
    ]
    submitter.submit_jobs.assert_called_once_with()
    for job in [
        eligible_job,
        disabled_job,
        all_shots_disabled_job,
        frame_based_unpopulated_shots_job,
        dynamic_chunking_unpopulated_shots_job,
        generic_frames_unpopulated_shots_job,
        shot_based_unpopulated_shots_job,
    ]:
        job.is_enabled.assert_called_once_with()


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


def test__is_frame_based_job_returns_false_without_parameter_definitions(remote_executor):
    job = _job(
        "BaseJob",
        enabled=True,
        shot_states=(),
        has_parameter_definitions=False,
    )

    assert not remote_executor.MoviePipelineDeadlineCloudRemoteExecutor._is_frame_based_job(job)


def test__is_frame_based_job_returns_false_for_invalid_frames_per_task(remote_executor):
    job = _job(
        "InvalidFramesPerTask",
        enabled=True,
        shot_states=(),
        frames_per_task="not-an-integer",
    )

    assert not remote_executor.MoviePipelineDeadlineCloudRemoteExecutor._is_frame_based_job(job)


def test__is_frame_based_job_returns_false_without_job_preset(remote_executor):
    job = _job(
        "NoJobPreset",
        enabled=True,
        shot_states=(),
        frames_per_task=10,
        has_job_preset=False,
    )

    assert not remote_executor.MoviePipelineDeadlineCloudRemoteExecutor._is_frame_based_job(job)
    job.get_parameter_definition_with_overrides.assert_not_called()
