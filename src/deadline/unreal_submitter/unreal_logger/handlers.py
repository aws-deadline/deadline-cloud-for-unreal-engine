import logging


class UnrealLogHandler(logging.Handler):

    def __init__(self):
        super().__init__()
        try:
            import unreal

            self._unreal_mod = unreal
            self.initialized = True
        except ModuleNotFoundError:
            self._unreal_mod = None
            self.initialized = False

    def emit(self, record):
        if not self._unreal_mod:
            return

        msg = self.format(record)

        if record.levelname == "WARNING":
            self._unreal_mod.log_warning(msg)
        elif record.levelname in ["ERROR", "CRITICAL"]:
            self._unreal_mod.log_error(msg)
        else:
            self._unreal_mod.log(msg)  # DEBUG, INFO and other custom levels
