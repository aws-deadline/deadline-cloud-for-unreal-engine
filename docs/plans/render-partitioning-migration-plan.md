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
- **CMF:** adaptor pip-installed manually, must be kept version-matched to the
  submitter (per `setup-cmf-worker.md`).
- run_data fields are optional in `run_data.schema.json` (only `handler` is
  required). A mismatch therefore fails **silently with wrong output** (a task
  renders the full sequence instead of its partition), not loudly. This drives
  the per-phase ordering below.

## Phases

### Phase 1 — Backwards-compatible adaptor ✅ merged (#324)

- Adaptor uses the new names internally, accepts both legacy
  (`chunk_size`/`chunk_id`) and new (`shots_per_task`/`task_index`) run_data
  keys via `_apply_param_aliases` (new wins). Schema permits all four keys.
- Submitter, templates, and user-facing names are unchanged.
- **Release:** non-breaking (`feat`) — ships as 0.6.10.
- **Exit criterion:** rolled out to fleet (SMF conda channel + CMF hosts on
  0.6.10+). ✅ met. After this, any deployed adaptor handles both old and new
  templates.

### Phase 2 — Submitter switches to new names ✅ merged (#338, 0.7.0)

- Rename on submitter side: `OpenJobStepParameterNames`, bundled templates,
  sample scripts, user docs.
- **`CondaPackages` pin bump (final Phase 2 step).** With 0.7.0 published to
  the SMF conda channel and validated, the default `CondaPackages` pin is
  bumped `unrealengine-openjd=0.6.*` → `0.7.*` in the render job templates
  (this change) so SMF workers install the 0.7.x adaptor by default. This
  merge is gated on 0.7 being available in the production conda channel — a
  new-names default must not resolve on a fleet that lacks a Phase-1+ adaptor.
- **Release:** breaking (`refactor!` + `BREAKING CHANGE:` footer), minor bump
  (0.6 → 0.7).
- **Precondition:** Phase 1 (0.6.10) deployed to the entire fleet. ✅ met.
  A new-names template must never reach a pre-Phase-1 adaptor — it would fail
  silently with wrong output.
- **User migration:** update saved Data Assets, custom templates, and
  submission scripts that reference `ChunkSize`/`ChunkId`; regenerate old job
  bundles. (Find-and-replace details in the Phase-2 PR description.)
- **Status:** submitter rename merged and released as 0.7.0; adaptor 0.7 built
  and validated in the conda channel's pre-production stage; production
  promotion in progress; default `CondaPackages` pin bump prepared (this
  change), to merge once 0.7 reaches the production channel.
- **Exit criterion:** all submitters in use emit new names.

### Phase 3 — Drop legacy support from the adaptor

- Remove `_apply_param_aliases` and the legacy keys from
  `run_data.schema.json`. Optionally set `additionalProperties: false` so a
  stale legacy template fails loudly at validation.
- **Release:** breaking (`refactor!` + `BREAKING CHANGE:` footer).
- **Precondition:** no submitter in use emits legacy names; no old job bundles
  in flight.
- **Exit criterion:** rename complete.

### Phase 4 — Adopt OpenJD native chunking (separate feature track)

A distinct feature unblocked by the rename: replace `FramesPerTask` with
OpenJD's scheduler-level `CHUNK[INT]` task chunking, where chunks are formed at
dispatch time rather than at submission. `ShotsPerTask` likely remains
submitter-side since OpenJD chunking operates on integer ranges, not shot
lists.

- **Dependencies:** requires `TASK_CHUNKING` extension support in
  worker-agent / openjd-sessions on target fleets.
- **Release:** feature (`feat`); potentially breaking depending on whether
  `FramesPerTask` is kept as an alias or removed.

## Sequencing summary

```
Phase 1  feat       adaptor accepts both names           (non-breaking)  ✅ merged (#324, 0.6.10)
   |       fleet rolled out to 0.6.10  ✅
Phase 2  refactor!  submitter emits new names            (breaking)      ✅ merged (#338, 0.7.0)
   |       + default CondaPackages pin bumped 0.6.* -> 0.7.*  <-- this change
   |       all submitters updated
Phase 3  refactor!  adaptor drops legacy-name support    (breaking)
   |
Phase 4  feat       adopt OpenJD native chunking         (feature)      independent track
```

Don't collapse phases: skipping Phase 1's fleet rollout before Phase 2, or
Phase 2's rollout before Phase 3, reintroduces the silent wrong-output failure
this plan exists to avoid.
