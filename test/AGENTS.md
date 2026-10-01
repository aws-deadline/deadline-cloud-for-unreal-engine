# AGENTS.md — test

## Overview

Test suite for `deadline-cloud-for-unreal-engine` Python packages.

## Conventions

- Framework: pytest
- Mocking: `unittest.mock`
- The `unreal` module is never available in tests — always mock it
- All test files must start with `# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.`
- Shared fixtures in `conftest.py` or `fixtures.py`

## Test Packages

### deadline_adaptor_for_unreal
Tests for `src/deadline/unreal_adaptor`

- `unit/UnrealAdaptor/test_adaptor.py` — Main adaptor class (lifecycle, subprocess, IPC)
- `unit/UnrealClient/test_client.py` — In-UE client
- `unit/UnrealClient/step_handlers/` — Step handlers (render, custom script, frames-per-task)

### deadline_submitter_for_unreal
Tests for `src/deadline/unreal_submitter`

- `unit/conftest.py` — Shared fixtures (`aws_test_config` mocks boto3)
- `fixtures.py` — Test data factories (`f_job_template_default`, `f_step_template_default`)
- `unit/test_submitter.py` — Main submission flow
- `unit/test_job_submit_wrapper.py` — Deadline API submission wrapper
- `unit/test_unreal_open_job/` — OpenJD job template construction

**Pattern:** Use `fixtures.py` factories for test templates. Mock `boto3.Session.client` via `aws_test_config`.

### deadline_perforce_utils_for_unreal
Tests for `src/deadline/unreal_perforce_utils`

- `test_app.py` — Workspace setup, sync, cleanup
- `test_perforce.py` — Low-level Perforce operations (mocks `p4python`)
- `test_secret_manager.py` — AWS Secrets Manager credential retrieval

### deadline_logger_for_unreal
Tests for `src/deadline/unreal_logger`

- `test_logger.py` — `get_logger()` behavior with/without `unreal` module

### deadline_cmd_utils_for_unreal
Tests for `src/deadline/unreal_cmd_utils`

- `test_cmd_utils.py` — CLI argument parsing, UE special keys (`dpcvars`, `execcmds`)

### end_to_end
E2E tests against real AWS Deadline Cloud infrastructure

- `conftest.py` — AWS resource creation (farms, queues, fleets), UE discovery
- `test_create_job.py` — Job creation
- `test_worker_agent.py` — Worker agent behavior

**Important:** Requires valid AWS credentials. Slow and resource-intensive. Resource cleanup in fixtures.
