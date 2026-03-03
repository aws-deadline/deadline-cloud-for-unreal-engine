# AGENTS.md — deadline_adaptor_for_unreal tests

## Overview

Unit tests for `src/deadline/unreal_adaptor`.

## Structure

- `unit/UnrealAdaptor/test_adaptor.py` — Tests for the main `UnrealAdaptor` class (lifecycle, subprocess management, IPC)
- `unit/UnrealClient/test_client.py` — Tests for the in-UE client
- `unit/UnrealClient/step_handlers/` — Tests for step handlers (render, custom script, frames-per-task)
  - `custom_scripts/` — Test data for custom script handler tests
