import pytest
from unittest.mock import Mock, MagicMock, patch

from deadline.unreal_logger import get_logger
from deadline.unreal_logger.logger import add_unreal_handler
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

    @pytest.mark.parametrize(
        "unreal_initialized, handler_added, add_handler_calls",
        [
            (True, True, 0),
            (False, True, 0),
            (False, False, 0),
            (True, False, 1),
        ],
    )
    @patch("deadline.unreal_logger.logger.add_unreal_handler")
    def test_get_logger(
        self,
        add_unreal_handler_mock: Mock,
        unreal_initialized: bool,
        handler_added: bool,
        add_handler_calls: int,
    ):
        # GIVEN
        with patch("deadline.unreal_logger.logger.UNREAL_INITIALIZED", unreal_initialized):
            with patch("deadline.unreal_logger.logger.UNREAL_HANDLER_ADDED", handler_added):
                # WHEN
                get_logger()

        # THEN
        assert add_unreal_handler_mock.call_count == add_handler_calls

    def test_add_unreal_handler(self):
        # GIVEN
        logger = get_logger()
        logger.handlers.clear()

        # WHEN
        add_unreal_handler(logger)

        # THEN
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], UnrealLogHandler)
