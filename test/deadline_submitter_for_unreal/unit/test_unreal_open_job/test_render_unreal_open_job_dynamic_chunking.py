# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
from unittest.mock import patch, MagicMock, Mock

# Mock external modules before importing
unreal_mock = MagicMock()
sys.modules["unreal"] = unreal_mock

p4_mock = Mock()
sys.modules["P4"] = p4_mock

from deadline.unreal_submitter.unreal_open_job.unreal_open_job import (  # noqa: E402
    RenderUnrealOpenJob,
    OpenJobParameterNames,
)


class TestRenderUnrealOpenJobIsUsingDynamicChunking:
    """Tests for RenderUnrealOpenJob._is_using_dynamic_chunking method."""

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object",
        return_value={"parameterDefinitions": []},
    )
    def test_returns_true_when_step_uses_chunk_int(self, get_template_object_mock):
        """Test that _is_using_dynamic_chunking returns True when a step has CHUNK[INT] parameter."""
        # GIVEN
        step_mock = MagicMock()
        step_mock.get_template_object.return_value = {
            "parameterSpace": {
                "taskParameterDefinitions": [
                    {"name": "DynamicChunking", "type": "CHUNK[INT]", "range": "{{Param.Frames}}"}
                ]
            }
        }

        render_job = RenderUnrealOpenJob(file_path="", name="TestJob", steps=[step_mock])

        # WHEN
        result = render_job._is_using_dynamic_chunking()

        # THEN
        assert result is True

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object",
        return_value={"parameterDefinitions": []},
    )
    def test_returns_false_when_step_uses_int_type(self, get_template_object_mock):
        """Test that _is_using_dynamic_chunking returns False when step uses regular INT type."""
        # GIVEN
        step_mock = MagicMock()
        step_mock.get_template_object.return_value = {
            "parameterSpace": {
                "taskParameterDefinitions": [{"name": "ChunkId", "type": "INT", "range": [0, 1, 2]}]
            }
        }

        render_job = RenderUnrealOpenJob(file_path="", name="TestJob", steps=[step_mock])

        # WHEN
        result = render_job._is_using_dynamic_chunking()

        # THEN
        assert result is False

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object",
        return_value={"parameterDefinitions": []},
    )
    def test_returns_false_when_no_steps(self, get_template_object_mock):
        """Test that _is_using_dynamic_chunking returns False when there are no steps."""
        # GIVEN
        render_job = RenderUnrealOpenJob(file_path="", name="TestJob", steps=[])

        # WHEN
        result = render_job._is_using_dynamic_chunking()

        # THEN
        assert result is False

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object",
        return_value={"parameterDefinitions": []},
    )
    def test_returns_true_when_any_step_uses_dynamic_chunking(self, get_template_object_mock):
        """Test that _is_using_dynamic_chunking returns True if any step uses CHUNK[INT]."""
        # GIVEN
        step_regular = MagicMock()
        step_regular.get_template_object.return_value = {
            "parameterSpace": {
                "taskParameterDefinitions": [{"name": "ChunkId", "type": "INT", "range": [0, 1]}]
            }
        }

        step_dynamic = MagicMock()
        step_dynamic.get_template_object.return_value = {
            "parameterSpace": {
                "taskParameterDefinitions": [
                    {"name": "DynamicChunking", "type": "CHUNK[INT]", "range": "{{Param.Frames}}"}
                ]
            }
        }

        render_job = RenderUnrealOpenJob(
            file_path="", name="TestJob", steps=[step_regular, step_dynamic]
        )

        # WHEN
        result = render_job._is_using_dynamic_chunking()

        # THEN
        assert result is True

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object",
        return_value={"parameterDefinitions": []},
    )
    def test_handles_step_template_file_not_found(self, get_template_object_mock):
        """Test that _is_using_dynamic_chunking handles FileNotFoundError gracefully."""
        # GIVEN
        step_mock = MagicMock()
        step_mock.get_template_object.side_effect = FileNotFoundError("Template not found")

        render_job = RenderUnrealOpenJob(file_path="", name="TestJob", steps=[step_mock])

        # WHEN
        result = render_job._is_using_dynamic_chunking()

        # THEN
        assert result is False


class TestRenderUnrealOpenJobBuildFramesParameterValue:
    """Tests for RenderUnrealOpenJob._build_frames_parameter_value method."""

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object",
        return_value={"parameterDefinitions": []},
    )
    def test_returns_unchanged_when_no_frames_parameter(self, get_template_object_mock):
        """Test that parameter values are unchanged when Frames parameter doesn't exist."""
        # GIVEN
        render_job = RenderUnrealOpenJob(file_path="", name="TestJob")
        parameter_values = [{"name": "OtherParam", "value": "test"}]

        # WHEN
        result = render_job._build_frames_parameter_value(parameter_values)

        # THEN
        assert result == parameter_values

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object",
        return_value={"parameterDefinitions": []},
    )
    def test_returns_unchanged_when_frames_already_has_value(self, get_template_object_mock):
        """Test that parameter values are unchanged when Frames already has a value."""
        # GIVEN
        render_job = RenderUnrealOpenJob(file_path="", name="TestJob")
        parameter_values = [{"name": OpenJobParameterNames.FRAMES, "value": "1-100"}]

        # WHEN
        result = render_job._build_frames_parameter_value(parameter_values)

        # THEN
        assert result[0]["value"] == "1-100"

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object",
        return_value={"parameterDefinitions": []},
    )
    def test_returns_unchanged_when_no_mrq_job(self, get_template_object_mock):
        """Test that parameter values are unchanged when MRQ job is not set."""
        # GIVEN
        render_job = RenderUnrealOpenJob(file_path="", name="TestJob")
        parameter_values = [{"name": OpenJobParameterNames.FRAMES, "value": None}]

        # WHEN
        result = render_job._build_frames_parameter_value(parameter_values)

        # THEN
        assert result[0]["value"] is None

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object",
        return_value={"parameterDefinitions": []},
    )
    def test_populates_frames_from_custom_playback_range(self, get_template_object_mock):
        """Test that Frames is populated from custom playback range when enabled."""
        # GIVEN
        output_settings_mock = MagicMock()
        output_settings_mock.use_custom_playback_range = True
        output_settings_mock.custom_start_frame = 10
        output_settings_mock.custom_end_frame = 50

        config_mock = MagicMock()
        config_mock.find_setting_by_class.return_value = output_settings_mock

        mrq_job_mock = MagicMock()
        mrq_job_mock.get_configuration.return_value = config_mock
        mrq_job_mock.sequence = MagicMock()

        level_sequence_mock = MagicMock()

        render_job = RenderUnrealOpenJob(file_path="", name="TestJob")
        render_job._mrq_job = mrq_job_mock

        parameter_values = [{"name": OpenJobParameterNames.FRAMES, "value": None}]

        with patch(
            "deadline.unreal_submitter.unreal_open_job.unreal_open_job.unreal.EditorAssetLibrary.load_asset",
            return_value=level_sequence_mock,
        ):
            # WHEN
            result = render_job._build_frames_parameter_value(parameter_values)

        # THEN
        assert result[0]["value"] == "10-50"

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object",
        return_value={"parameterDefinitions": []},
    )
    def test_populates_frames_from_level_sequence_playback_range(self, get_template_object_mock):
        """Test that Frames is populated from level sequence when custom range is disabled."""
        # GIVEN
        output_settings_mock = MagicMock()
        output_settings_mock.use_custom_playback_range = False

        config_mock = MagicMock()
        config_mock.find_setting_by_class.return_value = output_settings_mock

        mrq_job_mock = MagicMock()
        mrq_job_mock.get_configuration.return_value = config_mock
        mrq_job_mock.sequence = MagicMock()

        playback_range_mock = MagicMock()
        playback_range_mock.get_start_frame.return_value = 0
        playback_range_mock.get_end_frame.return_value = 100

        level_sequence_mock = MagicMock()
        level_sequence_mock.get_playback_range.return_value = playback_range_mock

        render_job = RenderUnrealOpenJob(file_path="", name="TestJob")
        render_job._mrq_job = mrq_job_mock

        parameter_values = [{"name": OpenJobParameterNames.FRAMES, "value": None}]

        with patch(
            "deadline.unreal_submitter.unreal_open_job.unreal_open_job.unreal.EditorAssetLibrary.load_asset",
            return_value=level_sequence_mock,
        ):
            # WHEN
            result = render_job._build_frames_parameter_value(parameter_values)

        # THEN
        assert result[0]["value"] == "0-100"

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object",
        return_value={"parameterDefinitions": []},
    )
    def test_returns_unchanged_when_level_sequence_not_found(self, get_template_object_mock):
        """Test that parameter values are unchanged when level sequence cannot be loaded."""
        # GIVEN
        config_mock = MagicMock()
        config_mock.find_setting_by_class.return_value = MagicMock()

        mrq_job_mock = MagicMock()
        mrq_job_mock.get_configuration.return_value = config_mock
        mrq_job_mock.sequence = MagicMock()

        render_job = RenderUnrealOpenJob(file_path="", name="TestJob")
        render_job._mrq_job = mrq_job_mock

        parameter_values = [{"name": OpenJobParameterNames.FRAMES, "value": None}]

        with patch(
            "deadline.unreal_submitter.unreal_open_job.unreal_open_job.unreal.EditorAssetLibrary.load_asset",
            return_value=None,
        ):
            # WHEN
            result = render_job._build_frames_parameter_value(parameter_values)

        # THEN
        assert result[0]["value"] is None

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object",
        return_value={"parameterDefinitions": []},
    )
    def test_handles_negative_frame_numbers(self, get_template_object_mock):
        """Test that negative frame numbers are handled correctly."""
        # GIVEN
        output_settings_mock = MagicMock()
        output_settings_mock.use_custom_playback_range = True
        output_settings_mock.custom_start_frame = -10
        output_settings_mock.custom_end_frame = 50

        config_mock = MagicMock()
        config_mock.find_setting_by_class.return_value = output_settings_mock

        mrq_job_mock = MagicMock()
        mrq_job_mock.get_configuration.return_value = config_mock
        mrq_job_mock.sequence = MagicMock()

        level_sequence_mock = MagicMock()

        render_job = RenderUnrealOpenJob(file_path="", name="TestJob")
        render_job._mrq_job = mrq_job_mock

        parameter_values = [{"name": OpenJobParameterNames.FRAMES, "value": None}]

        with patch(
            "deadline.unreal_submitter.unreal_open_job.unreal_open_job.unreal.EditorAssetLibrary.load_asset",
            return_value=level_sequence_mock,
        ):
            # WHEN
            result = render_job._build_frames_parameter_value(parameter_values)

        # THEN
        assert result[0]["value"] == "-10-50"
