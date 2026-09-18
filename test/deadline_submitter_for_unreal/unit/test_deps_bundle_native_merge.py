# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Guards which compiled artifact the dependency bundle ships for each interpreter.

The bundle is one flat directory placed on ``PYTHONPATH``, so it holds a single file per
name no matter which Python version Unreal Engine embeds. ``depsBundle.py`` installs the
compiled packages once per supported version and merges the results, and the merge is
where an interpreter can quietly lose its artifact: when two trees install the same
filename, the surviving copy is the only one any interpreter gets to load, and one built
for a newer Python fails to import on an older one.

These tests drive the merge over synthetic trees named the way the real wheels name their
extension modules, because a real build downloads a wheel per compiled package per
supported version. That is also their limit: they assert which artifact is selected, not
that it loads. Proving it loads needs the target interpreter, which the unit suite has no
access to.
"""

import subprocess
import sys
from pathlib import Path

import pytest
from packaging.requirements import Requirement

REPO_ROOT = Path(__file__).parents[3]
if str(REPO_ROOT) not in sys.path:
    # Appended rather than prepended: the repo root holds generically named modules
    # (hatch_custom_hook.py), and prepending would shadow any same-named import for the
    # rest of the pytest session.
    sys.path.append(str(REPO_ROOT))

import depsBundle  # noqa: E402

# awscrt's abi3 wheels all install this one name, whatever Python they were built for.
ABI3_ARTIFACT = "_awscrt.abi3.so"
# awscrt publishes abi3 wheels from this Python on; older versions get version-specific wheels.
FIRST_ABI3_VERSION = (3, 11)
# Stands in for the artifact the base environment resolved for the build host's own
# interpreter, which is not a version the bundle targets.
BASE_ENV_SENTINEL = "base-env-host"


def _version_key(version: str) -> tuple:
    return tuple(int(part) for part in version.split("."))


def _tag(version: str) -> str:
    """The interpreter tag a wheel puts in a version-specific extension module name."""
    return version.replace(".", "")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


@pytest.fixture
def supported_versions() -> list:
    versions = sorted(depsBundle.SUPPORTED_PYTHON_VERSIONS, key=_version_key)
    assert len(versions) >= 2, "a filename collision needs at least two supported versions"
    return versions


@pytest.fixture
def abi3_versions(supported_versions) -> list:
    versions = [v for v in supported_versions if _version_key(v) >= FIRST_ABI3_VERSION]
    assert versions, "no supported version gets an abi3 awscrt wheel"
    return versions


@pytest.fixture
def merged_bundle(tmp_path, supported_versions, abi3_versions) -> Path:
    """Run the merge over trees named the way the real wheels name their artifacts.

    Reproduces both naming schemes. awscrt installs the shared abi3 name from every abi3
    wheel (3.11+) and a version-specific name from the non-abi3 wheels it publishes for
    the older supported Pythons; xxhash and pyyaml install a version-specific name for
    every version.

    Each file's content records the version whose install produced it, so the merged tree
    reports where its own contents came from. The base environment is seeded with a
    sentinel, standing in for the copy resolved for the build host's own interpreter,
    which is not a version the bundle targets.
    """
    base_env = tmp_path / "base_env"
    _write(base_env / ABI3_ARTIFACT, BASE_ENV_SENTINEL)

    native_paths = []
    for version in supported_versions:
        tree = tmp_path / "native" / _tag(version)
        native_paths.append(tree)
        if version in abi3_versions:
            _write(tree / ABI3_ARTIFACT, version)
        else:
            _write(tree / f"_awscrt.cpython-{_tag(version)}-darwin.so", version)
        _write(tree / "xxhash" / f"_xxhash.cpython-{_tag(version)}-darwin.so", version)
        _write(tree / "yaml" / f"_yaml.cpython-{_tag(version)}-darwin.so", version)

    depsBundle._copy_native_to_base_env(base_env, native_paths)
    return base_env


def test_colliding_abi3_artifact_comes_from_the_lowest_supported_abi(merged_bundle, abi3_versions):
    """abi3 is forward compatible, so the lowest is the only copy that serves every version.

    A copy built for a newer Python links against symbols an older one does not export, so
    it fails to import there -- botocore then leaves its crypto binding unset and AWS
    Console sign-in reports that sign-in is needed, indefinitely. In particular the base
    environment's host-resolved copy, built for whatever interpreter ran the build, must
    not survive the merge.
    """
    lowest_abi3_version = abi3_versions[0]
    shipped = (merged_bundle / ABI3_ARTIFACT).read_text()

    assert shipped != BASE_ENV_SENTINEL, (
        f"{ABI3_ARTIFACT} is the base environment's host-resolved copy, built for an "
        f"interpreter the bundle does not target"
    )
    assert shipped == lowest_abi3_version, (
        f"{ABI3_ARTIFACT} was built for Python {shipped}, so it cannot be imported by "
        f"Python {lowest_abi3_version}; the copy built for the lowest supported abi3 "
        f"version is the one every supported interpreter can load"
    )


def test_version_specific_artifacts_are_kept_for_every_supported_version(
    merged_bundle, supported_versions, abi3_versions
):
    """The other half of the rule: these names do not collide, so none may be dropped.

    Collapsing a colliding name to one copy is only safe because the names that encode an
    interpreter tag are distinct, and every supported version needs its own.
    """
    for version in supported_versions:
        for package, module in (("xxhash", "_xxhash"), ("yaml", "_yaml")):
            artifact = merged_bundle / package / f"{module}.cpython-{_tag(version)}-darwin.so"
            assert (
                artifact.exists()
            ), f"the bundle carries no {package} artifact for Python {version}"
            assert artifact.read_text() == version

    for version in supported_versions:
        if version in abi3_versions:
            continue
        awscrt_non_abi3 = merged_bundle / f"_awscrt.cpython-{_tag(version)}-darwin.so"
        assert (
            awscrt_non_abi3.exists()
        ), f"the bundle carries no awscrt artifact for Python {version}"


def test_native_trees_are_merged_lowest_python_version_first(tmp_path, monkeypatch):
    """The merge keeps the first tree to supply a name, so the download order picks the winner.

    Ordered numerically rather than as strings: sorted as text, "3.9" lands after "3.10".
    The versions here are chosen to expose that, not to describe what is supported.
    """
    monkeypatch.setattr(depsBundle, "SUPPORTED_PYTHON_VERSIONS", ["3.13", "3.9", "3.11", "3.10"])
    monkeypatch.setattr(depsBundle, "_get_package_version", lambda package, install_path: "1.2.3")

    requested_versions = []

    def record(args, **kwargs):
        requested_versions.append(args[args.index("--python-version") + 1])
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(depsBundle.subprocess, "run", record)

    tree_paths = depsBundle._download_native_dependencies(tmp_path, tmp_path / "base_env")

    assert requested_versions == ["3.9", "3.10", "3.11", "3.13"]
    assert [path.name for path in tree_paths] == [
        "3_9_win_amd64",
        "3_10_win_amd64",
        "3_11_win_amd64",
        "3_13_win_amd64",
    ]


def test_get_package_version_matches_pip_list_casing(monkeypatch):
    """`pip list` prints the distribution's own casing, not the requirement's.

    NATIVE_DEPENDENCIES spells `pyyaml`, but pip reports it as `PyYAML`; a case-sensitive
    match would fail the per-version downloads for a package that is actually installed.
    """
    output = b"Package  Version\n-------- -------\nPyYAML   6.0.3\nxxhash   3.6.0\n"
    monkeypatch.setattr(
        depsBundle.subprocess,
        "run",
        lambda args, **kwargs: subprocess.CompletedProcess(args, 0, stdout=output),
    )

    assert depsBundle._get_package_version("pyyaml", Path("/unused")) == "6.0.3"


def test_deadline_floor_excludes_versions_without_console_signin():
    """The `console` extra first exists at deadline 0.60.4; 0.60.1 through 0.60.3 do not
    declare it. A floor that admits those versions lets pip satisfy `deadline[console]`
    by backtracking below the extra's introduction, silently dropping awscrt with only a
    warning, so console sign-in would appear installed and not work.
    """
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib

    with open(REPO_ROOT / "pyproject.toml", "rb") as pyproject_toml:
        project_dict = tomllib.load(pyproject_toml)

    requirements = [
        Requirement(dependency) for dependency in project_dict["project"]["dependencies"]
    ]
    deadline_requirements = [r for r in requirements if r.name.lower() == "deadline"]
    assert deadline_requirements, "pyproject.toml declares no deadline requirement"

    for requirement in deadline_requirements:
        assert "0.60.3" not in requirement.specifier, (
            f"`{requirement}` admits deadline 0.60.3, which has no console extra; "
            f"requesting deadline[console] under this floor lets pip backtrack below "
            f"0.60.4 and drop awscrt"
        )
        assert "0.60.4" in requirement.specifier, (
            f"`{requirement}` excludes deadline 0.60.4, the first version with AWS "
            f"Console sign-in"
        )
