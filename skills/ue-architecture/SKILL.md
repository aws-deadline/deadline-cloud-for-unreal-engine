---
name: ue-architecture
description: Architecture and design knowledge for deadline-cloud-for-unreal-engine. Use when understanding project structure, component relationships, data flow between submitter/adaptor/plugin, designing new features, or reviewing code for architectural correctness.
tags: [skill, unreal, deadline-cloud, architecture, design]
---

# UE Integration Architecture

## Overview

Architecture reference for `deadline-cloud-for-unreal-engine` — a C++ and Python integration enabling Unreal Movie Render Queue job submission to AWS Deadline Cloud and worker-side rendering via OpenJD adaptors.

## Usage

Use this skill when:
- Understanding how components interact
- Designing a new feature or reviewing a design
- Reviewing code for architectural correctness
- Deciding where new code should live
- Understanding the submission or rendering data flow

## Core Concepts

### High-Level Architecture

```
┌─────────────────────── SUBMITTER WORKSTATION ───────────────────────┐
│                                                                     │
│  Unreal Engine Editor                                               │
│  ├── C++ Plugin (UnrealDeadlineCloudService)                        │
│  │   ├── MovieRenderPipeline integration (MRQ executor)             │
│  │   ├── DeadlineCloudJobSettings (UE property system)              │
│  │   └── PythonAPILibraries (C++ ↔ Python bridge)                   │
│  │                                                                  │
│  └── Python (runs in UE's embedded interpreter)                     │
│      ├── Content/Python/ (plugin-side scripts)                      │
│      │   ├── init_unreal.py, settings.py, remote_executor.py        │
│      │   ├── open_job_template_api.py (C++ calls into this)         │
│      │   ├── submit_actions/ (render, p4, ugs, custom)              │
│      │   └── openjd_templates/ (YAML job/step/env templates)        │
│      │                                                              │
│      └── deadline.unreal_submitter (pip-installed package)           │
│          ├── submitter.py (orchestrates submission in bg thread)     │
│          ├── unreal_open_job/ (builds OpenJD job bundles)            │
│          └── unreal_dependency_collector.py (asset attachments)      │
│                                                                     │
│  Submits via: deadline.client.api → Deadline Cloud                  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                    OpenJD Job Bundle
                              │
                              ▼
┌─────────────────────── WORKER NODE ─────────────────────────────────┐
│                                                                     │
│  deadline.unreal_adaptor (Python process, outside UE)               │
│  ├── UnrealAdaptor/adaptor.py (manages UE subprocess lifecycle)     │
│  │   ├── Spawns UE via LoggingSubprocess                            │
│  │   ├── Runs AdaptorServer for IPC                                 │
│  │   └── Feeds actions via ActionsQueue                             │
│  │                                                                  │
│  └── UnrealClient/ (runs inside UE subprocess)                      │
│      ├── unreal_client.py (IPC with adaptor server)                 │
│      └── step_handlers/ (render, custom script)                     │
│                                                                     │
│  deadline.unreal_perforce_utils (if P4 job)                         │
│  ├── Workspace creation, sync, cleanup                              │
│  └── Credentials from AWS Secrets Manager                           │
│                                                                     │
│  deadline.unreal_cmd_utils (CLI arg merging for UE)                 │
│  deadline.unreal_logger (Python ↔ UE log bridge)                    │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Boundaries

| Component | Language | Runs Where | Key Responsibility |
|-----------|----------|------------|-------------------|
| `src/unreal_plugin/` C++ | C++ | UE Editor | UI, MRQ integration, UE property system, calls Python via bridge |
| `src/unreal_plugin/Content/Python/` | Python | UE Editor | Plugin-side scripts called by C++, OpenJD YAML templates |
| `src/deadline/unreal_submitter/` | Python | UE Editor | Job bundle construction, submission via `deadline.client.api` |
| `src/deadline/unreal_adaptor/UnrealAdaptor/` | Python | Worker (outside UE) | Manages UE subprocess, IPC server, action dispatch |
| `src/deadline/unreal_adaptor/UnrealClient/` | Python | Worker (inside UE) | IPC client, step handlers for rendering |
| `src/deadline/unreal_perforce_utils/` | Python | Worker | P4 workspace management, credential retrieval |
| `src/deadline/unreal_logger/` | Python | Both | Log bridge: Python `logging` ↔ `unreal.log()` |
| `src/deadline/unreal_cmd_utils/` | Python | Worker | UE CLI argument parsing and merging |

### The C++ ↔ Python Bridge

The C++ plugin defines abstract `UCLASS` types in `PythonAPILibraries/` (e.g., `PythonYamlLibrary`, `DeadlineCloudSettingsLibrary`). Python scripts in `Content/Python/` subclass these with `@unreal.uclass()` and implement the methods. C++ calls Python through UE's Python Script Plugin.

Key bridge files:
- C++: `Public/PythonAPILibraries/*.h` → abstract interfaces
- Python: `Content/Python/open_job_template_api.py`, `settings.py` → implementations

### Submission Flow

1. User configures job in MRQ UI (C++ `DeadlineCloudJobSettings` → UE property panels)
2. User clicks "Render (Remote)" → `MoviePipelineDeadlineCloudExecutorJob` triggers
3. C++ calls Python bridge → `submit_actions/render_job_submission.py`
4. Python creates `UnrealOpenJob` → builds OpenJD template from YAML templates + user settings
5. `DependencyCollector` gathers asset references
6. `submitter.py` submits via `deadline.client.api` in a background thread
7. Job bundle (OpenJD YAML + attachments) sent to Deadline Cloud

### Worker Rendering Flow

1. Deadline Cloud dispatches job to worker
2. `unreal-engine-openjd` CLI starts `UnrealAdaptor`
3. Adaptor validates init data against JSON schemas
4. Adaptor spawns UE subprocess with configured CLI args (merged via `unreal_cmd_utils`)
5. `UnrealClient` inside UE connects to adaptor's IPC server
6. Adaptor sends render actions via `ActionsQueue`
7. Step handlers execute renders (sticky rendering — UE stays open between tasks/shots)
8. Adaptor collects results and reports status

### Logging Rules

- **Code running outside UE** (adaptor server, perforce utils): use `logging.getLogger(__name__)`
- **Code running inside UE** (submitter, UnrealClient, plugin Python): use `from deadline.unreal_logger import get_logger`
- The `unreal` module import is always guarded with `try/except` in shared code

### Job Types

| Type | Submit Action | Templates | Description |
|------|--------------|-----------|-------------|
| Render | `render_job_submission.py` | `render_job.yml`, `render_step.yml` | Standard MRQ render |
| P4 Render | `p4_render_job_submission.py` | `p4/p4_*.yml` | Render with Perforce sync |
| UGS Render | `ugs_render_job_submission.py` | `ugs/ugs_*.yml` | Render with UnrealGameSync |
| Custom | `custom_job_submission.py` | `custom/custom_*.yml` | Custom script execution |

### OpenJD Template Structure

Templates in `Content/Python/openjd_templates/` define the job structure:
- **Job template** — top-level job definition with parameter definitions
- **Step templates** — render steps (per-shot task mapping)
- **Environment templates** — UE launch config, P4 sync, UGS sync, secrets
- **Host requirements** — GPU, OS, memory constraints

Python code in `unreal_open_job/` reads these YAML templates and merges them with user settings to produce the final OpenJD job bundle.

### External References

When designing features that touch Unreal Engine APIs, look up the official docs:
- **UE C++ API:** https://dev.epicgames.com/documentation/en-us/unreal-engine/API
- **UE Python API:** https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api

For OpenJD template work, use the `openjd-template` skill.

### Where New Code Should Go

| If you're adding... | Put it in... |
|---------------------|-------------|
| New UE editor UI / settings | `src/unreal_plugin/Source/` (C++) + `Content/Python/` if Python bridge needed |
| New job type | `Content/Python/submit_actions/` + `openjd_templates/` + `unreal_open_job/` |
| New worker-side behavior | `src/deadline/unreal_adaptor/` (adaptor or client side depending on UE dependency) |
| New submission logic | `src/deadline/unreal_submitter/` |
| Perforce features | `src/deadline/unreal_perforce_utils/` |
| CLI arg handling | `src/deadline/unreal_cmd_utils/` |
| OpenJD data assets | `Content/OpenJD_DataAssets/` |
