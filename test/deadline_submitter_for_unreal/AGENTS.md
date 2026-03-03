# AGENTS.md — deadline_submitter_for_unreal tests

## Overview

Unit tests for `src/deadline/unreal_submitter`. The `unreal` module must be mocked in all tests.

## Structure

- `unit/conftest.py` — Shared fixtures (e.g. `aws_test_config` mocks boto3 Deadline client)
- `fixtures.py` — Reusable test data factories (`f_job_template_default`, `f_step_template_default`, etc.)
- `unit/test_submitter.py` — Tests for the main submission flow
- `unit/test_job_submit_wrapper.py` — Tests for the Deadline API submission wrapper
- `unit/test_common.py` — Tests for shared utilities
- `unit/test_settings.py` — Tests for submission settings
- `unit/test_python397_patch.py` — Tests for Python 3.9.7 compatibility patches
- `unit/test_unreal_open_job/` — Tests for OpenJD job template construction (job, step, environment, entity, host requirements, parameter consistency, shared settings)

## Key patterns

- Use `fixtures.py` data factories when constructing test job/step templates
- Mock `boto3.Session.client` via the `aws_test_config` fixture for any test that touches AWS APIs
