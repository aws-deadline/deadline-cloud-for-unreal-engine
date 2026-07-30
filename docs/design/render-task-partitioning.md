# Render Task Partitioning

When you submit a render to AWS Deadline Cloud, the Unreal submitter splits the work in a Movie Render Queue (MRQ) job into multiple OpenJD **tasks** so they can be distributed across worker hosts.

This integration supports three partitioning modes, described below. Modes 1 and 2 are **submitter-side**: the task breakdown is decided at submission time and configured on the Render Step / Render Job parameters. Mode 3 is **scheduler-side**: chunk boundaries are computed by Deadline Cloud at dispatch time using OpenJD's native [task chunking](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0001-task-chunking.md) (`TASK_CHUNKING`) extension. The modes are mutually exclusive — Mode 3 is selected by using the dynamic-chunking template pair, and within the submitter-side modes `FramesPerTask` takes precedence when set.

> **Naming history:** the submitter-side parameters were originally called `ChunkSize`/`ChunkId`. They were renamed to `ShotsPerTask`/`TaskIndex` to avoid colliding with OpenJD's own `ChunkSize` parameter, which Mode 3 uses with OpenJD's meaning (frames per chunk). See the [version compatibility](#version-compatibility) section for which releases use which names.

## Mode 1 — Shots per task (`ShotsPerTask`)

Partitions the **enabled shots** of the Level Sequence. Each task renders up to `ShotsPerTask` consecutive enabled shots.

- Task count = ceil(number of enabled shots / `ShotsPerTask`)
- `ShotsPerTask` defaults to 1 (one shot per task). If it is 0 or negative, the submitter also uses 1.

Example — a Level Sequence with 10 enabled shots and `ShotsPerTask = 3` produces 4 tasks:

| TaskIndex | Shots rendered |
|---|---|
| 0 | 0, 1, 2 |
| 1 | 3, 4, 5 |
| 2 | 6, 7, 8 |
| 3 | 9 |

Use this mode when your sequence is organized into shots and you want each task to cover a whole number of shots.

### How to use

Use the default `DeadlineCloudRenderJob` Job Preset and set `FramesPerTask` to `0` in the MRQ job's **Job Template Overrides**. With `FramesPerTask` disabled, partitioning falls back to `ShotsPerTask`, which defaults to 1 (one shot per task). To change the number of shots per task, customize the Render Step Data Asset and set its `ShotsPerTask` parameter.

![Job Template Overrides with FramesPerTask set to 0](./images/render-task-partitioning-mode1.png)

## Mode 2 — Frames per task (`FramesPerTask`)

Partitions the **frame range** of the render. Each task renders up to `FramesPerTask` consecutive frames, regardless of shot boundaries.

- Task count = ceil(total frame range / `FramesPerTask`)
- `FramesPerTask` takes precedence: if it is set and greater than 0, `ShotsPerTask` is ignored.
- The frame range comes from the MRQ output settings' custom playback range if enabled, otherwise from the Level Sequence's playback range.

Example — a 100-frame sequence with `FramesPerTask = 25` produces 4 tasks:

| TaskIndex | Frames rendered |
|---|---|
| 0 | 0–24 |
| 1 | 25–49 |
| 2 | 50–74 |
| 3 | 75–99 |

Use this mode when you want even-sized tasks by frame count — for example to load-balance a long single shot across many workers.

### How to use

Use the default `DeadlineCloudRenderJob` Job Preset and set `FramesPerTask` to the number of frames per task in the MRQ job's **Job Template Overrides**. Any value greater than 0 enables this mode (`ShotsPerTask` is then ignored).

![Job Template Overrides with FramesPerTask set to 25](./images/render-task-partitioning-mode2.png)

## Mode 3 — Dynamic chunking (OpenJD `TASK_CHUNKING`)

Partitions the **frame range** of the render, like Mode 2 — but the chunk boundaries are computed by the Deadline Cloud scheduler at **dispatch time**, not by the submitter at submission time. This uses OpenJD's native [task chunking](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0001-task-chunking.md) extension (`TASK_CHUNKING`) with a `CHUNK[INT]` task parameter.

Dynamic chunking is **opt-in** via the dedicated template pair `dynamic_chunking/dynamic_chunking_render_job.yml` + `dynamic_chunking_render_step.yml`.

How it works:

- At submission, the submitter populates a hidden `Frames` job parameter with the render's frame range (formatted `<start>-<end>`, e.g. `0-99`) from the MRQ output settings' custom playback range if enabled, otherwise from the Level Sequence's playback range.
- The step's `DynamicChunking` task parameter (type `CHUNK[INT]`) ranges over `Frames`, producing one task per frame — chunking does **not** reduce the task count. At dispatch time the scheduler groups those tasks into chunks and runs each chunk as a single session action, handing it one contiguous sub-range via the `dynamic_chunked_frames` run_data key (e.g. `25-49`, inclusive on both ends).
- The adaptor parses that range and sets MRQ's `custom_start_frame`/`custom_end_frame` for the task (converting the scheduler's inclusive end to Unreal's exclusive end).

Job parameters on the dynamic-chunking template:

| Parameter | Meaning |
|---|---|
| `ChunkSize` | Default number of frames per chunk (OpenJD's `defaultTaskCount`). Default: 50. |
| `TargetRuntimeSeconds` | Optional target runtime per chunk. When greater than 0, the scheduler may adjust chunk sizes toward this runtime as chunks complete. When 0 (default), all chunks use `ChunkSize`. |
| `Frames` | Frame range expression. Populated automatically by the submitter; you do not set it by hand. |

Key differences from Mode 2:

- **Chunk boundaries can adapt.** With `TargetRuntimeSeconds` set, the scheduler can resize later chunks based on how long earlier chunks took — something submission-time partitioning cannot do.
- **No `TaskIndex`.** Chunks are identified by their frame sub-range, not by a 0-based index. For output file naming, the adaptor substitutes the chunk's **start frame** for the `{task_index}` filename token (chunk start frames are unique across chunks of a contiguous range).
- **Contiguous ranges only.** Unreal's Movie Render Queue only accepts contiguous frame ranges (`custom_start_frame`/`custom_end_frame`), so the template pins `rangeConstraint: CONTIGUOUS`. Non-contiguous chunk lists (e.g. pick-up frames `1,5,10`) are not supported until MRQ can render non-sequential frames.

Requirements: see [version compatibility](#version-compatibility).

### How to use

Dynamic chunking is not selectable from the default `DeadlineCloudRenderJob` Job Preset. To opt in, create your own Job and Step Data Assets whose template paths point at `dynamic_chunking/dynamic_chunking_render_job.yml` and `dynamic_chunking/dynamic_chunking_render_step.yml`, and set `ChunkSize` (frames per chunk) and optionally `TargetRuntimeSeconds` on the job. `Frames` is populated automatically at submission.

![Dynamic chunking overrides with ChunkSize set to 50 and TargetRuntimeSeconds set to 0](./images/render-task-partitioning-mode3.png)

## `TaskIndex`

In Modes 1 and 2, each generated task is assigned a 0-based `TaskIndex` identifying which partition it renders. It is filled in automatically during submission; you do not set it by hand. The adaptor uses `TaskIndex` to select the correct shots (Mode 1) or frame window (Mode 2) for each task. Mode 3 has no `TaskIndex` — chunks are identified by their frame sub-range instead.

### Output file naming

When a render is split across multiple tasks, MRQ writes one output file per task. For image sequences (PNG/EXR/etc.) the default `FileNameFormat` includes `{frame_number}`, so each task's output is already unique. For video containers such as `.mov`, the default format is just `{sequence_name}` and every task would write to the same filename. To disambiguate, add the `{task_index}` token to the MRQ Output Setting's `FileNameFormat` (for example `{sequence_name}_{task_index}`); the adaptor substitutes it at render time with a zero-padded value: the per-task index (Modes 1 and 2) or the chunk's start frame (Mode 3).

## Version compatibility

The submitter (Unreal plugin) and the adaptor (worker-side `unrealengine-openjd` package) are released independently. Their contract is the set of run_data keys the submitter's templates emit and the adaptor reads. The partitioning parameters were renamed across three minor versions (`ChunkSize`→`ShotsPerTask` on the wire `chunk_size`→`shots_per_task`, and `ChunkId`→`TaskIndex` on the wire `chunk_id`→`task_index`):

| Version | Submitter emits | Adaptor accepts |
|---|---|---|
| 0.6.x (≥ 0.6.10) | legacy names (`chunk_size`/`chunk_id`) | **both** legacy and new |
| 0.7.x | new names (`shots_per_task`/`task_index`) | **both** legacy and new |
| 0.8.x | new names | new names only |

Any submitter/adaptor pairing within one minor version of each other keeps working, provided a 0.6.x adaptor is at least 0.6.10. Because run_data fields are optional in the adaptor's schema (only `handler` is required), a mismatched pairing fails **silently with wrong output** — the task renders the full sequence instead of its partition — rather than loudly. The two mismatches to avoid:

- A 0.7+ submitter's template reaching a pre-0.6.10 adaptor (adaptor doesn't know the new keys).
- A legacy (pre-0.7) template reaching a 0.8+ adaptor (adaptor no longer accepts the old keys). Regenerate old job bundles and update custom templates or submission scripts that still reference `ChunkSize`/`ChunkId`.

On service-managed fleets the adaptor version is selected by the `CondaPackages` parameter in the job template (the bundled templates pin the adaptor minor version matching the submitter). On customer-managed fleets the adaptor is installed manually and must be kept version-matched to the submitter.

Mode 3 (dynamic chunking) additionally requires `TASK_CHUNKING` extension support in the fleet's worker agent and an adaptor that understands the `dynamic_chunked_frames` run_data key.

