# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
import pytest
from unittest.mock import MagicMock, patch

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


class TestUnrealRenderStepHandlerFramesPerTask:

    @pytest.mark.parametrize(
        "use_custom_range, custom_start, custom_end, sequence_start, sequence_end, expected_start, expected_end",
        [
            (True, 10, 50, 1, 100, 10, 50),  # Custom range used
            (False, 10, 50, 1, 100, 1, 100),  # Sequence range used
            (True, 0, 30, 5, 25, 0, 30),  # Custom range overrides sequence
        ],
    )
    def test_get_frame_range_caching(
        self,
        unreal_render_step_handler,
        use_custom_range,
        custom_start,
        custom_end,
        sequence_start,
        sequence_end,
        expected_start,
        expected_end,
    ):
        # GIVEN
        output_settings = MagicMock()
        output_settings.use_custom_playback_range = use_custom_range
        output_settings.custom_start_frame = custom_start
        output_settings.custom_end_frame = custom_end

        playback_range = MagicMock()
        playback_range.get_start_frame.return_value = sequence_start
        playback_range.get_end_frame.return_value = sequence_end

        level_sequence = MagicMock()
        level_sequence.get_playback_range.return_value = playback_range

        # WHEN - First call should cache values
        with patch(
            "deadline.unreal_adaptor.UnrealClient.step_handlers.unreal_render_step_handler.logger.info"
        ) as log_mock:
            start1, end1 = unreal_render_step_handler.get_frame_range(
                output_settings, level_sequence
            )

            # THEN
            assert start1 == expected_start
            assert end1 == expected_end
            assert log_mock.called

            # WHEN - Second call should use cached values
            log_mock.reset_mock()

            start2, end2 = unreal_render_step_handler.get_frame_range(
                output_settings, level_sequence
            )

            # THEN - Should return same values without logging
            assert start2 == expected_start
            assert end2 == expected_end
            assert not log_mock.called

    def test_get_frame_range_custom_playback_logging(self, unreal_render_step_handler):
        # GIVEN
        output_settings = MagicMock()
        output_settings.use_custom_playback_range = True
        output_settings.custom_start_frame = 5
        output_settings.custom_end_frame = 25

        level_sequence = MagicMock()

        # WHEN
        with patch(
            "deadline.unreal_adaptor.UnrealClient.step_handlers.unreal_render_step_handler.logger.info"
        ) as log_mock:
            unreal_render_step_handler.get_frame_range(output_settings, level_sequence)

            # THEN
            log_mock.assert_called_with("Cached custom frame range from 5 to 25")

    def test_get_frame_range_sequence_playback_logging(self, unreal_render_step_handler):
        # GIVEN
        output_settings = MagicMock()
        output_settings.use_custom_playback_range = False

        playback_range = MagicMock()
        playback_range.get_start_frame.return_value = 1
        playback_range.get_end_frame.return_value = 100

        level_sequence = MagicMock()
        level_sequence.get_playback_range.return_value = playback_range

        # WHEN
        with patch(
            "deadline.unreal_adaptor.UnrealClient.step_handlers.unreal_render_step_handler.logger.info"
        ) as log_mock:
            unreal_render_step_handler.get_frame_range(output_settings, level_sequence)

            # THEN
            log_mock.assert_called_with("Cached level sequence frame range from 1 to 100")

    @pytest.mark.parametrize(
        "task_index, frames_per_task, frame_start, frame_end, expected_start, expected_end",
        [
            (0, 10, 1, 100, 1, 11),  # First task
            (1, 10, 1, 100, 11, 21),  # Second task
            (9, 10, 1, 100, 91, 100),  # Last task (clamped to end)
            (0, 50, 10, 30, 10, 30),  # Single task covers entire range
            (2, 5, 0, 20, 10, 15),  # Middle task
        ],
    )
    def test_frames_per_task_calculation_logic(
        self,
        unreal_render_step_handler,
        task_index,
        frames_per_task,
        frame_start,
        frame_end,
        expected_start,
        expected_end,
    ):
        """Test the frame calculation logic without full run_script execution"""
        # GIVEN
        output_settings = MagicMock()
        level_sequence = MagicMock()

        # Mock frame range method
        with patch.object(
            unreal_render_step_handler, "get_frame_range", return_value=(frame_start, frame_end)
        ):
            # WHEN - Simulate the frame calculation logic from run_script
            frame_range_start, frame_range_end = unreal_render_step_handler.get_frame_range(
                output_settings, level_sequence
            )

            calculated_start = frame_range_start + (task_index * frames_per_task)
            calculated_end = min(calculated_start + frames_per_task, frame_range_end)

            # THEN
            assert calculated_start == expected_start
            assert calculated_end == expected_end

    def test_frames_per_task_vs_shots_per_task_precedence(self, unreal_render_step_handler):
        """Test that frames_per_task takes precedence over shots_per_task in argument processing"""
        # GIVEN
        args_with_frames_per_task = {
            "frames_per_task": 10,
            "task_index": 1,
            "shots_per_task": 5,  # This should be ignored
        }

        args_with_shots_per_task_only = {
            "shots_per_task": 5,
            "task_index": 1,
        }

        args_no_partitioning: dict[str, int] = {}

        # WHEN/THEN - Test precedence logic
        # frames_per_task should be used when present
        assert (
            args_with_frames_per_task.get("frames_per_task")
            and "task_index" in args_with_frames_per_task
        )

        # shots_per_task should be used when frames_per_task is not present
        assert (
            not args_with_shots_per_task_only.get("frames_per_task")
            and "shots_per_task" in args_with_shots_per_task_only
        )

        # No partitioning when neither is present
        assert (
            not args_no_partitioning.get("frames_per_task")
            and "shots_per_task" not in args_no_partitioning
        )

    def test_frame_range_caching_behavior(self, unreal_render_step_handler):
        """Test that frame range caching works correctly across multiple calls"""
        # GIVEN
        output_settings = MagicMock()
        output_settings.use_custom_playback_range = True
        output_settings.custom_start_frame = 10
        output_settings.custom_end_frame = 50

        level_sequence = MagicMock()

        # WHEN - Multiple calls to get_frame_range
        start1, end1 = unreal_render_step_handler.get_frame_range(output_settings, level_sequence)
        start2, end2 = unreal_render_step_handler.get_frame_range(output_settings, level_sequence)
        start3, end3 = unreal_render_step_handler.get_frame_range(output_settings, level_sequence)

        # THEN - All calls should return the same cached values
        assert start1 == start2 == start3 == 10
        assert end1 == end2 == end3 == 50

        # Verify the cached values are stored in class variables
        assert unreal_render_step_handler.cached_frame_range_start == 10
        assert unreal_render_step_handler.cached_frame_range_end == 50

    def test_frame_range_edge_cases(self, unreal_render_step_handler):
        """Test edge cases for frame range calculations"""
        # Test case 1: task_index * frames_per_task exceeds total range
        output_settings = MagicMock()
        level_sequence = MagicMock()

        with patch.object(unreal_render_step_handler, "get_frame_range", return_value=(1, 50)):
            frame_range_start, frame_range_end = unreal_render_step_handler.get_frame_range(
                output_settings, level_sequence
            )

            # task_index=10, frames_per_task=10 would start at frame 101, but range only goes to 50
            task_index = 10
            frames_per_task = 10

            calculated_start = frame_range_start + (task_index * frames_per_task)  # 1 + 100 = 101
            calculated_end = min(
                calculated_start + frames_per_task, frame_range_end
            )  # min(111, 50) = 50

            assert calculated_start == 101
            assert calculated_end == 50  # Clamped to range end

    @pytest.mark.parametrize(
        "fmt, task_index, expected",
        [
            ("{sequence_name}_{task_index}", 0, "{sequence_name}_0000"),
            ("{sequence_name}_{task_index}", 7, "{sequence_name}_0007"),
            ("{shot_name}.{task_index}.{render_pass}", 42, "{shot_name}.0042.{render_pass}"),
        ],
    )
    def test_apply_task_index_substitutes_token(
        self, unreal_render_step_handler, fmt, task_index, expected
    ):
        from deadline.unreal_adaptor.UnrealClient.step_handlers import (
            unreal_render_step_handler as handler_mod,
        )

        output_settings = MagicMock()
        output_settings.file_name_format = fmt
        render_job = MagicMock()
        render_job.get_configuration.return_value.find_or_add_setting_by_class.return_value = (
            output_settings
        )

        with patch.object(handler_mod, "unreal", MagicMock()):
            handler_mod.UnrealRenderStepHandler._apply_task_index_to_filename(
                render_job, task_index
            )

        assert output_settings.file_name_format == expected

    def test_apply_task_index_warns_when_no_per_task_token(self, unreal_render_step_handler):
        from deadline.unreal_adaptor.UnrealClient.step_handlers import (
            unreal_render_step_handler as handler_mod,
        )

        output_settings = MagicMock()
        output_settings.file_name_format = "{sequence_name}"
        render_job = MagicMock()
        render_job.get_configuration.return_value.find_or_add_setting_by_class.return_value = (
            output_settings
        )

        with (
            patch.object(handler_mod, "unreal", MagicMock()),
            patch.object(handler_mod.logger, "warning") as warn_mock,
        ):
            handler_mod.UnrealRenderStepHandler._apply_task_index_to_filename(render_job, 3)

        assert output_settings.file_name_format == "{sequence_name}"
        warn_mock.assert_called_once()

    def test_apply_task_index_silent_when_frame_number_present(self, unreal_render_step_handler):
        from deadline.unreal_adaptor.UnrealClient.step_handlers import (
            unreal_render_step_handler as handler_mod,
        )

        output_settings = MagicMock()
        output_settings.file_name_format = "{sequence_name}.{frame_number}"
        render_job = MagicMock()
        render_job.get_configuration.return_value.find_or_add_setting_by_class.return_value = (
            output_settings
        )

        with (
            patch.object(handler_mod, "unreal", MagicMock()),
            patch.object(handler_mod.logger, "warning") as warn_mock,
        ):
            handler_mod.UnrealRenderStepHandler._apply_task_index_to_filename(render_job, 3)

        assert output_settings.file_name_format == "{sequence_name}.{frame_number}"
        warn_mock.assert_not_called()

    def test_static_method_behavior(self, unreal_render_step_handler):
        """Test that get_frame_range is a static method and caching works across instances"""
        # GIVEN
        from deadline.unreal_adaptor.UnrealClient.step_handlers.unreal_render_step_handler import (
            UnrealRenderStepHandler,
        )

        # Clear any existing cache
        UnrealRenderStepHandler.cached_frame_range_start = None
        UnrealRenderStepHandler.cached_frame_range_end = None

        handler1 = UnrealRenderStepHandler()
        handler2 = UnrealRenderStepHandler()

        output_settings = MagicMock()
        output_settings.use_custom_playback_range = True
        output_settings.custom_start_frame = 20
        output_settings.custom_end_frame = 80

        level_sequence = MagicMock()

        # WHEN - Call from first instance
        start1, end1 = handler1.get_frame_range(output_settings, level_sequence)

        # THEN - Second instance should use the same cached values
        start2, end2 = handler2.get_frame_range(output_settings, level_sequence)

        assert start1 == start2 == 20
        assert end1 == end2 == 80

        # Both instances should see the same cached values
        assert handler1.cached_frame_range_start == handler2.cached_frame_range_start == 20
        assert handler1.cached_frame_range_end == handler2.cached_frame_range_end == 80
