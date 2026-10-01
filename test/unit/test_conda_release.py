# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Release gate regression tests; no AWS or GitHub requests."""

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest


spec = importlib.util.spec_from_file_location(
    "conda_release", Path(__file__).parents[2] / "scripts" / "conda_release.py"
)
assert spec is not None and spec.loader is not None
conda_release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(conda_release)


@pytest.fixture
def identity():
    env = {
        "GITHUB_REPOSITORY": "aws-deadline/deadline-cloud-for-unreal-engine",
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "2",
        "GITHUB_SHA": "a" * 40,
        "RELEASE_TAG": "1.2.3",
        # Dispatching an older tag can have a different workflow head.
        "SOURCE_COMMIT": "b" * 40,
    }
    metadata = conda_release.release_metadata(env)
    check = {
        "external_id": "conda-release:123:2",
        "app": {"id": 456},
        "head_sha": env["GITHUB_SHA"],
        "status": "completed",
        "conclusion": "success",
        "output": {"summary": json.dumps({"approved": True, "release": metadata})},
    }
    return env, metadata, check


def test_accepts_bound_approval_on_later_checks_page(identity):
    env, metadata, check = identity
    conda_release.verify_approval(metadata, [{"check_runs": []}, {"check_runs": [check]}], 456, env)


@pytest.mark.parametrize(
    "field,value",
    [
        ("external_id", "conda-release:123:1"),
        ("app", {"id": 789}),
        ("status", "in_progress"),
        ("conclusion", "failure"),
        ("head_sha", "c" * 40),
        ("output", {"summary": json.dumps({"approved": True, "release": {}})}),
        ("output", {"summary": json.dumps({"approved": False})}),
    ],
)
def test_rejects_untrusted_or_incomplete_approval(identity, field, value):
    env, metadata, check = identity
    check[field] = value
    with pytest.raises(ValueError):
        conda_release.verify_approval(metadata, [{"check_runs": [check]}], 456, env)


@pytest.mark.parametrize("checks", [[], "duplicate"])
def test_missing_or_ambiguous_app_rule_cannot_publish(identity, checks):
    env, metadata, check = identity
    checks = [check, deepcopy(check)] if checks == "duplicate" else checks
    with pytest.raises(ValueError):
        conda_release.verify_approval(metadata, [{"check_runs": checks}], 456, env)


def test_previous_attempt_metadata_cannot_publish(identity):
    env, metadata, check = identity
    env["GITHUB_RUN_ATTEMPT"] = "3"
    with pytest.raises(ValueError, match="different workflow attempt"):
        conda_release.verify_approval(metadata, [{"check_runs": [check]}], 456, env)


@pytest.mark.parametrize("tag", ["", "../mainline", "1.2", "v1.2.3", "1.2.3-rc.1", "01.2.3"])
def test_rejects_nonrelease_tags(identity, tag):
    env, _, _ = identity
    env["RELEASE_TAG"] = tag
    with pytest.raises(ValueError, match="stable release tag"):
        conda_release.release_metadata(env)


@pytest.mark.parametrize(
    "versions,ready",
    [
        ({}, False),
        ({"1.2.2": {"platforms": ["win-64"]}}, False),
        ({"1.2.3": {"platforms": ["linux-64"]}}, False),
        ({"1.2.3": {"platforms": ["linux-64", "win-64"]}}, True),
    ],
)
def test_manifest_requires_exact_version_and_platform(identity, versions, ready):
    _, metadata, _ = identity
    manifest = {"packages": {"unrealengine-openjd": versions}}
    if ready:
        conda_release.verify_manifest(metadata, manifest)
    else:
        with pytest.raises(ValueError, match="manifest does not contain"):
            conda_release.verify_manifest(metadata, manifest)
