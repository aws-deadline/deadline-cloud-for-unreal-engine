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
