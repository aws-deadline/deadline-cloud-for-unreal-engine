#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import logging

from deadline.unreal_logger.handlers import UnrealLogHandler

try:
    import unreal  # noqa: F401

    UNREAL_INITIALIZED = True
except ModuleNotFoundError:
    unreal = None
    UNREAL_INITIALIZED = False


UNREAL_HANDLER_ADDED = False


def add_unreal_handler(logger: logging.Logger) -> None:
    """
    Attach :class:`deadline.unreal_logger.handlers.UnrealLogHandler` to given logger

    :param logger: Logger instance
    :type logger: logging.Logger
    """

    unreal_log_handler = UnrealLogHandler(unreal)
    unreal_log_handler.setLevel(logging.DEBUG)
    logger.addHandler(unreal_log_handler)


def get_logger() -> logging.Logger:
    """
    Returns an instance of logging.Handler.
    Attach handler :class:`deadline.unreal_logger.handlers.UnrealLogHandler` if unreal module is
    available for the first time
    """

    unreal_logger = logging.getLogger("unreal_logger")
    unreal_logger.setLevel(logging.DEBUG)

    global UNREAL_HANDLER_ADDED

    # can be called outside UE so need to check before adding UE specific handler
    if not UNREAL_HANDLER_ADDED and UNREAL_INITIALIZED:
        add_unreal_handler(unreal_logger)
        UNREAL_HANDLER_ADDED = True

    return unreal_logger
