# Render Task Partitioning

When you submit a render to AWS Deadline Cloud, the Unreal submitter splits the work in a Movie Render Queue (MRQ) job into multiple OpenJD **tasks** so they can be distributed across worker hosts.

This integration currently supports two submitter-side partitioning modes, described below. They are configured on the Render Step / Render Job parameters and are mutually exclusive — `FramesPerTask` takes precedence when set.

> **Note on terminology — submitter partitioning vs. OpenJD chunking:** OpenJD has its own native [task chunking](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0001-task-chunking.md) feature, where the scheduler groups tasks into chunks at dispatch time using a `ChunkSize` parameter and a `CHUNK[INT]` task-parameter type. The two modes below are different: they are **submitter-side** partitioning that decides the task breakdown at submission time, implemented in this integration rather than the OpenJD scheduler.
>
> Support for OpenJD's native chunking is planned as an additional mode. To avoid the name collision ahead of that work, the submitter-side parameters that were previously called `ChunkSize`/`ChunkId` are now `ShotsPerTask`/`TaskIndex`. When OpenJD chunking is added, its `ChunkSize` will be a distinct, separately-documented concept.
>
> **Compatibility:** templates emitted by submitters ≥ 0.7.0 require adaptor ≥ 0.6.10 on the worker. Older adaptors ignore the new run_data keys and silently render the full sequence instead of the intended partition.

## Mode 1 — Shots per task (`ShotsPerTask`)

Partitions the **enabled shots** of the Level Sequence. Each task renders up to `ShotsPerTask` consecutive enabled shots.

- Task count = ceil(number of enabled shots / `ShotsPerTask`)
- If `ShotsPerTask` is 0 or negative, it defaults to 1 (one shot per task).

Example — a Level Sequence with 10 enabled shots and `ShotsPerTask = 3` produces 4 tasks:

| TaskIndex | Shots rendered |
|---|---|
| 0 | 0, 1, 2 |
| 1 | 3, 4, 5 |
| 2 | 6, 7, 8 |
| 3 | 9 |

Use this mode when your sequence is organized into shots and you want each task to cover a whole number of shots.

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

## `TaskIndex`

In both modes, each generated task is assigned a 0-based `TaskIndex` identifying which partition it renders. It is filled in automatically during submission; you do not set it by hand. The adaptor uses `TaskIndex` to select the correct shots (Mode 1) or frame window (Mode 2) for each task.

### Output file naming

When a render is split across multiple tasks, MRQ writes one output file per task. For image sequences (PNG/EXR/etc.) the default `FileNameFormat` includes `{frame_number}`, so each task's output is already unique. For video containers such as `.mov`, the default format is just `{sequence_name}` and every task would write to the same filename. To disambiguate, add the `{task_index}` token to the MRQ Output Setting's `FileNameFormat` (for example `{sequence_name}_{task_index}`); the submitter substitutes it at render time with a zero-padded per-task index.

