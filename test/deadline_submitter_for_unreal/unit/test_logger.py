import pytest
import logging
from typing import Type
from unittest.mock import Mock, MagicMock, patch

from deadline.unreal_submitter.unreal_logger import get_logger
from deadline.unreal_submitter.unreal_logger.handlers import UnrealLogHandler


class TestUnrealLogHandler:

    @pytest.mark.parametrize(
        "unreal_module, expected_initialized", [(MagicMock(), True), (None, False)]
    )
    def test_initialization(self, unreal_module, expected_initialized: bool):
        # GIVEN
        import sys

        current_mod = sys.modules["unreal"]
        sys.modules["unreal"] = unreal_module

        # WHEN
        handler = UnrealLogHandler()

        # THEN
        assert handler.initialized == expected_initialized

        sys.modules["unreal"] = current_mod

    @pytest.mark.parametrize(
        "unreal_module, log_level, expected_method",
        [
            (MagicMock(), "WARNING", "log_warning"),
            (MagicMock(), "ERROR", "log_error"),
            (MagicMock(), "CRITICAL", "log_error"),
            (MagicMock(), "INFO", "log"),
            (MagicMock(), "DEBUG", "log"),
            (MagicMock(), "CUSTOM_LEVEL", "log"),
        ],
    )
    @patch("logging.Handler.format")
    def test_emit(
        self, mock_format: Mock, unreal_module: MagicMock, log_level: str, expected_method: str
    ):
        # GIVEN
        import sys

        sys.modules["unreal"] = unreal_module

        setattr(unreal_module, expected_method, MagicMock())

        record = MagicMock()
        record.levelname = log_level
        mock_format.return_value = record

        handler = UnrealLogHandler()

        # WHEN
        handler.emit(record)

        # THEN
        mocked_method: MagicMock = getattr(unreal_module, expected_method)
        mocked_method.assert_called_once_with(record)


class TestUnrealLogger:

    @pytest.mark.parametrize(
        "unreal_module, expected_handler",
        [(MagicMock(), UnrealLogHandler), (None, logging.StreamHandler)],
    )
    def test_get_logger(self, unreal_module, expected_handler: Type[logging.Handler]):
        # GIVEN
        import sys

        current = sys.modules.get("unreal")

        if unreal_module is None:
            del sys.modules["unreal"]
        else:
            sys.modules["unreal"] = unreal_module

        # WHEN
        logger = get_logger()

        # THEN
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], expected_handler)

        if current:
            sys.modules["unreal"] = current  # Remove None from sys.modules
