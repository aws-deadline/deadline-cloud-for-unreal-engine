# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from collections import OrderedDict
from deadline.unreal_logger import get_logger

import shlex

logger = get_logger()

SPECIAL_KEYS = {"dpcvars", "execcmds"}
NEED_QUOTE_CHARS = set(" ,;")


def parse_command_line(cmd_line: str):
    tokens = []
    switches = []
    params = {}

    cmd_line = cmd_line or ""
    args = shlex.split(cmd_line)

    for arg in args:
        if arg.startswith("-"):
            stripped = arg.lstrip("-")
            if "=" in stripped:
                key, value = stripped.split("=", 1)
                value = value.strip('"').strip("'")
                params[key] = value
            else:
                switches.append(stripped)
        else:
            tokens.append(arg)

    return tokens, switches, params


def merge_cmd_args_with_priority(higher_priority_args: str, lower_priority_args: str) -> str:
    """
    Merge two Unreal‑Engine CLI strings, letting *higher_priority_args* win.

    • Positional tokens and flags are deduped (case‑insensitive).
    • Key‑value pairs: duplicates keep the value from *higher*.
    • -DPCVars   → lists combined, CVars from *higher* override.
    • -ExecCmds  → lists concatenated, dups removed by command name.
    • Values with spaces/commas/, are auto‑quoted.

    Returns the merged command string, on parse failure logs and
    yields an empty string.
    """

    def _parse_list(value: str):
        return [x.strip() for x in value.strip("\"' ").split(",") if x.strip()]

    def _merge_execcmds(v1, v2):
        def first_word(cmd):
            return cmd.split()[0].lower() if cmd else ""

        merged = OrderedDict()
        for cmd in _parse_list(v1) + _parse_list(v2):
            merged[first_word(cmd)] = cmd
        return ",".join(merged.values())

    def _merge_dpcvars(v1, v2):
        def pairs(lst):
            for item in lst:
                if "=" in item:
                    n, val = item.split("=", 1)
                else:
                    n, val = item.split(None, 1)
                yield n.strip().lower(), n.strip(), val.strip()

        merged = OrderedDict()
        for norm, name, val in pairs(_parse_list(v1) + _parse_list(v2)):
            merged[norm] = (name, val)
        return ",".join(f"{name}={val}" for _, (name, val) in merged.items())

    def _quote_if_needed(val: str):
        if any(c in NEED_QUOTE_CHARS for c in val):
            escaped = val.replace('"', r"\"")
            return f'"{escaped}"'
        return val

    try:
        t1, s1, kv1 = parse_command_line(lower_priority_args)

    except Exception:
        logger.error(f"Failed to parse command line arguments: {lower_priority_args}")
        return ""

    try:
        t2, s2, kv2 = parse_command_line(higher_priority_args)

    except Exception:
        logger.error(f"Failed to parse command line arguments: {higher_priority_args}")
        return ""

    tokens = []
    seen_tokens = set()
    for t in t1 + t2:
        if t.lower() not in seen_tokens:
            tokens.append(t)
            seen_tokens.add(t.lower())

    flags = {f.lower(): f for f in s1}
    flags.update({f.lower(): f for f in s2})
    switches = list(flags.values())

    out = {}
    for k, v in kv1.items():
        out[k.lower()] = (k, v)
    for k, v in kv2.items():
        lk = k.lower()
        if lk in SPECIAL_KEYS and lk in out:
            v = _merge_dpcvars(out[lk][1], v) if lk == "dpcvars" else _merge_execcmds(out[lk][1], v)
        out[lk] = (k, v)
    key_vals = {orig: val for orig, val in out.values()}

    parts = []
    parts.extend(tokens)
    parts.extend(f"-{flag}" for flag in switches)
    for key, val in key_vals.items():
        if val == "":
            parts.append(f"-{key}=")
        else:
            parts.append(f"-{key}={_quote_if_needed(val)}")
    return " ".join(parts)
