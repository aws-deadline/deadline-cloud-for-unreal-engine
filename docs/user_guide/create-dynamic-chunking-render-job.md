# Creating a Dynamically Chunked Render Job

This guide walks you through creating dynamic chunking data assets and using them to submit Movie Render Queue (MRQ) jobs to AWS Deadline Cloud from Unreal Engine.

Dynamic chunking lets the Deadline Cloud scheduler group frames into contiguous chunks when tasks are dispatched. The scheduler can adjust later chunk sizes based on completed task runtimes, which can improve load balancing when frame render times vary.

Dynamic chunking is opt-in. The standard render job data asset continues to use the existing shots-per-task or frames-per-task behavior.

## Prerequisites

Before creating a dynamically chunked render job:

- Complete the [submitter setup](./setup-submitter.md).
- Configure a Deadline Cloud queue and fleet that can render Unreal Engine jobs.
- Install version `0.7.1` or later of the Unreal Engine submitter plugin.
- Ensure workers use `unrealengine-openjd` version `0.7.1` or later. Dynamic chunking is first available in release `0.7.1`.

> **Important:** The submitter and worker adaptor must both support dynamic chunking. An older adaptor can render the full MRQ sequence for every dispatched chunk instead of rendering only that chunk.

The provided dynamic chunking templates currently support the base render workflow only. Perforce, Unreal Game Sync (UGS), and Movie Pipeline Queue (MPQ) variants are not supported.

## How dynamic chunking works

The submitter reads the effective frame range from the MRQ job and sends it to Deadline Cloud. Deadline Cloud then dispatches contiguous frame ranges to workers:

```text
MRQ frame range: 1-10
Default Dynamic Chunk Size: 5

Deadline Cloud scheduler
├── Task chunk: 1-5
└── Task chunk: 6-10
```

When **Target Runtime Seconds** is greater than `0`, the scheduler can adjust the number of frames in later chunks based on observed runtimes. The target is a scheduling hint, not a guaranteed task duration.

Unreal Engine MRQ accepts only contiguous start and end frame overrides, so every dispatched chunk is contiguous. A single-frame chunk is represented as a range such as `5-5`.

## Create the dynamic chunking data assets

Create a render step data asset first, and then add it to a render job data asset.

### 1. Create a dynamic chunking render step

1. In the Unreal Engine Content Browser, create a **Deadline Cloud Render Step** data asset.
2. Name the asset descriptively, such as `DynamicChunkingRenderStep`.
3. Select the following template from the plugin content:

    ```text
    Content/Python/openjd_templates/dynamic_chunking/dynamic_chunking_render_step.yml
    ```

4. Save the data asset.

The template defines the OpenJD `CHUNK[INT]` task parameter used by the scheduler. This parameter might not appear as an editable field in the data asset because Unreal Engine does not have a corresponding value type. Do not add or replace it manually.

### 2. Create a dynamic chunking render job

1. In the Unreal Engine Content Browser, create a **Deadline Cloud Render Job** data asset.
2. Name the asset descriptively, such as `DynamicChunkingRenderJob`.
3. Select the following template from the plugin content:

    ```text
    Content/Python/openjd_templates/dynamic_chunking/dynamic_chunking_render_job.yml
    ```

4. Review the job parameter definitions:

    | Parameter | Description | Action required |
    |-----------|-------------|-----------------|
    | `Frames` | Effective MRQ frame range | Leave unchanged. The submitter populates this value automatically. |
    | `ChunkSize` | Default number of frames in each chunk | Set an initial chunk size. The default is `50`. |
    | `TargetRuntimeSeconds` | Desired runtime for dynamically adjusted chunks | Keep `0` to use `ChunkSize` for all chunks, or set a positive target runtime. |
    | `CondaPackages` | Unreal Engine and adaptor packages used by the worker | Select the correct Unreal Engine version and `unrealengine-openjd` version `0.7.1` or later. |
    | `CondaChannels` | Conda channels containing the required packages | Use the defaults unless your fleet uses custom channels. |
    | `ExtraCmdArgs` | Additional Unreal Engine command-line arguments | Optional. Keep the default for standard setups. |

5. Add `DynamicChunkingRenderStep` to the job asset's **Steps** section.
6. Save the data asset.

## Select the dynamic chunking job preset

You can make the new job asset the default preset for Deadline Cloud MRQ jobs:

1. Open **Edit** > **Project Settings**.
2. Open **Plugins** > **Deadline Cloud**.
3. Under **Deadline Cloud Job Presets**, set **Default Job Preset** to `DynamicChunkingRenderJob`.
4. Close the Project Settings window.

Alternatively, select `DynamicChunkingRenderJob` as the **Job Preset** for an individual job in the MRQ Deadline Cloud settings.

## Submit a dynamically chunked render

1. Open **Window** > **Cinematics** > **Movie Render Queue**.
2. Add the level sequence to render.
3. Configure the MRQ output settings and frame range as usual.
4. Verify that the Deadline Cloud **Job Preset** is `DynamicChunkingRenderJob`.
5. Under **Job Template Overrides**:
    1. Set **Default Dynamic Chunk Size** to the initial number of frames per chunk.
    2. Set **Target Runtime Seconds**:
        - Use `0` for chunks based only on **Default Dynamic Chunk Size**.
        - Use a positive value to let the scheduler adjust later chunk sizes toward that runtime.
    3. Update **Conda Packages** for your Unreal Engine version and `unrealengine-openjd` version `0.7.1` or later, if needed.
6. Choose **Render (Remote)**.
7. Use Deadline Cloud Monitor to follow the job and inspect the frame range assigned to each task.

The submitter derives `Frames` from the MRQ range. You do not need to enter an OpenJD frame expression manually.

## Choose chunking settings

Start with a small test job before tuning a production render.

| Workload | Suggested starting point |
|----------|--------------------------|
| Validate the setup | `ChunkSize` of `5`, `TargetRuntimeSeconds` of `0` |
| Similar render time for every frame | Choose a fixed `ChunkSize` and leave `TargetRuntimeSeconds` at `0` |
| Highly variable frame render times | Choose a reasonable initial `ChunkSize` and set a positive `TargetRuntimeSeconds` |
| Short frames with significant task startup time | Increase `ChunkSize` to reduce task startup overhead |
| Long or unpredictable frames | Decrease `ChunkSize` so work can be distributed more evenly |

A smaller chunk size gives the scheduler more opportunities to balance work, but increases task and Unreal Engine startup overhead. A larger chunk size reduces overhead, but can leave workers idle near the end of a job if one chunk takes much longer than the others.

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Every task renders the full sequence | The worker is using an adaptor version earlier than `0.7.1` | Update `unrealengine-openjd` to version `0.7.1` or later and verify `CondaPackages` or the CMF installation. |
| Dynamic chunking controls are missing | The standard render job preset is selected | Select `DynamicChunkingRenderJob` and verify that it uses `dynamic_chunking_render_job.yml`. |
| Submission reports a missing or invalid `Frames` value | MRQ did not provide a usable frame range, or the submitter version is earlier than `0.7.1` | Verify the MRQ output frame range and update the submitter plugin to version `0.7.1` or later. |
| The job uses unexpected chunk sizes | A positive target runtime allows the scheduler to adjust chunks | Set **Target Runtime Seconds** to `0` to use the default chunk size for all chunks. |
| A Perforce, UGS, or MPQ job does not use dynamic chunking | The provided templates currently cover only the base render workflow | Use the base dynamic chunking job or wait for a dedicated template variant. |

When investigating a task, check its worker log for `Rendering custom frame range` or `Rendering dynamic chunk frame range`. The logged range confirms which frames the scheduler assigned to that worker action.
