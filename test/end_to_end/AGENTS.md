# AGENTS.md — end_to_end tests

## Overview

End-to-end tests that run against real AWS Deadline Cloud infrastructure. These tests create actual jobs, farms, queues, and fleets.

## Key files

- `conftest.py` — Extensive fixture setup: AWS resource creation (farms, queues, fleets), Unreal Engine discovery, logging configuration. Uses `boto3` directly.
- `test_create_job.py` — Tests for job creation
- `test_worker_agent.py` — Tests for worker agent behavior

## Important context

- These tests require valid AWS credentials and a real Deadline Cloud environment
- They are slow and resource-intensive — not run as part of the default unit tests
- The `conftest.py` adds the repo root to `sys.path` and imports from `scripts/build_plugin.py`
- Resource cleanup is handled by fixtures; check teardown logic before modifying
