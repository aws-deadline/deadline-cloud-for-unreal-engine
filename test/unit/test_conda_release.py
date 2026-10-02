# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Metadata supplied to the Conda release gate."""

import importlib.util
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
    return env


def test_metadata_records_staged_release(identity):
    metadata = conda_release.release_metadata(identity)
    assert metadata == {
        "schema_version": 1,
        "repository": identity["GITHUB_REPOSITORY"],
        "run_id": 123,
        "run_attempt": 2,
        "tag": "1.2.3",
        "version": "1.2.3",
        "package_name": "unrealengine-openjd",
        "required_platforms": ["win-64"],
        "source_commit": identity["SOURCE_COMMIT"],
    }


@pytest.mark.parametrize("tag", ["", "../mainline", "1.2", "v1.2.3", "1.2.3-rc.1", "01.2.3"])
def test_rejects_nonrelease_tags(identity, tag):
    env = identity
    env["RELEASE_TAG"] = tag
    with pytest.raises(ValueError, match="stable release tag"):
        conda_release.release_metadata(env)
