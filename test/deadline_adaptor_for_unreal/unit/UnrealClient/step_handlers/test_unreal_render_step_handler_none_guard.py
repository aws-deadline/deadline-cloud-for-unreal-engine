# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Tests for the None-guard in ``UnrealRenderStepHandler.get_frame_range``.

The adaptor has been observed crashing in production with
``AttributeError: 'NoneType' object has no attribute 'get_playback_range'``
when ``EditorAssetLibrary.load_asset`` returns ``None`` for the
``LevelSequence`` referenced by a job. The previous behaviour was to call
``level_sequence.get_playback_range()`` unconditionally, which crashes
when the loader returned None. These tests pin the defensive behaviour:
fall back to the MRQ ``output_settings`` custom range when it is
non-empty, and return ``(None, None)`` otherwise so the caller can
surface a clear error instead of crashing.
"""

import sys
import pytest
from unittest.mock import MagicMock, patch

# Ensure ``unreal`` is in ``sys.modules`` before the source module first
# imports it -- consistent with the other test files in this directory.
sys.modules.setdefault("unreal", MagicMock())


from deadline.unreal_adaptor.UnrealClient.step_handlers.unreal_render_step_handler import (  # noqa: E402
    UnrealRenderStepHandler,
)


@pytest.fixture()
def fresh_handler():
    UnrealRenderStepHandler.cached_frame_range_start = None
    UnrealRenderStepHandler.cached_frame_range_end = None
    return UnrealRenderStepHandler()


class TestGetFrameRangeNoneGuard:
    """When ``level_sequence`` is ``None`` and ``use_custom_playback_range`` is
    false, ``get_frame_range`` must NOT raise ``AttributeError``. It should
    fall back to the MRQ ``output_settings`` custom range, or return
    ``(None, None)`` if no usable range exists at all.
    """

    def test_none_sequence_falls_back_to_custom_range_when_non_empty(self, fresh_handler):
        output_settings = MagicMock()
        output_settings.use_custom_playback_range = False
        output_settings.custom_start_frame = 100
        output_settings.custom_end_frame = 200

        with patch(
            "deadline.unreal_adaptor.UnrealClient.step_handlers."
            "unreal_render_step_handler.logger.warning"
        ) as log_warning:
            start, end = fresh_handler.get_frame_range(output_settings, level_sequence=None)

        assert (start, end) == (100, 200)
        assert log_warning.called

    def test_none_sequence_returns_none_when_custom_range_empty(self, fresh_handler):
        output_settings = MagicMock()
        output_settings.use_custom_playback_range = False
        # Empty range: end <= start. No usable fallback.
        output_settings.custom_start_frame = 0
        output_settings.custom_end_frame = 0

        with patch(
            "deadline.unreal_adaptor.UnrealClient.step_handlers."
            "unreal_render_step_handler.logger.error"
        ) as log_error:
            start, end = fresh_handler.get_frame_range(output_settings, level_sequence=None)

        assert (start, end) == (None, None)
        assert log_error.called

    def test_use_custom_playback_range_overrides_none_sequence(self, fresh_handler):
        """If ``use_custom_playback_range`` is True, the level_sequence is
        never consulted -- None must be safe here."""
        output_settings = MagicMock()
        output_settings.use_custom_playback_range = True
        output_settings.custom_start_frame = 5
        output_settings.custom_end_frame = 25

        start, end = fresh_handler.get_frame_range(output_settings, level_sequence=None)
        assert (start, end) == (5, 25)

    def test_non_none_sequence_still_uses_sequence_playback_range(self, fresh_handler):
        """Regression guard: when a sequence loads, behaviour is unchanged."""
        output_settings = MagicMock()
        output_settings.use_custom_playback_range = False

        playback_range = MagicMock()
        playback_range.get_start_frame.return_value = 1
        playback_range.get_end_frame.return_value = 100
        level_sequence = MagicMock()
        level_sequence.get_playback_range.return_value = playback_range

        start, end = fresh_handler.get_frame_range(output_settings, level_sequence)
        assert (start, end) == (1, 100)
