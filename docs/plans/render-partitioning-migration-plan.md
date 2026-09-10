# Migration plan: rename render partitioning params, then adopt OpenJD chunking

**Status:** Phases 1–3 complete; Phase 4 in progress.
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
  Phase 4 updates this default from `unrealengine-openjd=0.7.*` to `1.0.*`;
  the glob matches the latest 1.0.x patch automatically.
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
| 1.0.x | new names | new names only |

Any submitter/adaptor pairing within one minor version of each other keeps
working, provided a 0.6.x adaptor is at least 0.6.10. The silent wrong-output
failure mode occurs when a 0.7+ submitter's template reaches a pre-0.6.10
adaptor, or a legacy template reaches a 1.0+ adaptor.

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

### Phase 3 — Adopt OpenJD native chunking ✅ complete (#353, 0.7.1)

- Added OpenJD's scheduler-level [`CHUNK[INT]` task chunking](https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0001-task-chunking.md)
  as a third, opt-in mode alongside `ShotsPerTask` and `FramesPerTask`.
  Deadline Cloud computes contiguous frame chunks at dispatch time from the
  submitted `Frames` range.
- Unreal's Movie Render Queue only supports contiguous frame ranges, so the
  integration requires `rangeConstraint: CONTIGUOUS`.
- The feature ships as one dedicated base render template pair under
  `openjd_templates/dynamic_chunking`; the existing templates and default
  submission path are unchanged.
- The submitter populates and validates `Frames`, while the adaptor applies
  scheduler-provided `dynamic_chunked_frames` ranges to MRQ. Follow-up fixes
  and user documentation landed in #355 and #356.
- **Release/status:** released in 0.7.1 on July 29, 2026. Dynamic chunking
  rendered correctly with 0.7.1 in Gamma; the broader 0.7.1 rollout continues
  as of July 30, 2026.
- **Exit criterion:** ✅ met — dynamic chunking rendered successfully end to
  end, and the existing `ShotsPerTask`/`FramesPerTask` tests remain green.

### Phase 4 — Drop legacy support from the adaptor, release 1.0 🚧 in progress (this change)

- Remove `_apply_param_aliases` and the legacy `chunk_size`/`chunk_id` fields
  from `run_data.schema.json`. The adaptor reads only `shots_per_task` and
  `task_index` after this change.
  - `additionalProperties: false` remains out of scope. The schema still does
    not enumerate every live run_data key, including `frames_per_task`, so
    enabling it requires a separate audit.
- **Migration impact:** legacy templates and saved job bundles that still emit
  `chunk_size`/`chunk_id` must be updated before using the 1.0.x adaptor.
  Otherwise, partitioning is silently skipped and each task can render the
  full sequence.
- **Release:** 1.0.0 — breaking (`refactor!` + `BREAKING CHANGE:` footer),
  major bump (0.7 → 1.0). The bundled templates pin
  `unrealengine-openjd=1.0.*`; public publication waits for the matching
  Windows Conda adaptor to complete production verification.
- **Status:** implementation is in progress in this change; 0.7.x remains the
  compatibility window where the adaptor accepts both legacy and new names.
- **Exit criterion:** 1.0.0 released and the default adaptor pin promoted to
  1.0.x; the submitter and adaptor then use only the new names.

## Sequencing summary

```
Phase 1  feat       adaptor accepts both names           (non-breaking)  ✅ merged (#324, 0.6.10)
   |       fleet rolled out to 0.6.10  ✅
Phase 2  refactor!  submitter emits new names            (breaking)      ✅ merged (#338, 0.7.0)
   |       default CondaPackages pin 0.6.* -> 0.7.*       ✅ merged (#343)
Phase 3  feat       adopt OpenJD native chunking         (non-breaking)  ✅ complete (#353, 0.7.1)
   |       Gamma render succeeded; 0.7.1 rollout continues as of 2026-07-30
Phase 4  refactor!  adaptor drops legacy-name support    (breaking)      🚧 this change (1.0.0)
```

End state by version: **0.6** — old names in the submitter, adaptor accepts
both; **0.7** — new names in the submitter, adaptor accepts both; **1.0** —
new names in both submitter and adaptor.

The expand/contract ordering remains important: Phase 1's adaptor rollout
preceded the Phase 2 submitter rename, and the 0.7.x line provided the
migration window before Phase 4 removes legacy support.
