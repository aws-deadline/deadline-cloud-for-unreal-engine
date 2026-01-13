# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import pytest

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_dynamic_chunking import (
    DynamicChunkingHelper,
)
from deadline.unreal_submitter.exceptions import SubmitterInputValidationError


class TestDynamicChunkingHelper:
    """Tests for the DynamicChunkingHelper class."""

    @pytest.mark.parametrize(
        "range_constraint",
        [
            "CONTIGUOUS",
            "NONCONTIGUOUS",
        ],
    )
    def test_validate_range_constraint_valid_values(self, range_constraint):
        """Test that valid RangeConstraint values pass validation."""
        # WHEN / THEN - should not raise
        DynamicChunkingHelper._validate_range_constraint(range_constraint)

    @pytest.mark.parametrize(
        "invalid_value",
        [
            "contiguous",  # lowercase
            "CONTIGOUS",  # typo
            "noncontiguous",  # lowercase
            "INVALID",
            "",
            "BOTH",
            "RANDOM",
        ],
    )
    def test_validate_range_constraint_invalid_values(self, invalid_value):
        """Test that invalid RangeConstraint values raise SubmitterInputValidationError."""
        # WHEN / THEN
        with pytest.raises(SubmitterInputValidationError) as exc_info:
            DynamicChunkingHelper._validate_range_constraint(invalid_value)

        # Verify error message contains helpful information
        assert f'Invalid RangeConstraint value "{invalid_value}"' in str(exc_info.value)
        assert "CONTIGUOUS" in str(exc_info.value)
        assert "NONCONTIGUOUS" in str(exc_info.value)


class TestValidateSingleChunkParameter:
    """Tests for the validate_single_chunk_parameter_per_step function."""

    def test_validate_single_chunk_parameter_per_step_no_chunk_params(self):
        """Test that templates with no CHUNK[INT] parameters pass validation."""
        # GIVEN - template with no CHUNK parameters
        step_template = {
            "parameterSpace": {
                "taskParameterDefinitions": [
                    {"name": "ChunkId", "type": "INT", "range": [0, 1, 2]},
                    {"name": "OutputPath", "type": "PATH", "range": ["/output"]},
                ]
            }
        }

        # WHEN / THEN - should not raise
        DynamicChunkingHelper._validate_single_chunk_parameter_per_step(step_template)

    def test_validate_single_chunk_parameter_per_step_one_chunk_param(self):
        """Test that templates with exactly one CHUNK[INT] parameter pass validation."""
        # GIVEN - template with one CHUNK[INT] parameter
        step_template = {
            "parameterSpace": {
                "taskParameterDefinitions": [
                    {
                        "name": "DynamicChunking",
                        "type": "CHUNK[INT]",
                        "range": "{{Param.Frames}}",
                        "chunks": {"defaultTaskCount": "{{Param.ChunkSize}}"},
                    },
                    {"name": "OutputPath", "type": "PATH", "range": ["/output"]},
                ]
            }
        }

        # WHEN / THEN - should not raise
        DynamicChunkingHelper._validate_single_chunk_parameter_per_step(step_template)

    def test_validate_single_chunk_parameter_per_step_multiple_chunk_params(self):
        """Test that templates with multiple CHUNK[INT] parameters raise error."""
        # GIVEN - template with multiple CHUNK[INT] parameters
        step_template = {
            "parameterSpace": {
                "taskParameterDefinitions": [
                    {
                        "name": "DynamicChunking1",
                        "type": "CHUNK[INT]",
                        "range": "{{Param.Frames}}",
                    },
                    {
                        "name": "DynamicChunking2",
                        "type": "CHUNK[INT]",
                        "range": "{{Param.Frames2}}",
                    },
                    {"name": "OutputPath", "type": "PATH", "range": ["/output"]},
                ]
            }
        }

        # WHEN / THEN
        with pytest.raises(SubmitterInputValidationError) as exc_info:
            DynamicChunkingHelper._validate_single_chunk_parameter_per_step(step_template)

        # Verify error message contains helpful information
        assert "2 CHUNK[INT] task parameters" in str(exc_info.value)
        assert "DynamicChunking1" in str(exc_info.value)
        assert "DynamicChunking2" in str(exc_info.value)
        assert "only one CHUNK[INT] parameter is allowed per step" in str(exc_info.value)

    def test_validate_single_chunk_parameter_per_step_empty_template(self):
        """Test that empty templates pass validation."""
        # GIVEN - empty template
        step_template = {}

        # WHEN / THEN - should not raise
        DynamicChunkingHelper._validate_single_chunk_parameter_per_step(step_template)

    def test_validate_single_chunk_parameter_per_step_malformed_template(self):
        """Test that malformed templates are handled gracefully."""
        # GIVEN - malformed template (None)
        step_template = None

        # WHEN / THEN - should not raise (graceful handling)
        DynamicChunkingHelper._validate_single_chunk_parameter_per_step(step_template)


class TestValidateFramesParameter:
    """Tests for the validate_frames_parameter function."""

    @pytest.mark.parametrize(
        "valid_frames",
        [
            # Single non-negative integers
            "1",
            "0",
            "100",
            "999",
            # Simple ranges
            "1-100",
            "0-50",
            "10-20",
            "0-0",  # single frame as range
            # Ranges with step
            "1-100:2",
            "0-50:5",
            "1-1000:10",
            "0-100:1",
            # Comma-separated lists (IntRangeList)
            "1,2,3",
            "1,5,10,15",
            "1-10,15,20-30",
            "1-10:2,15,20-30:5",
            # Complex mixed formats
            "1-10,15,20-30,35,40-50:2",
            "0,5-10,15,20-30:2",
            "1,2,3,4,5",
        ],
    )
    def test_validate_frames_parameter_valid_values(self, valid_frames):
        """Test that valid Frames parameter values pass validation."""
        # WHEN / THEN - should not raise
        DynamicChunkingHelper.validate_frames_parameter(valid_frames)

    @pytest.mark.parametrize(
        "empty_frames",
        [
            "",
            "   ",
            None,
        ],
    )
    def test_validate_frames_parameter_empty_values_raise_error(self, empty_frames):
        """Test that empty Frames parameter values raise SubmitterInputValidationError."""
        # WHEN / THEN - should raise (empty is not valid, use '0' for all frames)
        with pytest.raises(SubmitterInputValidationError) as exc_info:
            DynamicChunkingHelper.validate_frames_parameter(empty_frames)

        assert "Frames parameter is required" in str(exc_info.value)

    @pytest.mark.parametrize(
        "invalid_frames",
        [
            "abc",  # non-numeric
            "1-",  # incomplete range
            "-",  # just a dash
            "1--",  # double dash at end
            "1-10-20",  # invalid triple range
            "1:2",  # step without range
            "1-10:",  # step without value
            "1-10:abc",  # non-numeric step
            ",1,2",  # leading comma
            "1,2,",  # trailing comma
            "1,,2",  # double comma
            "1 2 3",  # spaces instead of commas
            "1..10",  # double dots
            "1-10;20-30",  # semicolon instead of comma
            "a-z",  # letters
            "1.5-10.5",  # floats
            "-1",  # negative single integer
            "-100",  # negative single integer
            "-10-10",  # negative start
            "-100--50",  # negative to negative
            "-10-10:2",  # negative with step
        ],
    )
    def test_validate_frames_parameter_invalid_values(self, invalid_frames):
        """Test that invalid Frames parameter values raise SubmitterInputValidationError."""
        # WHEN / THEN
        with pytest.raises(SubmitterInputValidationError) as exc_info:
            DynamicChunkingHelper.validate_frames_parameter(invalid_frames)

        # Verify error message contains helpful information
        assert f'Invalid Frames parameter value "{invalid_frames}"' in str(exc_info.value)
        assert "IntRangeList" in str(exc_info.value)
        assert "IntRangeExpr" in str(exc_info.value)


class TestSubstituteChunkParameterValues:
    """Tests for the _substitute_chunk_parameter_values method in UnrealOpenJobStep."""

    def test_substitute_range_constraint_from_job_parameter(self):
        """Test that rangeConstraint template expression is substituted with job parameter value."""
        import sys
        from unittest.mock import MagicMock

        # Mock unreal module
        unreal_mock = MagicMock()
        sys.modules["unreal"] = unreal_mock

        from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step import (
            UnrealOpenJobStep,
        )

        # GIVEN - a step with a job that has RangeConstraint parameter
        mock_job = MagicMock()
        mock_range_constraint_param = MagicMock()
        mock_range_constraint_param.value = "NONCONTIGUOUS"
        mock_job._find_extra_parameter.return_value = mock_range_constraint_param

        step = UnrealOpenJobStep(file_path="")
        step._open_job = mock_job

        yaml_param = {
            "name": "DynamicChunking",
            "type": "CHUNK[INT]",
            "range": "{{Param.Frames}}",
            "chunks": {
                "defaultTaskCount": "{{Param.ChunkSize}}",
                "targetRuntimeSeconds": "{{Param.TargetRuntimeSeconds}}",
                "rangeConstraint": "{{Param.RangeConstraint}}",
            },
        }

        # WHEN
        result = step._substitute_chunk_parameter_values(yaml_param)

        # THEN
        assert result["chunks"]["rangeConstraint"] == "NONCONTIGUOUS"
        # Verify template expressions for other fields are preserved
        assert result["chunks"]["defaultTaskCount"] == "{{Param.ChunkSize}}"
        assert result["chunks"]["targetRuntimeSeconds"] == "{{Param.TargetRuntimeSeconds}}"
        # Verify original dict is not modified
        assert yaml_param["chunks"]["rangeConstraint"] == "{{Param.RangeConstraint}}"

    def test_substitute_range_constraint_defaults_to_contiguous_when_no_job(self):
        """Test that rangeConstraint defaults to CONTIGUOUS when no job is available."""
        import sys
        from unittest.mock import MagicMock

        # Mock unreal module
        unreal_mock = MagicMock()
        sys.modules["unreal"] = unreal_mock

        from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step import (
            UnrealOpenJobStep,
        )

        # GIVEN - a step without a job
        step = UnrealOpenJobStep(file_path="")
        step._open_job = None

        yaml_param = {
            "name": "DynamicChunking",
            "type": "CHUNK[INT]",
            "range": "{{Param.Frames}}",
            "chunks": {
                "defaultTaskCount": "{{Param.ChunkSize}}",
                "rangeConstraint": "{{Param.RangeConstraint}}",
            },
        }

        # WHEN
        result = step._substitute_chunk_parameter_values(yaml_param)

        # THEN
        assert result["chunks"]["rangeConstraint"] == "CONTIGUOUS"

    def test_substitute_range_constraint_preserves_literal_value(self):
        """Test that literal rangeConstraint values are preserved."""
        import sys
        from unittest.mock import MagicMock

        # Mock unreal module
        unreal_mock = MagicMock()
        sys.modules["unreal"] = unreal_mock

        from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step import (
            UnrealOpenJobStep,
        )

        # GIVEN - a step with literal rangeConstraint
        step = UnrealOpenJobStep(file_path="")
        step._open_job = None

        yaml_param = {
            "name": "DynamicChunking",
            "type": "CHUNK[INT]",
            "range": "{{Param.Frames}}",
            "chunks": {
                "defaultTaskCount": "{{Param.ChunkSize}}",
                "rangeConstraint": "NONCONTIGUOUS",  # literal value
            },
        }

        # WHEN
        result = step._substitute_chunk_parameter_values(yaml_param)

        # THEN - literal value should be preserved
        assert result["chunks"]["rangeConstraint"] == "NONCONTIGUOUS"

    def test_substitute_handles_missing_chunks_config(self):
        """Test that parameters without chunks config are handled gracefully."""
        import sys
        from unittest.mock import MagicMock

        # Mock unreal module
        unreal_mock = MagicMock()
        sys.modules["unreal"] = unreal_mock

        from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step import (
            UnrealOpenJobStep,
        )

        # GIVEN - a parameter without chunks config
        step = UnrealOpenJobStep(file_path="")
        step._open_job = None

        yaml_param = {
            "name": "ChunkId",
            "type": "INT",
            "range": [0, 1, 2],
        }

        # WHEN
        result = step._substitute_chunk_parameter_values(yaml_param)

        # THEN - parameter should be returned unchanged
        assert result == yaml_param
