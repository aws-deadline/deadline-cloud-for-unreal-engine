# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
import pytest
from unittest.mock import MagicMock, patch

unreal_mock = MagicMock()
sys.modules["unreal"] = unreal_mock

from deadline.unreal_submitter.unreal_open_job.unreal_open_job import (  # noqa: E402
    UnrealOpenJob,
    UnrealOpenJobParameterDefinition,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step import (  # noqa: E402
    RenderUnrealOpenJobStep,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity import (  # noqa: E402
    OpenJobStepParameterNames,
)


class TestRenderUnrealOpenJobStepFramesPerTask:

    @pytest.mark.parametrize(
        "frames_per_task, total_frames, expected_task_count",
        [
            (10, 100, 10),  # Even division
            (10, 95, 10),  # Rounds up
            (10, 105, 11),  # Rounds up
            (25, 100, 4),  # Even division
            (30, 100, 4),  # Rounds up
            (1, 50, 50),  # One frame per task
            (100, 50, 1),  # More frames per task than total
        ],
    )
    def test_get_chunk_ids_count_frames_per_task_custom_range(
        self, frames_per_task, total_frames, expected_task_count
    ):
        # GIVEN
        frames_per_task_param = UnrealOpenJobParameterDefinition(
            OpenJobStepParameterNames.FRAMES_PER_TASK, "INT", frames_per_task
        )
        job = UnrealOpenJob(file_path="", name="TestJob", extra_parameters=[frames_per_task_param])

        mrq_job_mock = MagicMock()
        render_step = RenderUnrealOpenJobStep(file_path="", mrq_job=mrq_job_mock)
        render_step.open_job = job

        # Mock output settings with custom range
        output_settings_mock = MagicMock()
        output_settings_mock.use_custom_playback_range = True
        output_settings_mock.custom_start_frame = 10
        output_settings_mock.custom_end_frame = 10 + total_frames

        with patch.object(render_step, "_load_output_settings", return_value=output_settings_mock):
            # WHEN
            task_count = render_step._get_chunk_ids_count()

            # THEN
            assert task_count == expected_task_count

    @pytest.mark.parametrize(
        "frames_per_task, sequence_start, sequence_end, expected_task_count",
        [
            (10, 1, 100, 10),  # 99 frames (100-1), 10 per task = ceil(9.9) = 10
            (15, 5, 50, 3),  # 45 frames (50-5), 15 per task = ceil(3.0) = 3
            (20, 0, 39, 2),  # 39 frames (39-0), 20 per task = ceil(1.95) = 2
            (50, 10, 30, 1),  # 20 frames (30-10), 50 per task = ceil(0.4) = 1
        ],
    )
    def test_get_chunk_ids_count_frames_per_task_sequence_range(
        self, frames_per_task, sequence_start, sequence_end, expected_task_count
    ):
        # GIVEN
        frames_per_task_param = UnrealOpenJobParameterDefinition(
            OpenJobStepParameterNames.FRAMES_PER_TASK, "INT", frames_per_task
        )
        job = UnrealOpenJob(file_path="", name="TestJob", extra_parameters=[frames_per_task_param])

        mrq_job_mock = MagicMock()
        render_step = RenderUnrealOpenJobStep(file_path="", mrq_job=mrq_job_mock)
        render_step.open_job = job

        # Mock level sequence and output settings
        level_sequence_mock = MagicMock()
        playback_range_mock = MagicMock()
        playback_range_mock.get_start_frame.return_value = sequence_start
        playback_range_mock.get_end_frame.return_value = sequence_end
        level_sequence_mock.get_playback_range.return_value = playback_range_mock

        output_settings_mock = MagicMock()
        output_settings_mock.use_custom_playback_range = False

        with (
            patch.object(render_step, "_load_level_sequence", return_value=level_sequence_mock),
            patch.object(render_step, "_load_output_settings", return_value=output_settings_mock),
        ):

            # WHEN
            task_count = render_step._get_chunk_ids_count()

            # THEN
            assert task_count == expected_task_count

    def test_get_chunk_ids_count_frames_per_task_precedence_over_chunk_size(self):
        # GIVEN - Both FramesPerTask and ChunkSize provided, FramesPerTask should take precedence
        frames_per_task_param = UnrealOpenJobParameterDefinition(
            OpenJobStepParameterNames.FRAMES_PER_TASK, "INT", 25
        )
        chunk_size_param = UnrealOpenJobParameterDefinition(
            OpenJobStepParameterNames.TASK_CHUNK_SIZE, "INT", 5
        )
        job = UnrealOpenJob(
            file_path="", name="TestJob", extra_parameters=[frames_per_task_param, chunk_size_param]
        )

        mrq_job_mock = MagicMock()
        render_step = RenderUnrealOpenJobStep(file_path="", mrq_job=mrq_job_mock)
        render_step.open_job = job

        # Mock output settings with custom range (99 frames)
        output_settings_mock = MagicMock()
        output_settings_mock.use_custom_playback_range = True
        output_settings_mock.custom_start_frame = 1
        output_settings_mock.custom_end_frame = 100

        with patch.object(render_step, "_load_output_settings", return_value=output_settings_mock):
            # WHEN
            task_count = render_step._get_chunk_ids_count()

            # THEN - Should use FramesPerTask: 99 frames / 25 per task = 4 tasks (math.ceil(3.96))
            assert task_count == 4

    def test_get_chunk_ids_count_frames_per_task_fallback_to_chunk_size(self):
        # GIVEN - FramesPerTask is 0, should fall back to ChunkSize
        frames_per_task_param = UnrealOpenJobParameterDefinition(
            OpenJobStepParameterNames.FRAMES_PER_TASK, "INT", 0
        )
        chunk_size_param = UnrealOpenJobParameterDefinition(
            OpenJobStepParameterNames.TASK_CHUNK_SIZE, "INT", 5
        )
        job = UnrealOpenJob(
            file_path="", name="TestJob", extra_parameters=[frames_per_task_param, chunk_size_param]
        )

        # Mock MRQ job with shots
        shot_info = []
        for _ in range(10):  # 10 shots
            shot_info_mock = MagicMock()
            shot_info_mock.enabled = True
            shot_info.append(shot_info_mock)

        mrq_job_mock = MagicMock()
        mrq_job_mock.shot_info = shot_info

        render_step = RenderUnrealOpenJobStep(file_path="", mrq_job=mrq_job_mock)
        render_step.open_job = job

        # WHEN
        task_count = render_step._get_chunk_ids_count()

        # THEN - Should use chunk size logic: 10 shots / 5 per chunk = 2 tasks
        assert task_count == 2

    def test_get_chunk_ids_count_frames_per_task_no_fallback_error(self):
        # GIVEN - FramesPerTask is 0 and no ChunkSize parameter
        frames_per_task_param = UnrealOpenJobParameterDefinition(
            OpenJobStepParameterNames.FRAMES_PER_TASK, "INT", 0
        )
        job = UnrealOpenJob(file_path="", name="TestJob", extra_parameters=[frames_per_task_param])

        mrq_job_mock = MagicMock()
        mrq_job_mock.shot_info = []

        render_step = RenderUnrealOpenJobStep(file_path="", mrq_job=mrq_job_mock)
        render_step.open_job = job

        # WHEN/THEN - Should raise ValueError about missing parameters
        with pytest.raises(ValueError) as exception_info:
            render_step._get_chunk_ids_count()

        assert OpenJobStepParameterNames.TASK_CHUNK_SIZE in str(exception_info.value)
        assert OpenJobStepParameterNames.FRAMES_PER_TASK in str(exception_info.value)
