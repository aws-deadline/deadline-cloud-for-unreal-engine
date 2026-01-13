# Job Template Generation Workflow

This document describes how the Unreal submitter generates OpenJD job templates for submission to AWS Deadline Cloud.

## Overview

When a user submits a render job from Unreal Engine, the submitter converts the job configuration into an OpenJD-compliant job template. This template defines the job structure, parameters, steps, and task distribution.

## Architecture

```
User submits render job from Unreal
           │
           ▼
┌─────────────────────────────────────┐
│  UnrealOpenJob.build_template()     │  ← Job-level template
│  - Job parameters (Frames, etc.)    │
│  - Job environments                 │
│  - Calls step.build_template()      │
└─────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  UnrealOpenJobStep.build_template() │  ← Step-level template
│  - Validates parameters             │
│  - Calls _build_template()          │
└─────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  _build_template()                  │
│  1. Get step parameters list        │
│  2. Build parameterSpace            │
│  3. Add environments                │
│  4. Add dependencies                │
│  5. Add host requirements           │
│  6. Return StepTemplate             │
└─────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  Final OpenJD Job Template (JSON)   │
│  - Submitted to Deadline Cloud      │
└─────────────────────────────────────┘
```

## Key Components

### UnrealOpenJob (`unreal_open_job.py`)

The top-level job entity that:
- Holds job-level parameters (project path, frames, runtime settings)
- Contains one or more steps (render steps, custom steps)
- Manages job environments
- Builds the complete `JobTemplate` OpenJD model

### UnrealOpenJobStep (`unreal_open_job_step.py`)

Represents a single step in the job:
- Reads step configuration from YAML templates
- Manages task parameter definitions (how work is divided)
- Handles step dependencies and environments
- Builds `StepTemplate` OpenJD model

### Key Methods

#### `_build_step_parameter_definition_list()`

Builds the list of task parameter definitions from the YAML template:

1. **Reads YAML template** - Gets `taskParameterDefinitions` from the step template
2. **Applies parameter overrides** - For standard types (INT, FLOAT, STRING, PATH), allows runtime customization from `_extra_parameters`
3. **Skips overrides for CHUNK[INT]** - Dynamic chunking parameters get their values from template expressions like `"{{Param.Frames}}"`
4. **Parses into OpenJD models** - Converts YAML dicts into validated OpenJD model objects using `PARAMETER_DEFINITION_MAPPING`

#### `_build_template()`

Assembles the complete step template:

1. Calls `_build_step_parameter_definition_list()` to get task parameters
2. Builds `parameterSpace` with task parameter definitions
3. Adds step environments
4. Adds step dependencies
5. Adds host requirements
6. Returns parsed `StepTemplate` model

## Parameter Types

Defined in `PARAMETER_DEFINITION_MAPPING`:

| Type | OpenJD Class | Python Class | Description |
|------|--------------|--------------|-------------|
| INT | `IntTaskParameterDefinition` | `int` | Integer values |
| FLOAT | `FloatTaskParameterDefinition` | `float` | Floating point values |
| STRING | `StringTaskParameterDefinition` | `str` | String values |
| PATH | `PathTaskParameterDefinition` | `str` | File/directory paths |
| CHUNK[INT] | `ChunkIntTaskParameterDefinition` | N/A | Dynamic chunking (TASK_CHUNKING extension) |

## Parameter Name Classes

### OpenJobParameterNames (Job-level)

Parameters defined at the job level:
- `UNREAL_PROJECT_PATH`, `UNREAL_PROJECT_NAME` - Project configuration
- `FRAMES`, `TARGET_RUNTIME_SECONDS`, `RANGE_CONSTRAINT` - Dynamic chunking configuration
- `PERFORCE_*` - Source control settings

### OpenJobStepParameterNames (Step-level)

Parameters defined at the step level:
- `QUEUE_MANIFEST_PATH`, `LEVEL_SEQUENCE_PATH` - Render configuration
- `TASK_CHUNK_SIZE`, `TASK_CHUNK_ID` - Static chunking
- `DYNAMIC_CHUNKING` - CHUNK[INT] task parameter name

## Parameter Overrides

YAML step templates define static task parameter definitions, but actual job configurations vary at runtime. Parameter overrides allow the submitter to dynamically adjust these definitions based on the specific job being submitted.

### How It Works

1. YAML template defines base parameter structure (name, type, range)
2. At submission time, `_extra_parameters` contains runtime values from the job configuration
3. `_build_step_parameter_definition_list()` merges these by overriding the template's `range` field
4. The merged definition is parsed into an OpenJD model

### Example

Template defines:
```yaml
taskParameterDefinitions:
  - name: "ChunkId"
    type: "INT"
    range: [0]  # Static placeholder
```

At runtime, if the job has 5 shots, the submitter overrides:
```python
range: [0, 1, 2, 3, 4]  # Actual shot indices
```

### Why CHUNK[INT] Skips Overrides

CHUNK[INT] parameters use template expressions (e.g., `"{{Param.Frames}}"`) instead of static ranges. The actual chunk boundaries are computed by Deadline Cloud at runtime based on:
- Frame range from job parameters
- Target runtime per chunk
- Historical performance data

Since the range isn't known until Deadline Cloud processes the job, there's nothing to override at submission time.

## Dynamic Chunking (TASK_CHUNKING Extension)

For dynamic chunking templates:

1. Job-level parameters (`Frames`, `TargetRuntimeSeconds`, `RangeConstraint`) are defined in `OpenJobParameterNames`
2. Step template references these via `CHUNK[INT]` type with `chunks` configuration
3. `ChunkIntTaskParameterDefinition` OpenJD class handles the special structure
4. Deadline Cloud service calculates optimal chunk boundaries at runtime

## Files

- `src/deadline/unreal_submitter/unreal_open_job/unreal_open_job.py` - Job entity
- `src/deadline/unreal_submitter/unreal_open_job/unreal_open_job_step.py` - Step entity
- `src/deadline/unreal_submitter/unreal_open_job/unreal_open_job_entity.py` - Base entity, parameter mappings
- `src/deadline/unreal_submitter/unreal_open_job/unreal_open_job_dynamic_chunking.py` - Dynamic chunking helper
