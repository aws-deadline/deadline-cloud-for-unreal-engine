import os
import json
import logging
import logging.config
from typing import Optional

from deadline.unreal_submitter.unreal_logger.handlers import UnrealLogHandler


with open(f"{os.path.dirname(__file__)}/config.json", "r") as f:
    LOGGER_CONFIG = json.load(f)


def get_logger() -> logging.Logger:

    logging.config.dictConfig(LOGGER_CONFIG)

    unreal_logger = logging.getLogger("unreal_logger")

    unreal_log_handler: Optional[UnrealLogHandler] = next(
        (h for h in unreal_logger.handlers if isinstance(h, UnrealLogHandler)), None
    )
    stdout_log_handler: Optional[logging.StreamHandler] = next(
        (h for h in unreal_logger.handlers if isinstance(h, logging.StreamHandler)), None
    )

    if unreal_log_handler is not None:
        if unreal_log_handler.initialized and stdout_log_handler is not None:
            unreal_logger.removeHandler(stdout_log_handler)
        else:
            unreal_logger.removeHandler(unreal_log_handler)

    return unreal_logger
