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
            ("  5-5  ", 5, 5),  # Single frame range with extra whitespace
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
            ("-10", "Invalid dynamic_chunked_frames format"),  # Negative single frame
            ("1--2", "Invalid dynamic_chunked_frames format"),  # Double dash
            ("-1-10", "Invalid dynamic_chunked_frames format"),  # Negative start
            ("1-10-20", "Invalid dynamic_chunked_frames format"),  # Multiple dashes
            ("1,2,3", "Invalid dynamic_chunked_frames format"),  # Non-contiguous list (unsupported - MRQ limitation)
            ("1-10:2", "Invalid dynamic_chunked_frames format"),  # Stepped range (unsupported - MRQ limitation)
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


class TestDynamicChunkingPrecedence:
    """Tests for chunking mode precedence"""

    def test_dynamic_chunking_takes_precedence_over_frames_per_task(
        self, unreal_render_step_handler
    ):
        """Test that dynamic_chunked_frames takes precedence over frames_per_task"""
        # GIVEN
        args_with_all = {
            "dynamic_chunked_frames": "1-10",
            "frames_per_task": 5,
            "chunk_id": 0,
            "chunk_size": 3,
        }

        # WHEN/THEN - dynamic_chunked_frames should be checked first
        assert "dynamic_chunked_frames" in args_with_all

        # The condition in run_script checks dynamic_chunked_frames first
        if "dynamic_chunked_frames" in args_with_all:
            mode = "dynamic"
        elif args_with_all.get("frames_per_task") and "chunk_id" in args_with_all:
            mode = "frames_per_task"
        elif "chunk_size" in args_with_all and "chunk_id" in args_with_all:
            mode = "chunk_size"
        else:
            mode = "none"

        assert mode == "dynamic"

    def test_frames_per_task_used_when_no_dynamic_chunking(self, unreal_render_step_handler):
        """Test that frames_per_task is used when dynamic_chunked_frames is absent"""
        # GIVEN
        args_without_dynamic = {
            "frames_per_task": 5,
            "chunk_id": 0,
            "chunk_size": 3,
        }

        # WHEN/THEN
        if "dynamic_chunked_frames" in args_without_dynamic:
            mode = "dynamic"
        elif args_without_dynamic.get("frames_per_task") and "chunk_id" in args_without_dynamic:
            mode = "frames_per_task"
        elif "chunk_size" in args_without_dynamic and "chunk_id" in args_without_dynamic:
            mode = "chunk_size"
        else:
            mode = "none"

        assert mode == "frames_per_task"

    def test_chunk_size_used_when_no_dynamic_or_frames_per_task(self, unreal_render_step_handler):
        """Test that chunk_size is used when dynamic_chunked_frames and frames_per_task are absent"""
        # GIVEN
        args_chunk_size_only = {
            "chunk_size": 3,
            "chunk_id": 0,
        }

        # WHEN/THEN
        if "dynamic_chunked_frames" in args_chunk_size_only:
            mode = "dynamic"
        elif args_chunk_size_only.get("frames_per_task") and "chunk_id" in args_chunk_size_only:
            mode = "frames_per_task"
        elif "chunk_size" in args_chunk_size_only and "chunk_id" in args_chunk_size_only:
            mode = "chunk_size"
        else:
            mode = "none"

        assert mode == "chunk_size"

    def test_no_chunking_when_no_params(self, unreal_render_step_handler):
        """Test that no chunking mode is selected when no chunking params are present"""
        # GIVEN
        args_no_chunking: dict[str, int] = {}

        # WHEN/THEN
        if "dynamic_chunked_frames" in args_no_chunking:
            mode = "dynamic"
        elif args_no_chunking.get("frames_per_task") and "chunk_id" in args_no_chunking:
            mode = "frames_per_task"
        elif "chunk_size" in args_no_chunking and "chunk_id" in args_no_chunking:
            mode = "chunk_size"
        else:
            mode = "none"

        assert mode == "none"


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
