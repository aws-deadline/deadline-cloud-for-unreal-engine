# AGENTS.md — unreal_cmd_utils

## Overview

Utilities for parsing and merging Unreal Engine command-line arguments. Used by the adaptor to combine user-specified and default CLI flags.

## Key files

- `cmd_utils.py` — `parse_command_line()` and `merge_cmd_args_with_priority()` for UE CLI string manipulation
- `__init__.py` — Re-exports `merge_cmd_args_with_priority`

## Important context

- Handles UE-specific special keys like `dpcvars` and `execcmds` that require special quoting
- Uses `shlex` for tokenization
- Higher-priority args override lower-priority args when keys conflict

