# AGENTS.md — unreal_logger

## Overview

Logging bridge between Python's `logging` module and Unreal Engine's log system. Provides `get_logger()` which auto-detects whether it's running inside UE and attaches the appropriate handler.

## Key files

- `logger.py` — `get_logger()` factory; returns a logger with UE handler (if inside UE) or console handler
- `handlers.py` — `UnrealLogHandler` that forwards Python log records to `unreal.log()`

## Important context

- The `unreal` module import is guarded with try/except — this package works both inside and outside UE
- `get_logger()` always returns a logger named `"unreal_logger"` (not `__name__`), so all callers share one logger — this means you lose per-module log traceability
- Use `get_logger()` in code that runs inside UE or in simple packages (submitter, perforce_utils, UnrealClient)
- Use standard `logging.getLogger(__name__)` when per-module logger names matter for debugging (e.g. `UnrealAdaptor/` which runs outside UE as a multi-module process)

