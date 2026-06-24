# Render Task Partitioning

When you submit a render to AWS Deadline Cloud, the Unreal submitter splits the work in a Movie Render Queue (MRQ) job into multiple OpenJD **tasks** so they can be distributed across worker hosts.

This integration currently supports two submitter-side partitioning modes, described below. They are configured on the Render Step / Render Job parameters and are mutually exclusive — `FramesPerTask` takes precedence when set.

> **Parameter rename in progress.** Two of these parameters are being renamed to avoid colliding with OpenJD's own task-chunking terminology:
>
> | Old name | New name |
> |---|---|
> | `ChunkSize` | `ShotsPerTask` |
> | `ChunkId` | `TaskIndex` |
>
> Both names are referenced throughout this page as **`ChunkSize` / `ShotsPerTask`** and **`ChunkId` / `TaskIndex`**. During the transition the worker adaptor accepts either name, so jobs keep working whichever name your submitter emits. The old names are deprecated and will be removed in a future release.

> **Important — `ChunkSize` / `ShotsPerTask` is NOT OpenJD's `ChunkSize`:** OpenJD has its own native [task chunking](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0001-task-chunking.md) feature with a `ChunkSize` parameter and a `CHUNK[INT]` task-parameter type, where the scheduler groups tasks into chunks at dispatch time. This integration's parameter is unrelated: it is a **submitter-side** value that decides the shot-per-task breakdown at submission time, implemented in this integration rather than the OpenJD scheduler. The two share the old name but mean different things — and OpenJD's `ChunkSize` is actually closest in meaning to this integration's `FramesPerTask` (frames grouped per task), not to `ChunkSize` / `ShotsPerTask` (shots per task). The rename exists precisely to remove this confusion.

## Mode 1 — Shots per task (`ChunkSize` / `ShotsPerTask`)

Partitions the **enabled shots** of the Level Sequence. Each task renders up to `ChunkSize` / `ShotsPerTask` consecutive enabled shots.

- Task count = ceil(number of enabled shots / `ChunkSize` / `ShotsPerTask`)
- If the value is 0 or negative, it defaults to 1 (one shot per task).

Example — a Level Sequence with 10 enabled shots and `ChunkSize` / `ShotsPerTask` = 3 produces 4 tasks:

| ChunkId / TaskIndex | Shots rendered |
|---|---|
| 0 | 0, 1, 2 |
| 1 | 3, 4, 5 |
| 2 | 6, 7, 8 |
| 3 | 9 |

Use this mode when your sequence is organized into shots and you want each task to cover a whole number of shots.

## Mode 2 — Frames per task (`FramesPerTask`)

Partitions the **frame range** of the render. Each task renders up to `FramesPerTask` consecutive frames, regardless of shot boundaries. (`FramesPerTask` is not affected by the rename.)

- Task count = ceil(total frame range / `FramesPerTask`)
- `FramesPerTask` takes precedence: if it is set and greater than 0, `ChunkSize` / `ShotsPerTask` is ignored.
- The frame range comes from the MRQ output settings' custom playback range if enabled, otherwise from the Level Sequence's playback range.

Example — a 100-frame sequence with `FramesPerTask = 25` produces 4 tasks:

| ChunkId / TaskIndex | Frames rendered |
|---|---|
| 0 | 0–24 |
| 1 | 25–49 |
| 2 | 50–74 |
| 3 | 75–99 |

Use this mode when you want even-sized tasks by frame count — for example to load-balance a long single shot across many workers.

## `ChunkId` / `TaskIndex`

In both modes, each generated task is assigned a 0-based `ChunkId` / `TaskIndex` identifying which partition it renders. It is filled in automatically during submission; you do not set it by hand. The adaptor uses it to select the correct shots (Mode 1) or frame window (Mode 2) for each task.

### Output file naming

When a render is split across multiple tasks, MRQ writes one output file per task. For image sequences (PNG/EXR/etc.) the default `FileNameFormat` includes `{frame_number}`, so each task's output is already unique. For video containers such as `.mov`, the default format is just `{sequence_name}` and every task would write to the same filename. To disambiguate, add the `{task_index}` token to the MRQ Output Setting's `FileNameFormat` (for example `{sequence_name}_{task_index}`); the submitter substitutes it at render time with a zero-padded per-task index.
