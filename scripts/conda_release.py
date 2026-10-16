# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Bind the Conda approval to the staged release in this workflow attempt."""

import argparse
import json
import os
import re
from pathlib import Path

PACKAGE = "unrealengine-openjd"
PLATFORMS = ["win-64"]


def validate_metadata(metadata):
    """Reject incomplete release identities before creating or trusting an approval."""
    if metadata.get("schema_version") != 1:
        raise ValueError("Unsupported release metadata schema")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", metadata["repository"]):
        raise ValueError("Invalid repository")
    for key in ("run_id", "run_attempt"):
        if type(metadata[key]) is not int or metadata[key] < 1:
            raise ValueError(f"Invalid {key}")
    if not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", metadata["tag"]):
        raise ValueError("A stable release tag is required")
    if metadata["version"] != metadata["tag"]:
        raise ValueError("Release tag and Conda version differ")
    if not re.fullmatch(r"[0-9a-f]{40}", metadata["source_commit"]):
        raise ValueError("An immutable release commit is required")
    if metadata["package_name"] != PACKAGE or metadata["required_platforms"] != PLATFORMS:
        raise ValueError("Unexpected Conda package or platforms")


def release_metadata(environ):
    """Create metadata only after the workflow has successfully staged the release."""
    metadata = {
        "schema_version": 1,
        "repository": environ["GITHUB_REPOSITORY"],
        "run_id": int(environ["GITHUB_RUN_ID"]),
        "run_attempt": int(environ["GITHUB_RUN_ATTEMPT"]),
        "tag": environ["RELEASE_TAG"],
        "version": environ["RELEASE_TAG"],
        "package_name": PACKAGE,
        "required_platforms": PLATFORMS,
        "source_commit": environ["SOURCE_COMMIT"],
    }
    validate_metadata(metadata)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["metadata"])
    parser.add_argument("metadata", type=Path)
    args = parser.parse_args()
    args.metadata.write_text(json.dumps(release_metadata(os.environ), indent=2) + "\n")


if __name__ == "__main__":
    main()
