# AGENTS.md — deadline-cloud-for-unreal-engine

## ⚠️ Before You Commit

**Every commit MUST be signed off.** Use `git commit -s` — the DCO check will
block any PR that contains an unsigned commit. See
[Commit Messages](#commit-messages) below for the full format.

## Build

```bash
hatch build
```

## Tests

You **MUST** use `hatch run test` to run unit tests — do NOT use `pytest` directly.

```bash
hatch run test                    # All unit tests
hatch run test -- test/<dir> -v   # One test package
hatch run test -- -k "test_name"  # One test by name
```

**UE Automation (Spec) GUI Tests:** Require installing the plugin with test content first:
```bash
python scripts/build_plugin.py --install --test
```
Then in UE: Tools → Test Automation → search "Deadline" → run.

**E2E Tests:** Require authentication with AWS Deadline Cloud and are resource-intensive. You **SHOULD** only run E2E tests when all unit tests pass and you are about to finalize the change set.
```bash
hatch run e2e -s
```

## Linting

```bash
hatch run lint    # ruff + mypy
hatch run fmt     # black auto-format
```

## Testing Conventions
- See `test/AGENTS.md` for detailed test structure and patterns

## Commit Messages

**IMPORTANT:** All commits MUST be signed off. Always use `git commit -s` (never `git commit` without `-s`). PRs with unsigned commits will be blocked.

Use conventional commits:
- `feat:` — new features
- `fix:` — bug fixes
- `docs:` — documentation
- `test:` — tests only
- `refactor:` — code refactoring
- `perf:` — performance improvements
- `feat!:` or `fix!:` — breaking changes (include `BREAKING CHANGES:` in message body)

## Design Docs for Major Changes

For new features or major refactors, use the `ue-design` skill. This does NOT apply to small bug fixes.

## Dependency Version Bumps

When bumping versions in `pyproject.toml`, also update `PythonRequirements` in `src/unreal_plugin/UnrealDeadlineCloudService.uplugin`. UE's PipInstall caches packages in `<project>/Intermediate/PipInstall/` and won't auto-upgrade transitive dependencies, causing silent import failures if they go stale. Pin critical transitive dependencies (e.g. `typing_extensions>=4.14.1` required by `pydantic`) explicitly in the `.uplugin`.

## Architecture

C++ and Python integration enabling Unreal Movie Render Queue job submission to AWS Deadline Cloud and worker-side rendering via OpenJD adaptors. Each component has its own `AGENTS.md` with detailed context.

```
  SUBMITTER WORKSTATION                         WORKER NODE
 ┌──────────────────────┐                     ┌──────────────────────┐
 │  UE Editor           │                     │  unreal_adaptor      │
 │  ├─ C++ Plugin       │   OpenJD Job Bundle │  ├─ UnrealAdaptor/   │
 │  ├─ Content/Python/  │ ──────────────────► │  └─ UnrealClient/    │
 │  └─ unreal_submitter │                     │                      │
 └──────────────────────┘                     │  unreal_perforce_utils│
                                              │  unreal_cmd_utils    │
                                              │  unreal_logger       │
                                              └──────────────────────┘
```

### External References

- **UE C++ API:** https://dev.epicgames.com/documentation/en-us/unreal-engine/API
- **UE Python API:** https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api
- For OpenJD template work, use the `openjd-template` skill
