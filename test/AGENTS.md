# AGENTS.md — test

## Overview

Test suite for the `deadline-cloud-for-unreal-engine` Python packages. Organized by source package with unit and end-to-end test directories.

## Running tests

- Run all tests: `pytest` from repo root
- Run a specific suite: `pytest test/deadline_submitter_for_unreal/`
- Run a single test: `pytest test/path/to/test_file.py::test_name`
- Coverage threshold: 65% (enforced in `pyproject.toml`)
- Coverage report: `build/coverage/`

## Structure

- `deadline_submitter_for_unreal/` — Tests for `src/deadline/unreal_submitter`
- `deadline_adaptor_for_unreal/` — Tests for `src/deadline/unreal_adaptor`
- `deadline_perforce_utils_for_unreal/` — Tests for `src/deadline/unreal_perforce_utils`
- `deadline_logger_for_unreal/` — Tests for `src/deadline/unreal_logger`
- `deadline_cmd_utils_for_unreal/` — Tests for `src/deadline/unreal_cmd_utils`
- `end_to_end/` — E2E tests that run against real Deadline Cloud infrastructure
- `test_copyright_headers.py` — Validates all source files have the required Amazon copyright header

## Conventions

- Framework: pytest
- Mocking: `unittest.mock` (`patch`, `MagicMock`)
- The `unreal` module is never available in tests — always mock it
- All test files must start with `# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.`
- Shared fixtures go in `conftest.py` or `fixtures.py` within each test package
