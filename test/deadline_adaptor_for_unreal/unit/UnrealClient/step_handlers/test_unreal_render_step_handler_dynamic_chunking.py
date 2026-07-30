# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
import pytest
from unittest.mock import MagicMock

unreal_mock = MagicMock()
unreal_mock.log = MagicMock()
sys.modules["unreal"] = unreal_mock


@pytest.fixture()
def unreal_render_step_handler():
    from deadline.unreal_adaptor.UnrealClient.step_handlers.unreal_render_step_handler import (
        UnrealRenderStepHandler,
    )

    # Clear cached values before each test
    UnrealRenderStepHandler.cached_frame_range_start = None
    UnrealRenderStepHandler.cached_frame_range_end = None
    return UnrealRenderStepHandler()


class TestParseDynamicChunkedFrames:
    """Tests for parse_dynamic_chunked_frames static method.

    Only CONTIGUOUS rangeConstraint is supported because Unreal Engine's Movie Render Queue
    only accepts contiguous frame ranges (custom_start_frame/custom_end_frame). MRQ does not
    provide an API to render arbitrary non-contiguous frames in a single job.
    """

    @pytest.mark.parametrize(
        "input_value, expected_start, expected_end",
        [
            ("1-10", 1, 10),  # Range
            ("0-100", 0, 100),  # Range starting from zero
            ("5-5", 5, 5),  # Range with same start and end (single frame)
            ("0-0", 0, 0),  # Single frame zero as range
            ("100-100", 100, 100),  # Single frame large number as range
            ("10-20", 10, 20),  # Range middle values
            (" 1-10 ", 1, 10),  # Range with whitespace
            (" 5-5 ", 5, 5),  # Single frame range with extra whitespace
            # Negative frame support
            ("-100--76", -100, -76),  # Both negative
            ("-50-10", -50, 10),  # Negative start, positive end
            ("-10--10", -10, -10),  # Single negative frame as range
            ("-1-0", -1, 0),  # Negative to zero
            (" -100--76 ", -100, -76),  # Negative with whitespace
        ],
    )
    def test_valid_frame_chunk_formats(
        self, unreal_render_step_handler, input_value, expected_start, expected_end
    ):
        """Test that valid frame chunk formats are parsed correctly"""
        # WHEN
        start, end = unreal_render_step_handler.parse_dynamic_chunked_frames(input_value)

        # THEN
        assert start == expected_start
        assert end == expected_end

    @pytest.mark.parametrize(
        "input_value, expected_error_substring",
        [
            ("", "cannot be empty"),  # Empty string
            ("   ", "cannot be empty"),  # Whitespace only
            ("5", "Invalid dynamic_chunked_frames format"),  # Single frame (not range format)
            ("0", "Invalid dynamic_chunked_frames format"),  # Single frame zero
            ("100", "Invalid dynamic_chunked_frames format"),  # Single frame large number
            ("abc", "Invalid dynamic_chunked_frames format"),  # Non-numeric
            ("1.5", "Invalid dynamic_chunked_frames format"),  # Float
            ("1-", "Invalid dynamic_chunked_frames format"),  # Incomplete range
            ("-10", "Invalid dynamic_chunked_frames format"),  # Negative single frame (not range)
            ("1-10-20", "Invalid dynamic_chunked_frames format"),  # Multiple dashes (ambiguous)
            (
                "1,2,3",
                "Invalid dynamic_chunked_frames format",
            ),  # Non-contiguous list (unsupported - MRQ limitation)
            (
                "1-10:2",
                "Invalid dynamic_chunked_frames format",
            ),  # Stepped range (unsupported - MRQ limitation)
        ],
    )
    def test_invalid_frame_chunk_formats(
        self, unreal_render_step_handler, input_value, expected_error_substring
    ):
        """Test that invalid frame chunk formats raise ValueError with descriptive message"""
        # WHEN/THEN
        with pytest.raises(ValueError) as exc_info:
            unreal_render_step_handler.parse_dynamic_chunked_frames(input_value)

        assert expected_error_substring in str(exc_info.value)

    def test_start_greater_than_end_raises_error(self, unreal_render_step_handler):
        """Test that start > end in range raises ValueError"""
        # WHEN/THEN
        with pytest.raises(ValueError) as exc_info:
            unreal_render_step_handler.parse_dynamic_chunked_frames("10-1")

        assert "start (10) cannot be greater than end (1)" in str(exc_info.value)

    def test_negative_start_greater_than_end_raises_error(self, unreal_render_step_handler):
        """Test that start > end with negative frames raises ValueError"""
        # WHEN/THEN
        with pytest.raises(ValueError) as exc_info:
            unreal_render_step_handler.parse_dynamic_chunked_frames("-50--100")

        assert "start (-50) cannot be greater than end (-100)" in str(exc_info.value)


class TestDynamicChunkingPrecedence:
    """Tests for chunking mode precedence, exercised through the real run_script()."""

    @pytest.fixture()
    def run_script_env(self, unreal_render_step_handler):
        """
        Patch run_script's collaborators and wire one mock job into the queue.

        Yields (handler, job_mock, output_settings_mock, patches) where patches
        holds the patched static methods for call assertions.
        """
        from unittest.mock import patch
        import deadline.unreal_adaptor.UnrealClient.step_handlers.unreal_render_step_handler as handler_module

        job = MagicMock()
        output_settings = MagicMock()
        job.get_configuration.return_value.find_or_add_setting_by_class.return_value = (
            output_settings
        )

        subsystem = MagicMock()
        subsystem.get_queue.return_value.get_jobs.return_value = [job]
        unreal_mock.get_editor_subsystem.return_value = subsystem

        # The handler module may already have been imported by another test
        # module with a different (or absent) `unreal`; patch its globals so
        # run_script sees the mock regardless of import order. The executor
        # class only exists when the module was imported with a truthy
        # `unreal`, hence create=True.
        with (
            patch.object(handler_module, "unreal", unreal_mock),
            patch.object(
                handler_module,
                "RemoteRenderMoviePipelineEditorExecutor",
                MagicMock(),
                create=True,
            ),
            patch.object(
                handler_module.UnrealRenderStepHandler, "create_queue_from_job_args"
            ) as create_queue,
            patch.object(
                handler_module.UnrealRenderStepHandler, "enable_shots_for_task"
            ) as enable_shots,
            patch.object(
                handler_module.UnrealRenderStepHandler, "_apply_task_index_to_filename"
            ) as apply_filename,
            patch.object(
                handler_module.UnrealRenderStepHandler, "get_frame_range", return_value=(0, 100)
            ) as get_frame_range,
        ):
            patches = {
                "create_queue": create_queue,
                "enable_shots": enable_shots,
                "apply_filename": apply_filename,
                "get_frame_range": get_frame_range,
            }
            yield unreal_render_step_handler, job, output_settings, patches

    def test_dynamic_chunking_takes_precedence_over_frames_per_task(self, run_script_env):
        """When all three modes' args are present, dynamic chunking wins."""
        handler, job, output_settings, patches = run_script_env

        # WHEN
        handler.run_script(
            {
                "dynamic_chunked_frames": "1-10",
                "frames_per_task": 5,
                "task_index": 0,
                "shots_per_task": 3,
            }
        )

        # THEN - the dynamic branch ran: inclusive "1-10" -> exclusive [1, 11)
        assert output_settings.use_custom_playback_range is True
        assert output_settings.custom_start_frame == 1
        assert output_settings.custom_end_frame == 11
        # frame-based path not taken
        patches["get_frame_range"].assert_not_called()
        # shot-based path not taken
        patches["enable_shots"].assert_not_called()
        # filename token substituted with the chunk START FRAME, not task_index
        patches["apply_filename"].assert_called_once_with(job, 1)

    def test_frames_per_task_used_when_no_dynamic_chunking(self, run_script_env):
        """Without dynamic_chunked_frames, frames_per_task + task_index wins."""
        handler, job, output_settings, patches = run_script_env

        # WHEN
        handler.run_script({"frames_per_task": 5, "task_index": 0, "shots_per_task": 3})

        # THEN - frame window [0, 5) computed from get_frame_range()=(0, 100)
        assert output_settings.custom_start_frame == 0
        assert output_settings.custom_end_frame == 5
        patches["enable_shots"].assert_not_called()
        patches["apply_filename"].assert_called_once_with(job, 0)

    def test_shots_per_task_used_when_no_dynamic_or_frames_per_task(self, run_script_env):
        """Without the higher-priority modes, shots_per_task + task_index wins."""
        handler, job, output_settings, patches = run_script_env

        # WHEN
        handler.run_script({"shots_per_task": 3, "task_index": 1})

        # THEN
        patches["enable_shots"].assert_called_once_with(
            render_job=job, shots_per_task=3, task_index=1
        )
        patches["get_frame_range"].assert_not_called()
        patches["apply_filename"].assert_called_once_with(job, 1)

    def test_no_chunking_when_no_params(self, run_script_env):
        """With no chunking args, no chunking branch runs."""
        handler, job, output_settings, patches = run_script_env

        # WHEN
        handler.run_script({})

        # THEN
        patches["enable_shots"].assert_not_called()
        patches["apply_filename"].assert_not_called()
        patches["get_frame_range"].assert_not_called()


class TestStaticMethodBehavior:
    """Tests for static method behavior"""

    def test_parse_dynamic_chunked_frames_is_static(self, unreal_render_step_handler):
        """Test that parse_dynamic_chunked_frames can be called as static method"""
        from deadline.unreal_adaptor.UnrealClient.step_handlers.unreal_render_step_handler import (
            UnrealRenderStepHandler,
        )

        # WHEN - Call as static method
        start, end = UnrealRenderStepHandler.parse_dynamic_chunked_frames("1-10")

        # THEN
        assert start == 1
        assert end == 10

    def test_parse_dynamic_chunked_frames_across_instances(self, unreal_render_step_handler):
        """Test that parse_dynamic_chunked_frames works consistently across instances"""
        from deadline.unreal_adaptor.UnrealClient.step_handlers.unreal_render_step_handler import (
            UnrealRenderStepHandler,
        )

        handler1 = UnrealRenderStepHandler()
        handler2 = UnrealRenderStepHandler()

        # WHEN
        start1, end1 = handler1.parse_dynamic_chunked_frames("5-15")
        start2, end2 = handler2.parse_dynamic_chunked_frames("5-15")

        # THEN
        assert start1 == start2 == 5
        assert end1 == end2 == 15


class TestDynamicChunkingInclusiveToExclusiveConversion:
    """Tests for inclusive-to-exclusive frame range conversion.

    The scheduler returns inclusive frame ranges (e.g., "150-150" means render frame 150,
    which is 1 frame), but Unreal Engine's custom_end_frame is exclusive. The adaptor
    must add 1 to the end frame to correctly render the expected number of frames.
    """

    @pytest.mark.parametrize(
        "dynamic_chunked_frames, expected_start, expected_ue_end, expected_frame_count",
        [
            ("150-150", 150, 151, 1),  # Single frame - the bug case
            ("0-0", 0, 1, 1),  # Single frame at zero
            ("1-10", 1, 11, 10),  # Range of 10 frames
            ("0-99", 0, 100, 100),  # 100 frames starting from 0
            ("50-74", 50, 75, 25),  # Mid-range chunk
        ],
    )
    def test_dynamic_chunking_converts_inclusive_to_exclusive_end_frame(
        self,
        unreal_render_step_handler,
        dynamic_chunked_frames,
        expected_start,
        expected_ue_end,
        expected_frame_count,
    ):
        """Test that dynamic chunking adds 1 to end frame for Unreal's exclusive end frame.

        The scheduler returns inclusive ranges (e.g., "150-150" = 1 frame), but Unreal's
        custom_end_frame is exclusive. Without the +1 adjustment, "150-150" would result
        in custom_start_frame=150, custom_end_frame=150, which Unreal interprets as 0 frames,
        causing "Cannot render the Queue with frame range of zero length" error.
        """
        # GIVEN - Parse the dynamic_chunked_frames as run_script does
        start_frame, end_frame = unreal_render_step_handler.parse_dynamic_chunked_frames(
            dynamic_chunked_frames
        )

        # WHEN - Apply the +1 conversion as run_script does for dynamic chunking
        # This simulates the logic in run_script:
        #   end_frame = end_frame + 1  # Convert inclusive to exclusive
        ue_end_frame = end_frame + 1

        # THEN - Verify the converted values match expected Unreal settings
        assert start_frame == expected_start
        assert ue_end_frame == expected_ue_end

        # Verify the frame count Unreal will calculate (end - start)
        actual_frame_count = ue_end_frame - start_frame
        assert actual_frame_count == expected_frame_count

    def test_single_frame_chunk_does_not_cause_zero_length_error(self, unreal_render_step_handler):
        """Test that single frame chunk "150-150" results in 1 frame, not 0.

        This is the specific bug case: scheduler sends "150-150" meaning render frame 150.
        Without the fix, Unreal would get start=150, end=150, calculate 0 frames, and error.
        With the fix, Unreal gets start=150, end=151, correctly rendering 1 frame.
        """
        # GIVEN - The bug case input
        dynamic_chunked_frames = "150-150"

        # WHEN - Parse and apply the conversion
        start_frame, end_frame = unreal_render_step_handler.parse_dynamic_chunked_frames(
            dynamic_chunked_frames
        )
        ue_end_frame = end_frame + 1  # The fix: convert inclusive to exclusive

        # THEN - Frame range should be 150-151 (1 frame), not 150-150 (0 frames)
        assert start_frame == 150
        assert ue_end_frame == 151  # +1 for exclusive end

        # The frame count Unreal will calculate: 151 - 150 = 1 frame
        frame_count = ue_end_frame - start_frame
        assert frame_count == 1, "Single frame chunk should result in exactly 1 frame"

        # Without the fix, this would be 0 frames:
        frame_count_without_fix = end_frame - start_frame
        assert frame_count_without_fix == 0, "Without fix, single frame chunk would be 0 frames"

    def test_inclusive_range_semantics(self, unreal_render_step_handler):
        """Test that the scheduler's inclusive range semantics are correctly understood.

        Scheduler range "10-20" means frames 10, 11, 12, ..., 19, 20 = 11 frames total.
        Unreal's exclusive end means custom_end_frame=21 to render those 11 frames.
        """
        # GIVEN
        dynamic_chunked_frames = "10-20"

        # WHEN
        start_frame, end_frame = unreal_render_step_handler.parse_dynamic_chunked_frames(
            dynamic_chunked_frames
        )
        ue_end_frame = end_frame + 1

        # THEN
        # Scheduler says "10-20" = frames 10 through 20 inclusive = 11 frames
        scheduler_frame_count = end_frame - start_frame + 1  # Inclusive count
        assert scheduler_frame_count == 11

        # Unreal needs end=21 to render 11 frames (21 - 10 = 11)
        assert ue_end_frame == 21
        ue_frame_count = ue_end_frame - start_frame  # Exclusive count
        assert ue_frame_count == 11
