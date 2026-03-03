# AGENTS.md — deadline_perforce_utils_for_unreal tests

## Overview

Unit tests for `src/deadline/unreal_perforce_utils`.

## Key files

- `test_app.py` — Tests for workspace setup, sync, and cleanup logic
- `test_perforce.py` — Tests for low-level Perforce operations (mocks `p4python`)
- `test_cli.py` — Tests for the CLI entry point
- `test_secret_manager.py` — Tests for AWS Secrets Manager credential retrieval
- `test_unreal_source_control.py` — Tests for Unreal-specific source control operations
