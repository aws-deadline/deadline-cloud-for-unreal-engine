#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import logging
import sys

from openjd.adaptor_runtime import EntryPoint

from .adaptor import UnrealAdaptor

__all__ = ["main"]
_logger = logging.getLogger(__name__)


def main():
    _logger.info("About to start the UnrealAdaptor")

    package_name = vars(sys.modules[__name__])["__package__"]
    if not package_name:
        raise RuntimeError(f"Must be run as a module. Do not run {__file__} directly")

    try:
        EntryPoint(UnrealAdaptor).start()
    except Exception as e:
        _logger.error(f"Entrypoint failed: {e}")
        sys.exit(1)

    _logger.info("Done UnrealAdaptor main")


if __name__ == "__main__":
    main()
