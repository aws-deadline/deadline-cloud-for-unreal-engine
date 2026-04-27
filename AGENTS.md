# AGENTS.md — deadline-cloud-for-unreal-engine

## Post-Change Validation

After making ANY code changes, you MUST run:
1. `hatch run fmt` — auto-format
2. `hatch run lint` — ruff + mypy
3. `hatch build` — verify the package builds
4. `hatch run test` — run ALL unit tests (do NOT use `pytest` directly, do NOT pass specific test files)

To run targeted tests: `hatch run test -- test/<dir> -v` or `hatch run test -- -k "test_name"`

**UE Automation (Spec) GUI Tests:** Require a running Unreal Editor instance. **Do NOT run** — they must be run manually by a human developer.

**E2E Tests:** Require AWS Deadline Cloud authentication and real cloud resources. **Do NOT run** — they must be run manually by a human developer.

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
