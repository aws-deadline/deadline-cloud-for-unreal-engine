# AGENTS.md — deadline-cloud-for-unreal-engine

For project architecture and component relationships, use the `ue-architecture` skill.

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

- The `unreal` module is **never** available in tests — always mock it
- All test files **MUST** start with `# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.`
- Coverage threshold: 65%

## Commit Messages

Always sign commits: `git commit -s`

Use conventional commits:
- `feat:` — new features
- `fix:` — bug fixes
- `docs:` — documentation
- `test:` — tests only
- `refactor:` — code refactoring
- `perf:` — performance improvements
- `feat!:` or `fix!:` — breaking changes (include `BREAKING CHANGES:` in message body)

## Design Docs for Major Changes

For new features or major refactors, use the `design-doc` skill. This does NOT apply to small bug fixes.

UE-specific additions to the standard design process:
- Use the `ue-architecture` skill to understand component boundaries and where code should go
- Use the `openjd-template` skill when the feature involves OpenJD templates
- Reference UE docs when the feature touches Unreal Engine APIs:
  - UE C++ API: https://dev.epicgames.com/documentation/en-us/unreal-engine/API
  - UE Python API: https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api
- Check backwards compatibility — if breaking changes are needed, include version bump and migration plan in the implementation plan
- Consider security implications and call them out explicitly
- Research options, present tradeoffs, and ask follow-up questions before committing to an approach
- Save design docs in `docs/designs/`
