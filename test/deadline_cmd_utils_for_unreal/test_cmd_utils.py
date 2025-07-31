# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import pytest

from deadline.unreal_cmd_utils import (
    merge_cmd_args_with_priority,
    parse_command_line,
)


# ──────────────────────────────────────────────────────────────
# Tokens and flags: deduplication + higher‑priority override
# ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "lower, higher, exp_tokens, exp_switches",
    [
        (
            "MapA MapB -fullscreen -flag1",
            "MapB MapC -Flag1 -novsync",
            {"mapa", "mapb", "mapc"},
            {"fullscreen", "flag1", "novsync"},
        ),
        (
            "Token -DEBUG",
            "token -debug -someOther",
            {"token"},
            {"debug", "someother"},
        ),
    ],
)
def test_merge_tokens_and_switches(lower, higher, exp_tokens, exp_switches):
    """Ensure tokens and switches are case‑insensitively deduplicated,
    and switches from the higher‑priority string win."""
    merged = merge_cmd_args_with_priority(higher, lower)
    tokens, switches, _ = parse_command_line(merged)

    assert {t.lower() for t in tokens} == exp_tokens
    assert {s.lower() for s in switches} == exp_switches


# ──────────────────────────────────────────────────────────────
# Standard key=value pairs: higher priority wins
# ──────────────────────────────────────────────────────────────
def test_merge_key_value_priority():
    lower = "-Foo=lower -Bar=willLose"
    higher = "-bar=Override -Baz=New"

    _, _, params = parse_command_line(merge_cmd_args_with_priority(higher, lower))

    assert params == {
        "Foo": "lower",  # from lower‑priority string
        "bar": "Override",  # overridden by higher‑priority string
        "Baz": "New",
    }


# ──────────────────────────────────────────────────────────────
# DPCVars: merge lists, higher‑priority CVar values override
# ──────────────────────────────────────────────────────────────
def test_merge_dpcvars():
    lower = '-DPCVars="r.ShadowQuality=2,r.ViewDistanceScale 4"'
    higher = '-DPCVars="p.FogDensity 0.3,r.ShadowQuality 4"'

    _, _, params = parse_command_line(merge_cmd_args_with_priority(higher, lower))

    # The order is preserved by first appearance; r.ShadowQuality taken from higher.
    assert params["DPCVars"] == ("r.ShadowQuality=4," "r.ViewDistanceScale=4," "p.FogDensity=0.3")


# ──────────────────────────────────────────────────────────────
# ExecCmds: merge lists, duplicates removed by first word
# ──────────────────────────────────────────────────────────────
def test_merge_execcmds():
    lower = '-ExecCmds="stat fps, toggledebugcamera"'
    higher = '-ExecCmds="stat fps, r.SetNearClipPlane 1"'

    _, _, params = parse_command_line(merge_cmd_args_with_priority(higher, lower))

    assert params["ExecCmds"] == "stat fps,toggledebugcamera,r.SetNearClipPlane 1"


# ──────────────────────────────────────────────────────────────
# Auto‑quoting for values containing spaces or commas
# ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "arg_string, expected_fragment",
    [
        ('-Option="Has Spaces"', '-Option="Has Spaces"'),
        ("-Option=comma,separated", '-Option="comma,separated"'),
        ('-Option="both , things"', '-Option="both , things"'),
    ],
)
def test_quote_if_needed(arg_string, expected_fragment):
    merged = merge_cmd_args_with_priority(arg_string, "")
    assert expected_fragment in merged


# ──────────────────────────────────────────────────────────────
# None and/or empty strings as inputs
# ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "higher, lower, exp_tokens, exp_switches, exp_params",
    [
        (None, None, set(), set(), {}),
        ("", "", set(), set(), {}),
        (None, "MapA -Flag", {"mapa"}, {"flag"}, {}),
        ("MapA -Flag", None, {"mapa"}, {"flag"}, {}),
        ("", "-Opt=Val", set(), set(), {"Opt": "Val"}),
    ],
)
def test_none_or_empty_inputs(higher, lower, exp_tokens, exp_switches, exp_params):
    """Both None and empty strings should be treated as empty command lines."""
    merged = merge_cmd_args_with_priority(higher, lower)
    tokens, switches, params = parse_command_line(merged)

    assert {t.lower() for t in tokens} == exp_tokens
    assert {s.lower() for s in switches} == exp_switches
    assert params == exp_params


# ──────────────────────────────────────────────────────────────
# Empty value in lower‑priority string overridden by non‑empty
# ──────────────────────────────────────────────────────────────
def test_empty_overridden_by_nonempty():
    merged = merge_cmd_args_with_priority("-Setting=foo", "-Setting=")
    _, switches, params = parse_command_line(merged)

    assert "Setting" not in switches
    assert params["Setting"] == "foo"  # value comes from higher string


# ──────────────────────────────────────────────────────────────
# Non‑empty value overridden by empty in higher string
# ──────────────────────────────────────────────────────────────
def test_nonempty_overridden_by_empty():
    merged = merge_cmd_args_with_priority("-Setting=", "-Setting=bar")
    _, switches, params = parse_command_line(merged)

    assert "Setting" not in switches
    assert params["Setting"] == ""


# ──────────────────────────────────────────────────────────────
# Both inputs empty or None → merged result is empty string
# ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("higher, lower", [("", ""), (None, ""), ("", None), (None, None)])
def test_both_inputs_empty_result_empty_string(higher, lower):
    assert merge_cmd_args_with_priority(higher, lower) == ""
