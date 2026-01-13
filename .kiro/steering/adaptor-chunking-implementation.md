# Adaptor Chunking Implementation

This document describes how the Unreal submitter and adaptor divide rendering work across Deadline Cloud tasks. There are three chunking modes: shot-based (ChunkSize), frame-based (FramesPerTask) and dynamic chunking (dynamic_chunked_frames). These modes are mutually exclusive.

## Overview

For shot-based and frame-based chunking, the submitter calculates how many tasks are needed, then populates the `ChunkId` task parameter range. For dynamic chunking, Deadline Cloud's TASK_CHUNKING extension computes frame ranges and passes them directly to the adaptor via `dynamic_chunked_frames`.

## Architecture

```
Submission Time                          Worker Execution Time
───────────────                          ────────────────────

┌─────────────────────────┐              ┌─────────────────────────┐
│ Dynamic Chunking:       │              │ run_script(args)        │
│   TASK_CHUNKING ext     │   OpenJD     │                         │
│   computes frame ranges │ ──────────►  │ Dynamic Chunking:       │
│                         │   Template   │   parse_dynamic_chunked │
├─────────────────────────┤              │   _frames() → set       │
│ Non-Dynamic Chunking:   │              │   custom_start/end      │
│ _get_chunk_ids_count()  │              │                         │
│                         │              │ Frame-based:            │
│ Shot-based Chunking:    │              │   custom_start/end_frame│
│   10 shots / 3 = 4 tasks│              │                         │
│                         │              │ Shot-based:             │
│ Frame-based Chunking:   │              │   enable_shots_by_chunk │
│   100 frames / 25 = 4   │              │                         │
│                         │              │                         │
│ ChunkId = [0,1,2,3]     │              │                         │
└─────────────────────────┘              └─────────────────────────┘
```

## Parameter Priority

The three chunking modes are mutually exclusive. The adaptor checks for parameters in this order:

```
dynamic_chunked_frames present  →  Use dynamic chunking (parse directly)
         ↓ (fallback if not present)
FramesPerTask > 0               →  Use frame-based division
         ↓ (fallback if 0 or missing)
ChunkSize > 0                   →  Use shot-based division
         ↓ (fallback if 0)
ChunkSize = 1                   →  One shot per task (default)
```

## Key Components

### 1. Parameter Definitions

Location: `src/deadline/unreal_submitter/unreal_open_job/unreal_open_job_entity.py`

```python
class OpenJobStepParameterNames:
    FRAMES_PER_TASK = "FramesPerTask"  # Frame-based division
    TASK_CHUNK_SIZE = "ChunkSize"       # Shot-based division
    TASK_CHUNK_ID = "ChunkId"           # Task identifier for Frame-based and Shot-based modes
    DYNAMIC_CHUNKING = "DynamicChunking"  # Dynamic chunking
```

### 2. Task Count Calculation (Submitter)

Location: `src/deadline/unreal_submitter/unreal_open_job/unreal_open_job_step.py`

Method: `RenderUnrealOpenJobStep._get_chunk_ids_count()`

Note: This method is used for shot-based and frame-based chunking. Dynamic chunking templates use `CHUNK[INT]` type which is handled by Deadline Cloud's TASK_CHUNKING extension.

```python
def _get_chunk_ids_count(self) -> int:
    enabled_shots = [shot for shot in self.mrq_job.shot_info if shot.enabled]
    
    # Priority 1: Frame-based division
    frames_per_task_parameter = self.open_job._find_extra_parameter(
        parameter_name=OpenJobStepParameterNames.FRAMES_PER_TASK, parameter_type="INT"
    )
    if frames_per_task_parameter and frames_per_task_parameter.value > 0:
        total_frame_range = end_frame - start_frame
        return math.ceil(total_frame_range / frames_per_task_parameter.value)
    
    # Priority 2: Shot-based division
    chunk_size = int(chunk_size_parameter.value)
    if chunk_size <= 0:
        chunk_size = 1  # default: 1 shot per task
    
    return math.ceil(len(enabled_shots) / chunk_size)
```

### 3. OpenJD Templates

#### Shot-Based and Frame-Based Template

Location: `src/unreal_plugin/Content/Python/openjd_templates/render_job.yml`

```yaml
parameterDefinitions:
- name: FramesPerTask
  type: INT
  default: 0
- name: ChunkSize
  type: INT
  default: 1
```

Location: `src/unreal_plugin/Content/Python/openjd_templates/render_step.yml`

```yaml
parameterSpace:
  taskParameterDefinitions:
  - name: ChunkId
    type: INT
    range: []  # Populated at submission: [0, 1, 2, ...]

script:
  embeddedFiles:
  - name: runData
    data: |
      frames_per_task: {{Param.FramesPerTask}}
      chunk_size: {{Param.ChunkSize}}
      chunk_id: {{Task.Param.ChunkId}}
```

#### Dynamic Chunking Template

Location: `src/unreal_plugin/Content/Python/openjd_templates/dynamic_chunking/dynamic_chunking_render_job.yml`

```yaml
specificationVersion: jobtemplate-2023-09
extensions:
  - TASK_CHUNKING
parameterDefinitions:
- name: Frames
  type: STRING
  description: 'Frame range from MRQ settings. Populated by submitter at submission time.'
  userInterface: 
   control: HIDDEN
- name: ChunkSize
  type: INT
  default: 50
- name: TargetRuntimeSeconds
  type: INT
  default: 0
  minValue: 0
  description: 'Optional target runtime in seconds per chunk. When 0 (default), chunking uses the ChunkSize for all chunks.'
# NOTE: RangeConstraint parameter removed - CONTIGUOUS is hardcoded in step template
```

Location: `src/unreal_plugin/Content/Python/openjd_templates/dynamic_chunking/dynamic_chunking_render_step.yml`

```yaml
# NOTE: Only CONTIGUOUS rangeConstraint is supported because Unreal Engine's Movie Render Queue
# only accepts contiguous frame ranges (custom_start_frame/custom_end_frame).
parameterSpace:
  taskParameterDefinitions:
  - name: DynamicChunking
    type: CHUNK[INT]
    range: "{{Param.Frames}}"
    chunks:
      defaultTaskCount: "{{Param.ChunkSize}}"
      targetRuntimeSeconds: "{{Param.TargetRuntimeSeconds}}"
      rangeConstraint: CONTIGUOUS  # Hardcoded - non-contiguous not supported

script:
  embeddedFiles:
  - name: runData
    data: |
      dynamic_chunked_frames: {{Task.Param.DynamicChunking}}
```

### 4. Worker Execution (Adaptor)

Location: `src/deadline/unreal_adaptor/UnrealClient/step_handlers/unreal_render_step_handler.py`

Method: `UnrealRenderStepHandler.run_script()`

```python
def run_script(self, args: dict) -> bool:
    # ... queue creation logic ...
    
    for job in subsystem.get_queue().get_jobs():
        # Dynamic chunking or frame-based chunking (both set custom frame ranges)
        if "dynamic_chunked_frames" in args or (
            args.get("frames_per_task") and "chunk_id" in args
        ):
            # ... get output_settings and level_sequence ...
            
            # Determine frame range based on chunking mode
            if "dynamic_chunked_frames" in args:
                start_frame, end_frame = self.parse_dynamic_chunked_frames(
                    args["dynamic_chunked_frames"]
                )
                # The scheduler returns inclusive frame ranges (e.g., "10-10" means 1 frame),
                # but Unreal's custom_end_frame is exclusive. Add 1 to make it inclusive.
                end_frame = end_frame + 1
                # Dynamic chunking requires explicit custom playback range
                output_settings.use_custom_playback_range = True
            else:
                # Frame-based chunking
                frames_per_task: int = args["frames_per_task"]
                frame_range_start, frame_range_end = self.get_frame_range(
                    output_settings, level_sequence
                )
                start_frame = frame_range_start + (chunk_id * frames_per_task)
                end_frame = min(start_frame + frames_per_task, frame_range_end)
            
            output_settings.custom_start_frame = start_frame
            output_settings.custom_end_frame = end_frame
            level_sequence.set_playback_start(start_frame)
            level_sequence.set_playback_end(end_frame)
        
        # Shot-based chunking
        elif "chunk_size" in args and "chunk_id" in args:
            chunk_size: int = args["chunk_size"]
            UnrealRenderStepHandler.enable_shots_by_chunk(
                render_job=job,
                task_chunk_size=chunk_size,
                task_chunk_id=chunk_id,
            )
```

---

## Dynamic Chunking (dynamic_chunked_frames)

### CONTIGUOUS RangeConstraint Only

Per [OpenJobDescription task chunking RFC](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0001-task-chunking.md), it supports CONTIGUOUS and Non-contiguous rangeConstraints. But Unreal Engine's Movie Render Queue (MRQ) only accepts contiguous frame ranges via `custom_start_frame` and `custom_end_frame`. There is a open feature request for Unreal Engine rendering to support non-contiguous frames: https://issues.amazon.com/issues/Bea-51813#:~:text=https%3A//forums.unrealengine.com/t/feature%2Drequest%2Drendering%2Dnon%2Dsequential%2Dframe%2Dranges%2Dand%2Devery%2Dn%2Dth%2Dframe/1982729. We will not support non-contiguous frames until Unreal Engine supports it.

### How It Works

1. **Submission**: Job uses `TASK_CHUNKING` extension with `CHUNK[INT]` task parameter type
2. **Deadline Cloud**: TASK_CHUNKING service computes optimal frame chunks based on Frames, ChunkSize, TargetRuntimeSeconds, and RangeConstraint
3. **Execution**: Each worker receives `dynamic_chunked_frames` (e.g., "1-10") and parses it directly

### Frame Chunk Parsing

```python
@staticmethod
def parse_dynamic_chunked_frames(dynamic_chunked_frames: str) -> tuple[int, int]:
    """
    Parse a contiguous frame chunk expression into start and end frames.

    IMPORTANT: Only CONTIGUOUS rangeConstraint is supported. Non-contiguous frame lists
    (e.g., "1,5,10" or "1-5,10-15:2") are NOT supported because Unreal Engine's Movie Render
    Queue (MRQ) only accepts contiguous frame ranges via custom_start_frame/custom_end_frame.
    MRQ does not provide an API to render arbitrary non-contiguous frames in a single job.

    Supported format:
        Range: "<start>-<end>" (e.g., "1-10", "5-5", "0-100")

    :param dynamic_chunked_frames: Frame chunk expression string from TASK_CHUNKING extension
        (must be CONTIGUOUS rangeConstraint)
    :return: Tuple of (start_frame, end_frame)
    :raises ValueError: If dynamic_chunked_frames is empty, malformed, or not in range format
    """
    # Validate not empty
    if not dynamic_chunked_frames or not dynamic_chunked_frames.strip():
        raise ValueError("dynamic_chunked_frames cannot be empty")

    dynamic_chunked_frames = dynamic_chunked_frames.strip()

    # CONTIGUOUS mode always returns range format: "<start>-<end>"
    match = re.match(r"^(\d+)-(\d+)$", dynamic_chunked_frames)
    if match:
        start = int(match.group(1))
        end = int(match.group(2))
        if start > end:
            raise ValueError(
                f"Invalid frame range: start ({start}) cannot be greater than end ({end})"
            )
        return (start, end)

    raise ValueError(
        f"Invalid dynamic_chunked_frames format: '{dynamic_chunked_frames}'. "
        "Expected range format '<start>-<end>' (e.g., '1-10', '5-5')"
    )
```

### Example: 100 Frames with Dynamic Chunking

Deadline Cloud computes chunks based on configuration. The scheduler returns inclusive frame ranges, but Unreal's `custom_end_frame` is exclusive, so the adaptor adds 1 to the end frame:

| Task | dynamic_chunked_frames | Parsed Start | Parsed End | UE custom_start_frame | UE custom_end_frame | Frames Rendered |
|------|------------------------|--------------|------------|----------------------|---------------------|-----------------|
| 1    | "0-24"                 | 0            | 24         | 0                    | 25                  | 25              |
| 2    | "25-49"                | 25           | 49         | 25                   | 50                  | 25              |
| 3    | "50-74"                | 50           | 74         | 50                   | 75                  | 25              |
| 4    | "75-99"                | 75           | 99         | 75                   | 100                 | 25              |

Single frame example: `dynamic_chunked_frames = "10-10"` → `custom_start_frame = 10`, `custom_end_frame = 11` → renders 1 frame (frame 10)

Note: Unlike frame-based chunking, the adaptor doesn't calculate frame ranges - it receives them pre-computed from Deadline Cloud.

---

## Shot-Based Chunking (ChunkSize)

### How It Works

1. **Submission**: Submitter counts enabled shots and divides by `ChunkSize`
2. **Template**: `ChunkId` range populated with task indices `[0, 1, 2, ...]`
3. **Execution**: Each worker enables only its assigned shots using array slicing

### Shot Selection Logic

```python
@staticmethod
def enable_shots_by_chunk(render_job, task_chunk_size: int, task_chunk_id: int):
    all_shots_to_render = [shot for shot in render_job.shot_info if shot.enabled]
    
    # Array slice: shots[start:end] for this task
    shots_chunk = all_shots_to_render[
        task_chunk_id * task_chunk_size : (task_chunk_id + 1) * task_chunk_size
    ]
    
    # Enable only shots in this chunk, disable all others
    for shot in render_job.shot_info:
        shot.enabled = shot in shots_chunk
```

### Example: 10 Shots with ChunkSize=3

| Task | ChunkId | Shot Indices | Shots Rendered |
|------|---------|--------------|----------------|
| 1    | 0       | 0, 1, 2      | sh1, sh2, sh3  |
| 2    | 1       | 3, 4, 5      | sh4, sh5, sh6  |
| 3    | 2       | 6, 7, 8      | sh7, sh8, sh9  |
| 4    | 3       | 9            | sh10           |

Note: Only enabled shots are counted. Disabled shots in the level sequence are skipped.

---

## Frame-Based Chunking (FramesPerTask)

### How It Works

1. **Submission**: Submitter calculates total frame range and divides by `FramesPerTask`
2. **Template**: `ChunkId` range populated with task indices `[0, 1, 2, ...]`
3. **Execution**: Each worker sets custom start/end frame based on `ChunkId`

### Frame Range Caching

The adaptor caches the frame range on first access to ensure consistency:

```python
class UnrealRenderStepHandler(BaseStepHandler):
    cached_frame_range_start = None
    cached_frame_range_end = None
    
    @staticmethod
    def get_frame_range(output_settings, level_sequence):
        if UnrealRenderStepHandler.cached_frame_range_start is None:
            # Cache from custom playback range or level sequence
            ...
        return (cached_frame_range_start, cached_frame_range_end)
```

### Example: 100 Frames with FramesPerTask=25

| Task | ChunkId | Start Frame | End Frame | Frames |
|------|---------|-------------|-----------|--------|
| 1    | 0       | 0           | 25        | 25     |
| 2    | 1       | 25          | 50        | 25     |
| 3    | 2       | 50          | 75        | 25     |
| 4    | 3       | 75          | 100       | 25     |

---

## Files

### Submitter
- `src/deadline/unreal_submitter/unreal_open_job/unreal_open_job_entity.py` - Parameter names
- `src/deadline/unreal_submitter/unreal_open_job/unreal_open_job_step.py` - Task count calculation
- `src/deadline/unreal_submitter/unreal_open_job/unreal_open_job_dynamic_chunking.py` - Dynamic chunking validation

### Adaptor
- `src/deadline/unreal_adaptor/UnrealClient/step_handlers/unreal_render_step_handler.py` - Shot/frame selection, dynamic_chunked_frames parsing

### Tests
- `test/deadline_adaptor_for_unreal/unit/UnrealClient/step_handlers/test_unreal_render_step_handler_dynamic_chunking.py` - Dynamic chunking unit tests

### Templates (Shot-Based and Frame-Based)
- `src/unreal_plugin/Content/Python/openjd_templates/render_job.yml` - Job parameter definitions
- `src/unreal_plugin/Content/Python/openjd_templates/render_step.yml` - Step template with ChunkId

### Templates (Dynamic Chunking)
- `src/unreal_plugin/Content/Python/openjd_templates/dynamic_chunking/dynamic_chunking_render_job.yml` - Job with TASK_CHUNKING extension
- `src/unreal_plugin/Content/Python/openjd_templates/dynamic_chunking/dynamic_chunking_render_step.yml` - Step template with CHUNK[INT]

