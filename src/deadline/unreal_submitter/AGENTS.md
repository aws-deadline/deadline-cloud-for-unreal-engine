# AGENTS.md — unreal_submitter

## Overview

Handles job submission from the Unreal Editor to AWS Deadline Cloud. Runs inside UE's embedded Python interpreter.

## Key files

- `submitter.py` — Main entry point; orchestrates job creation and submission in a background thread
- `common.py` — Shared utilities and data structures
- `settings.py` — Submission settings/defaults
- `exceptions.py` — Custom exception types (notably `UserException` for user-facing errors)
- `job_submit_wrapper.py` — Wrapper around the deadline client submission API
- `unreal_dependency_collector.py` — Collects asset dependencies for job attachments
- `unreal_open_job/` — OpenJD job template construction (job, steps, environments, host requirements, parameter consistency)

## Important context

- This code runs inside Unreal Engine's Python environment — the `unreal` module is always available here
- Uses `deadline.client.api` for submission and telemetry
- Telemetry is collected by default; users can opt out via `DEADLINE_CLOUD_TELEMETRY_OPT_OUT=true`
- The `unreal_open_job` subpackage builds OpenJD job bundles programmatically — changes here affect the job structure sent to Deadline Cloud


## UE Plugin Locations

Three plugin directories matter for `get_plugins_references()`:

- **Project** (`<Project>/Plugins/`): Project level plugins. Scanned and uploaded.
- **Engine stock** (`<Engine>/Engine/Plugins/`): Built-in plugins. Shipped with UE — skipped.
- **FAB/Marketplace installed** (`<Engine>/Engine/Plugins/Marketplace/`): Fab/Marketplace/Launcher-installed plugins. Uploaded and copied into the worker's engine dir by the auto-injected `InstallMarketplacePlugins` environment.
