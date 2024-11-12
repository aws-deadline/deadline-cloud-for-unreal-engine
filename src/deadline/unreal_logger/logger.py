#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import logging


from deadline.unreal_logger.handlers import UnrealLogHandler


def get_logger() -> logging.Logger:
    """
    Returns an instance of logging.Handler.
    Attach handler :class:`deadline.unreal_logger.handlers.UnrealLogHandler` if unreal module is
    available
    """

    unreal_logger = logging.getLogger("unreal_logger")
    print(id(unreal_logger))
    unreal_logger.setLevel(logging.DEBUG)

    try:
        import unreal  # noqa: F401
    except ModuleNotFoundError:
        unreal = None

    # can be called outside UE so need to check before adding UE specific handler
    if unreal is not None:
        unreal_log_handler = UnrealLogHandler(unreal)
        unreal_log_handler.setLevel(logging.DEBUG)

        # If we found existed UnrealLogHandler, skip adding duplicate
        existed_unreal_log_handler = next(
            (h for h in unreal_logger.handlers if isinstance(h, UnrealLogHandler)), None
        )
        if not existed_unreal_log_handler:
            unreal_logger.addHandler(unreal_log_handler)

    return unreal_logger
