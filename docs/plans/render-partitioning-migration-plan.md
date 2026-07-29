# Migration plan: rename render partitioning params, then adopt OpenJD chunking

**Status:** living plan — update as phases land.
**Audience:** maintainers of `deadline-cloud-for-unreal-engine`.

## Background

This integration splits a Movie Render Queue job into OpenJD tasks using two
**submitter-side** parameters (see
[`docs/design/render-task-partitioning.md`](../design/render-task-partitioning.md)).
The parameters were originally named `ChunkSize` (shots per task) and
`FramesPerTask` (frames per task), with `ChunkId` as the per-task index;
the run_data keys on the wire were `chunk_size`/`chunk_id`.

OpenJD has since added a **native, scheduler-level** [task chunking](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0001-task-chunking.md)
feature with its own `ChunkSize` parameter — closer in meaning to our
`FramesPerTask` than to our `ChunkSize`. The shared name was misleading and
blocked adoption of OpenJD's native mode.

The fix is to rename `ChunkSize`→`ShotsPerTask` and `ChunkId`→`TaskIndex`,
then adopt OpenJD chunking. Because the submitter and adaptor are released
independently (run_data keys are their contract), we use an **expand/contract
(parallel-change)** rollout.

## Compatibility model

- Submitter writes run_data keys; adaptor reads them. Key names are the contract.
- **SMF:** adaptor version pinned by `CondaPackages` in the job template.
  As of Phase 2 this default is `unrealengine-openjd=0.7.*` (bumped from
  `0.6.*`); the glob matches the latest 0.7.x patch automatically.
- **Customer-managed fleets:** adaptor pip-installed manually, must be kept version-matched to the
  submitter (per `setup-cmf-worker.md`).
- run_data fields are optional in `run_data.schema.json` (only `handler` is
  required). A mismatch therefore fails **silently with wrong output** (a task
  renders the full sequence instead of its partition), not loudly. This drives
  the per-phase ordering below.

## Version compatibility matrix

The durable copy of this matrix lives in
[`docs/design/render-task-partitioning.md`](../design/render-task-partitioning.md#version-compatibility)
(this plan file is deleted when the project completes). Summary:

| Version | Submitter emits | Adaptor accepts |
|---|---|---|
| 0.6.x (≥ 0.6.10) | legacy names (`chunk_size`/`chunk_id`) | **both** legacy and new |
| 0.7.x | new names (`shots_per_task`/`task_index`) | **both** legacy and new |
| 0.8.x | new names | new names only |

Any submitter/adaptor pairing within one minor version of each other keeps
working, provided a 0.6.x adaptor is at least 0.6.10. The silent wrong-output
failure mode occurs when a 0.7+ submitter's template reaches a pre-0.6.10
adaptor, or a legacy template reaches a 0.8+ adaptor.

## Phases

### Phase 1 — Backwards-compatible adaptor ✅ merged (#324)

- Adaptor uses the new names internally, accepts both legacy
  (`chunk_size`/`chunk_id`) and new (`shots_per_task`/`task_index`) run_data
  keys via `_apply_param_aliases` (new wins). Schema permits all four keys.
- Submitter, templates, and user-facing names are unchanged.
- **Release:** non-breaking (`feat`) — ships as 0.6.10.
- **Exit criterion:** rolled out to fleet (SMF conda channel + customer-managed fleet hosts on
  0.6.10+). ✅ met. After this, any deployed adaptor handles both old and new
  templates.

### Phase 2 — Submitter switches to new names ✅ merged (#338, 0.7.0)

- Rename on submitter side: `OpenJobStepParameterNames`, bundled templates,
  sample scripts, user docs.
- **`CondaPackages` pin bump (final Phase 2 step).** ✅ merged
  ([#343](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/pull/343)).
  With 0.7.0 published to the SMF conda channel and validated, the default
  `CondaPackages` pin was bumped `unrealengine-openjd=0.6.*` → `0.7.*` in the
  render job templates so SMF workers install the 0.7.x adaptor by default.
- **Release:** breaking (`refactor!` + `BREAKING CHANGE:` footer), minor bump
  (0.6 → 0.7).
- **Precondition:** Phase 1 (0.6.10) deployed to the entire fleet. ✅ met.
  A new-names template must never reach a pre-Phase-1 adaptor — it would fail
  silently with wrong output.
- **User migration:** update saved Data Assets, custom templates, and
  submission scripts that reference `ChunkSize`/`ChunkId`; regenerate old job
  bundles. (Find-and-replace details in the Phase-2 PR description.)
  - Includes internal canary/test job bundles that hand-author OpenJD
    templates rather than going through the submitter — these are just as
    exposed to Phase 4 dropping legacy support as any customer template and
    are tracked internally.
- **Exit criterion:** all submitters in use emit new names.

### Phase 3 — Adopt OpenJD native chunking 🚧 in progress (this change)

> **Ordering note:** this phase was previously sequenced *after* dropping
> legacy adaptor support. The two are independent, and removing legacy
> support is disruptive to users still migrating off the old names — so the
> removal is deliberately sequenced last (Phase 4, released as 0.8.0), and
> the new feature work proceeds first on 0.7.x.

A distinct feature unblocked by the rename: add support for OpenJD's
scheduler-level [`CHUNK[INT]` task chunking](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0001-task-chunking.md)
(the `TASK_CHUNKING` extension) as a **third, mutually-exclusive** chunking
mode alongside the existing `ShotsPerTask` (shot-based) and `FramesPerTask`
(frame-based) modes. Chunk boundaries are computed by Deadline Cloud at
dispatch time from a `Frames` integer-range expression, rather than by the
submitter at submission time.

This is independent of the rename phases. Dynamic chunking is new
functionality, added alongside the existing modes, not a replacement for
them.

- **Dependencies:** requires `openjd-model` with `ChunkIntTaskParameterDefinition`
  / `ExtensionName` / `TaskChunksDefinition` support (confirmed present in the
  current dependency set) and `TASK_CHUNKING` extension support on the
  worker-agent / openjd-sessions side of target fleets.
- **Scope constraint:** Unreal's Movie Render Queue only accepts contiguous
  frame ranges via `custom_start_frame`/`custom_end_frame`. Only
  `rangeConstraint: CONTIGUOUS` is supported; `NONCONTIGUOUS` is out of scope
  until MRQ supports non-sequential frame ranges (tracked separately).
- **Template scope:** Phase 3 intentionally ships a **single template pair**
  based on the base render job only
  (`dynamic_chunking/dynamic_chunking_render_job.yml` + `_render_step.yml`).
  Dynamic-chunking variants of the P4, UGS, and MPQ templates are follow-up
  work, not part of this phase. The default submission path is unchanged:
  the standard templates continue to use shots-per-task (`ShotsPerTask`)
  mode, and dynamic chunking is strictly opt-in via the dedicated template.
- **Prior attempt:** [PR #261](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/pull/261)
  implemented this against an older revision of the codebase, before the
  Phase 2 submitter rename landed. Its parameter and method names
  (`ChunkSize`/`ChunkId`/`_get_chunk_ids_count()`/`enable_shots_by_chunk()`/
  `chunk_size`/`chunk_id` run_data keys) are stale — the current codebase
  uses `ShotsPerTask`/`TaskIndex`/`_get_task_count()`/`enable_shots_for_task()`/
  `shots_per_task`/`task_index`. The design and test coverage from #261 are
  reused; every identifier is re-mapped onto current names. The current
  `run_script()` also carries `_apply_task_index_to_filename()`, added after
  #261, which is not present in that PR and must be preserved/extended.
- **Release:** feature (`feat`), non-breaking — ships as a 0.7.x patch.
  Dynamic chunking is opt-in via a new template using the `TASK_CHUNKING`
  extension and `CHUNK[INT]` type; existing `ShotsPerTask`/`FramesPerTask`
  templates are unchanged.
- **Release-ordering caveat:** the dynamic template's
  `unrealengine-openjd=0.7.*` pin resolves to the *latest* 0.7.x. The adaptor
  side of this change (the `dynamic_chunked_frames` run_data key) ships in
  the same release, so the pin is satisfied as soon as that release reaches
  the conda channel — but a fleet that resolves an older 0.7.x (stale cache,
  explicit pin) silently renders the full sequence per chunk. A hard version
  floor (`>=0.7.N`) is not currently expressible: the submitter's
  `normalize_openjd_version_param` only recognizes `=X.Y.Z`-style pins and
  would mangle a `>=` spec (fixing that normalizer is a prerequisite for
  floor pins, tracked as follow-up). Do not promote the dynamic-chunking
  template to users before the containing release is live in the production
  conda channel.
- **Design (mapped onto current names):**
  - New job-level parameters: `OpenJobParameterNames.FRAMES` (`"Frames"`),
    `TARGET_RUNTIME_SECONDS`, `RANGE_CONSTRAINT` (hardcoded `CONTIGUOUS` in
    the bundled template).
  - New step-level task parameter: `OpenJobStepParameterNames.DYNAMIC_CHUNKING`
    (`"DynamicChunking"`, type `CHUNK[INT]`).
  - `DynamicChunkingHelper` (new module,
    `unreal_open_job_dynamic_chunking.py`): detects `CHUNK[INT]` usage in a
    step template, validates `rangeConstraint`/`Frames` format, enforces at
    most one `CHUNK[INT]` parameter per step.
  - `RenderUnrealOpenJobStep._build_template()`: when a step uses dynamic
    chunking, skip `_get_task_count()`/`TaskIndex` range calculation entirely
    (chunk boundaries are computed by the scheduler, not the submitter).
  - `RenderUnrealOpenJob._build_parameter_values()`: populate the `Frames`
    job parameter from the MRQ job's frame range at submission time.
  - Adaptor `UnrealRenderStepHandler.run_script()`: new
    `dynamic_chunked_frames` run_data key, parsed by a new
    `parse_dynamic_chunked_frames()` static method into `(start, end)`, with
    the scheduler's inclusive end converted to Unreal's exclusive
    `custom_end_frame` (`end + 1`). Integrates with, rather than replaces,
    the existing `frames_per_task`/`shots_per_task` branches and
    `_apply_task_index_to_filename()`.
  - New bundled template pair:
    `dynamic_chunking/dynamic_chunking_render_job.yml` and
    `dynamic_chunking_render_step.yml`, added alongside the existing
    `render_job.yml`/`render_step.yml` (opt-in, not a replacement).
  - `open_job_template_api.py`: skip parameter types unsupported by Unreal's
    `ValueType` enum (i.e. `CHUNK[INT]`) when converting step parameters for
    the Data Asset UI, rather than erroring.
- **Exit criterion:** a dynamic-chunking template renders correctly end to
  end (unit tests + e2e job submission), with the legacy `ShotsPerTask`/
  `FramesPerTask` templates unaffected and their existing tests still green.

### Phase 4 — Drop legacy support from the adaptor, release 0.8 ⏸️ deferred

> **Ordering note:** deliberately sequenced **last** (previously Phase 3).
> Removing the legacy aliases is disruptive to any user still on the old
> names, and it fails **silently** (a stale template renders the full
> sequence instead of its partition, with no error). Deferring it behind the
> dynamic-chunking feature work gives users the entire 0.7.x line as a
> migration window, and makes the cut-over an explicit, plannable minor
> release (0.8.0) rather than a change folded in alongside other work.

- Remove `_apply_param_aliases` and the legacy `chunk_size`/`chunk_id` keys
  from `run_data.schema.json`.
  - Not doing (out of scope): setting `additionalProperties: false`. The
    schema is currently missing `frames_per_task` (a live, actively-used key
    emitted by the bundled templates), so locking down `additionalProperties`
    now would newly reject it. That requires a separate audit of every
    emitted run_data key before it can be enabled safely.
- **Release: 0.8.0** — breaking (`refactor!` + `BREAKING CHANGE:` footer),
  minor bump (0.7 → 0.8). After this release the rename is complete on both
  sides: the submitter emits only new names (since 0.7.0) and the adaptor
  accepts only new names. Follow with a `CondaPackages` default pin bump
  `unrealengine-openjd=0.7.*` → `0.8.*` once 0.8 is validated in the
  production conda channel (same gated two-step as the Phase 2 pin bump).
- **Preconditions (⛔ not yet met):**
  - No submitter in use emits legacy names; no old job bundles in flight.
  - All internal test/canary bundles across all DCC integrations (not just
    Unreal) audited for hand-authored legacy names (tracked internally).
  - A soak period on 0.7.x with no observed legacy-name usage, or an
    explicit customer communication + waiting period.
  - Re-review these preconditions with the team before merging.
- **Status: deferred, deliberately not merging yet.** The implementation
  branch that previously existed for this work has since been removed while
  the hold is in effect; re-create it from this plan when resuming.
- **Exit criterion:** 0.8.0 released; rename complete in both submitter and
  adaptor.

## Sequencing summary

```
Phase 1  feat       adaptor accepts both names           (non-breaking)  ✅ merged (#324, 0.6.10)
   |       fleet rolled out to 0.6.10  ✅
Phase 2  refactor!  submitter emits new names            (breaking, 0.7.0) ✅ merged (#338)
   |       0.7.0 deployed to all production environments  ✅
   |       + default CondaPackages pin bump 0.6.* -> 0.7.*  ✅ merged (#343)
   |       all submitters updated
Phase 3  feat       adopt OpenJD native chunking         (non-breaking, 0.7.x) 🚧 this change
   |
Phase 4  refactor!  adaptor drops legacy-name support    (breaking, 0.8.0) ⏸️ DEFERRED
           preconditions not met: cannot yet confirm no legacy-name
           submitters/bundles remain in flight
```

End state by version: **0.6** — old names in the submitter, adaptor accepts
both; **0.7** — new names in the submitter, adaptor accepts both; **0.8** —
new names in both submitter and adaptor.

Don't collapse phases: skipping Phase 1's fleet rollout before Phase 2, or
Phase 2's rollout before Phase 4's legacy removal, reintroduces the silent
wrong-output failure this plan exists to avoid.
