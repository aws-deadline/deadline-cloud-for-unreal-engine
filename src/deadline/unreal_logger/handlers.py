#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import logging


class UnrealLogHandler(logging.Handler):
    """
    Logging handler which writes records using unreal.log methods
    """

    def __init__(self, unreal_module):
        super().__init__()
        self._unreal_mod = unreal_module

    def emit(self, record):
        """
        Log the specified logging record.
        Calls the unreal log method corresponding to the record level name:
            - WARNING - unreal.log_warning
            - ERROR, CRITICAL - unreal.log_error
            - DEBUG, INFO and other custom levels - unreal.log
        """

        if self._unreal_mod is None:
            return

        msg = self.format(record)

        if record.levelname == "WARNING":
            self._unreal_mod.log_warning(msg)
        elif record.levelname in ["ERROR", "CRITICAL"]:
            self._unreal_mod.log_error(msg)
        else:
            self._unreal_mod.log(msg)  # DEBUG, INFO and other custom levels
