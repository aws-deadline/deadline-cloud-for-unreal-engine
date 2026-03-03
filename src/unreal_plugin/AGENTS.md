# AGENTS.md — unreal_plugin (UE C++ Plugin)

## Overview

Unreal Engine C++ plugin (`UnrealDeadlineCloudService`) that provides the in-editor UI and API for submitting render jobs to AWS Deadline Cloud. Requires UE 5.4+.

## Structure

- `Source/UnrealDeadlineCloudService/`
  - `Private/` — Implementation files
    - `DeadlineCloudJobSettings/` — Job, environment, step, host requirements settings and detail customizations
    - `MovieRenderPipeline/` — Movie Render Pipeline (MRQ) integration for Deadline Cloud execution
    - `PythonAPILibraries/` — C++ wrappers exposing Python APIs to Blueprints (job bundles, settings, YAML)
    - `Tests/` — Automation spec tests (environment, host requirements, job, step, UI)
  - `Public/` — Header files mirroring the Private structure
- `Content/`
  - `Python/` — Python scripts running inside UE
    - `init_unreal.py` — Plugin initialization
    - `settings.py` — Settings management
    - `job_library.py` — Job-related utilities
    - `open_job_template_api.py` — OpenJD template API
    - `remote_executor.py` — Remote execution utilities for Deadline Cloud
    - `submit_actions/` — Submission action scripts (render, P4 render, UGS render, custom)
    - `openjd_templates/` — YAML OpenJD templates (render jobs, steps, environments, host requirements)
  - `OpenJD_DataAssets/` — UE data assets for OpenJD presets (Default, Render, Perforce, UGS)
  - `Widgets/` — UE widget assets (job submitter UI, path selector)
- `Config/` — Plugin default settings INI
- `Documentation/` — Doxygen configuration for C++ docs

## Plugin dependencies

Requires these UE plugins (declared in `.uplugin`):
- `PythonScriptPlugin`
- `MovieRenderPipeline`
- `EditorScriptingUtilities`

## Build

- Build file: `UnrealDeadlineCloudService.Build.cs`
- Module type: `UncookedOnly` (editor-only, not shipped in cooked builds)
- The Python `deadline-cloud-for-unreal-engine` package (>=0.5.0) must be available in the UE Python environment

## Development pipeline

- Python submitter library is bundled into `Content/Python/libraries/` during CI/CD (see `DEVELOPMENT.md`)
- C++ docs generated with Doxygen: `cd Documentation && doxygen`

## Testing

- C++ automation tests in `Private/Tests/` — run via UE's Automation framework
- Integration tests in `Private/Tests/Integration/`
- OpenJD template tests in `Private/Tests/openjd_templates/`

## Code style

- C++ follows standard UE coding conventions
- Python files in `Content/Python/` follow the same style as the `deadline.*` packages (copyright header, type hints, ruff/black formatting)
