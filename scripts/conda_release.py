# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Bind the Conda approval to the staged release in this workflow attempt."""

import argparse
import json
import os
import re
import urllib.request
from pathlib import Path

PACKAGE = "unrealengine-openjd"
PLATFORMS = ["win-64"]
MANIFEST_URL = "https://downloads.deadlinecloud.amazonaws.com/conda/manifest.json"


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


def verify_approval(metadata, pages, app_id, environ):
    """Require the configured App's completed approval for exactly this run attempt."""
    validate_metadata(metadata)
    expected = (
        environ["GITHUB_REPOSITORY"],
        int(environ["GITHUB_RUN_ID"]),
        int(environ["GITHUB_RUN_ATTEMPT"]),
    )
    actual = (metadata["repository"], metadata["run_id"], metadata["run_attempt"])
    if actual != expected:
        raise ValueError("Release metadata belongs to a different workflow attempt")
    if app_id < 1:
        raise ValueError("The Conda release App ID is not configured")
    external_id = f"conda-release:{metadata['run_id']}:{metadata['run_attempt']}"
    matches = [
        check
        for page in pages
        for check in page["check_runs"]
        if check.get("external_id") == external_id and check.get("app", {}).get("id") == app_id
    ]
    if len(matches) != 1:
        raise ValueError("Expected one Conda approval check from the configured App")
    check = matches[0]
    if (
        check.get("status") != "completed"
        or check.get("conclusion") != "success"
        or check.get("head_sha") != environ["GITHUB_SHA"]
    ):
        raise ValueError("The Conda App has not approved this workflow attempt")
    state = json.loads(check["output"]["summary"])
    if state.get("approved") is not True or state.get("release") != metadata:
        raise ValueError("The Conda approval does not match the staged release")


def verify_manifest(metadata, manifest):
    """Recheck exact public availability immediately before public release work."""
    entry = manifest.get("packages", {}).get(PACKAGE, {}).get(metadata["version"], {})
    if not all(platform in entry.get("platforms", []) for platform in PLATFORMS):
        raise ValueError(
            f"Conda manifest does not contain {PACKAGE} {metadata['version']} for win-64"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["metadata", "verify"])
    parser.add_argument("metadata", type=Path)
    parser.add_argument("checks", type=Path, nargs="?")
    args = parser.parse_args()
    if args.command == "metadata":
        args.metadata.write_text(json.dumps(release_metadata(os.environ), indent=2) + "\n")
    else:
        if args.checks is None:
            parser.error("verify requires a checks JSON file")
        metadata = json.loads(args.metadata.read_text())
        verify_approval(
            metadata,
            json.loads(args.checks.read_text()),
            int(os.environ["CONDA_RELEASE_APP_ID"]),
            os.environ,
        )
        with urllib.request.urlopen(MANIFEST_URL, timeout=30) as response:
            verify_manifest(metadata, json.load(response))
        print(f"Approved: {PACKAGE} {metadata['version']} for win-64")


if __name__ == "__main__":
    main()
