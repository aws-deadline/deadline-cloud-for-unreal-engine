# AGENTS.md — unreal_adaptor

## Overview

Worker-side adaptor that launches and controls Unreal Engine on Deadline Cloud render nodes. Built on the `openjd-adaptor-runtime` framework.

## Structure

- `UnrealAdaptor/` — Server-side adaptor
  - `adaptor.py` — Main `UnrealAdaptor` class (extends `openjd.adaptor_runtime.adaptors.Adaptor`); manages UE subprocess lifecycle
  - `common.py` — Shared utilities and data validation
  - `__main__.py` — CLI entry point (`unreal-engine-openjd`)
  - `schemas/` — JSON schemas for init/run data validation
- `UnrealClient/` — Client-side code that runs inside the UE process
  - `unreal_client.py` — Communicates with the adaptor server via IPC
  - `step_handlers/` — Per-step-type handlers (render, custom script)

## Important context

- The adaptor spawns an Unreal Engine subprocess and communicates with it via `openjd` IPC (AdaptorServer/ActionsQueue)
- `UnrealClient` code runs inside the UE process; `UnrealAdaptor` code runs outside it
- Logging differs by side:
  - `UnrealAdaptor/` (runs outside UE): use `import logging` / `logging.getLogger(__name__)`
  - `UnrealClient/` (runs inside UE): use `from deadline.unreal_logger import get_logger` / `get_logger(__name__)`
- JSON schemas in `schemas/` validate data passed between adaptor and client

