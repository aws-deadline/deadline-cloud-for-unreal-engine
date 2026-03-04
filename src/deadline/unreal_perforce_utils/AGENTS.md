# AGENTS.md — unreal_perforce_utils

## Overview

Perforce workspace management for Deadline Cloud Unreal Engine jobs. Handles workspace creation, syncing, and source control operations on render workers.

## Key files

- `app.py` — Main application logic: workspace setup, sync, and cleanup
- `perforce.py` — Low-level Perforce operations via `p4python`
- `secret_manager.py` — Retrieves Perforce credentials from AWS Secrets Manager
- `unreal_source_control.py` — Unreal-specific source control operations
- `cli.py` — CLI entry point (`unreal-engine-p4-utils`)
- `exceptions.py` — Custom exception types

## Important context

- Workspace names follow the pattern: `<USERNAME>_<HOST>_<PROJECT>` (with optional `_<WORKER_ID>`)
- Uses `p4python` (not the `p4` CLI) for Perforce operations
- Credentials are fetched from AWS Secrets Manager at runtime
- This code runs on worker nodes, not inside Unreal Engine

