import pytest
from types import ModuleType
from unittest.mock import Mock, MagicMock, patch

from deadline.unreal_logger import get_logger
from deadline.unreal_logger.handlers import UnrealLogHandler


class TestUnrealLogHandler:

    @pytest.mark.parametrize(
        "log_level, expected_method",
        [
            ("WARNING", "log_warning"),
            ("ERROR", "log_error"),
            ("CRITICAL", "log_error"),
            ("INFO", "log"),
            ("DEBUG", "log"),
            ("CUSTOM_LEVEL", "log"),
        ],
    )
    @patch("logging.Handler.format")
    def test_emit(self, mock_format: Mock, log_level: str, expected_method: str):
        # GIVEN
        unreal_module = MagicMock()
        setattr(unreal_module, expected_method, MagicMock())

        record = MagicMock()
        record.levelname = log_level
        mock_format.return_value = record

        handler = UnrealLogHandler(unreal_module)

        # WHEN
        handler.emit(record)

        # THEN
        mocked_method: MagicMock = getattr(unreal_module, expected_method)
        mocked_method.assert_called_once_with(record)

    def test_emit_with_invalid_unreal_module(self):
        # GIVEN
        unreal_module = Mock(return_value=None)
        handler = UnrealLogHandler(unreal_module)

        # WHEN
        handler.emit(MagicMock())

        # THEN
        assert unreal_module.call_count == 0


class TestUnrealLogger:

    def test_get_logger(
        self,
    ):
        # GIVEN
        import sys

        current = sys.modules.get("unreal")
        sys.modules["unreal"] = MagicMock()

        # WHEN
        logger = get_logger()

        # THEN
        assert len(logger.handlers) == 1

        if isinstance(current, ModuleType):
            sys.modules["unreal"] = current  # Remove MagicMock from sys.modules
