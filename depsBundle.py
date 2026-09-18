from __future__ import annotations

import re
import shutil
import subprocess
import sys

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

SUPPORTED_PYTHON_VERSIONS = ["3.9", "3.10", "3.11"]
SUPPORTED_PLATFORMS = ["win_amd64"]
# Packages with compiled extension modules, fetched once per supported Python version so the
# bundle carries a loadable artifact for each interpreter.
#
# awscrt is here because its wheels are not uniformly abi3: Python 3.9 and 3.10 get a
# version-specific _awscrt.cp<tag>-win_amd64.pyd while 3.11+ get an abi3 (untagged)
# _awscrt.pyd. Resolving it only in the base environment would ship whichever the build
# host produced, so any Unreal Engine whose interpreter that single artifact does not cover
# would fail to import awscrt and AWS Console sign-in would break there.
# pyyaml is here because it ships a version-specific `_yaml` extension module: resolved only
# in the base environment it lands built for a single interpreter, and pyyaml hides that by
# falling back to its pure-Python parser on the other versions.
#
# The per-version downloads pin each package to the version the base environment resolved,
# deliberately: the compiled artifacts must match the package the bundle ships. If a package
# ever drops wheels for one of SUPPORTED_PYTHON_VERSIONS, the pinned download fails under
# check=True and the build breaks loudly rather than shipping a bundle that cannot load there.
#
# p4python is knowingly absent although it also ships a compiled extension (P4API) with no
# pure-Python fallback: its pin is marker-gated per Python version in project.dependencies,
# which the single base-environment pin used here cannot express -- covering it needs the
# pin resolved per target interpreter, a larger change than this list.
#
# This list overrides the packages that need one artifact per interpreter; it is not a
# general platform fix. The base environment itself is still resolved for the build host
# (no --platform/--python-version), so host-platform artifacts ride along in the zip and
# any dependency marker-gated on the target platform is evaluated against the host instead.
NATIVE_DEPENDENCIES = ["xxhash", "awscrt", "pyyaml"]


def _get_project_dict() -> dict[str, Any]:
    if sys.version_info < (3, 11):
        with TemporaryDirectory() as toml_env:
            toml_install_pip_args = ["pip", "install", "--target", toml_env, "toml"]
            subprocess.run(toml_install_pip_args, check=True)
            sys.path.insert(0, toml_env)
            import toml
        mode = "r"
    else:
        import tomllib as toml

        mode = "rb"

    with open("pyproject.toml", mode) as pyproject_toml:
        return toml.load(pyproject_toml)


def _get_dependencies(pyproject_dict: dict[str, Any]) -> list[str]:
    if "project" not in pyproject_dict:
        raise Exception("pyproject.toml is missing project section")
    if "dependencies" not in pyproject_dict["project"]:
        raise Exception("pyproject.toml is missing dependencies section")

    dependencies = pyproject_dict["project"]["dependencies"]
    deps_noopenjd = filter(lambda dep: not dep.startswith("openjd"), dependencies)
    return list(map(lambda dep: dep.replace(" ", ""), deps_noopenjd))


def _get_package_version_regex(package: str) -> re.Pattern:
    # Case-insensitive because `pip list` prints the distribution's own casing, which need not
    # match how the requirement is spelled -- `pyyaml` is reported as `PyYAML`. `-`, `_` and
    # `.` match interchangeably because PEP 503 treats them as equivalent, so `pip list` may
    # print a different separator than the one spelled here. The required whitespace keeps a
    # prefix sibling like `pyyaml-env-tag` from matching.
    name = "[-_.]+".join(re.escape(part) for part in re.split(r"[-_.]+", package))
    return re.compile(rf"^{name}\s+(\S+)\s*$", re.IGNORECASE)


def _get_package_version(package: str, install_path: Path) -> str:
    version_regex = _get_package_version_regex(package)
    pip_args = ["pip", "list", "--path", str(install_path)]
    output = subprocess.run(pip_args, check=True, capture_output=True).stdout.decode("utf-8")
    for line in output.split("\n"):
        match = version_regex.match(line)
        if match:
            return match.group(1)
    raise Exception(f"Could not find version for package {package}")


def _add_console_extra(requirement: str) -> str:
    """Add deadline's `console` extra to a requirement string, preserving its specifier."""
    match = re.fullmatch(
        r"(?P<name>[A-Za-z0-9._-]+)(?:\[(?P<extras>[^\]]*)\])?(?P<spec>.*)", requirement
    )
    if not match or match.group("name").lower() != "deadline":
        return requirement
    extras = [extra for extra in (match.group("extras") or "").split(",") if extra]
    if "console" not in extras:
        extras.append("console")
    return f"{match.group('name')}[{','.join(extras)}]{match.group('spec')}"


def _build_base_environment(working_directory: Path, dependencies: list[str]) -> Path:
    (working_directory / "base_env").mkdir()
    base_env_path = working_directory / "base_env"
    # The bundle is the submitter, which needs AWS Console sign-in. The console extra is
    # requested here rather than declared in project.dependencies, because those are also
    # resolved into the adaptor package, where a compiled awscrt wheel is both unusable and
    # unavailable for one of the platform tags that build targets (see pyproject.toml).
    #
    # Requesting the extra rather than installing awscrt directly means the bundle tracks
    # whatever the extra actually requires -- notably a botocore floor, since the console
    # login provider lives in botocore, not in deadline -- and takes awscrt from the exact
    # version botocore's crt extra pins, rather than resolving it independently and drifting.
    #
    # The `deadline` spelling in project.dependencies is load-bearing for the rewrite, but a
    # miss cannot pass silently: awscrt is in NATIVE_DEPENDENCIES, so if the extra is not
    # applied, _get_package_version("awscrt", ...) raises because the base environment does
    # not contain it.
    dependencies_for_pip = [_add_console_extra(dependency) for dependency in dependencies]
    base_env_pip_args = [
        "pip",
        "install",
        "--target",
        str(base_env_path),
        "--only-binary=:all:",
        *dependencies_for_pip,
    ]
    subprocess.run(base_env_pip_args, check=True)
    return base_env_path


def _python_version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def _download_native_dependencies(working_directory: Path, base_env: Path) -> list[Path]:
    versioned_native_dependencies = [
        f"{package_name}=={_get_package_version(package_name, base_env)}"
        for package_name in NATIVE_DEPENDENCIES
    ]
    native_dependency_paths = []
    # Ascending order is load-bearing: _copy_native_to_base_env resolves a filename
    # collision in favour of the tree it sees first.
    for version in sorted(SUPPORTED_PYTHON_VERSIONS, key=_python_version_key):
        for platform in SUPPORTED_PLATFORMS:
            native_dependency_path = (
                working_directory / "native" / f"{version.replace('.', '_')}_{platform}"
            )
            native_dependency_paths.append(native_dependency_path)
            native_dependency_path.mkdir(parents=True)
            native_dependency_pip_args = [
                "pip",
                "install",
                "--target",
                str(native_dependency_path),
                "--platform",
                platform,
                "--python-version",
                version,
                "--only-binary=:all:",
                # These trees exist only for their compiled artifacts, and they overwrite the
                # base environment during the merge. Without --no-deps each tree would carry the
                # packages' full transitive closures, resolved independently of the base
                # environment's, and clobber whatever it had resolved for anything they share.
                # Today none of NATIVE_DEPENDENCIES has runtime dependencies, but that is a
                # property of the current graph, not of this code.
                "--no-deps",
                *versioned_native_dependencies,
            ]
            subprocess.run(native_dependency_pip_args, check=True)
    return native_dependency_paths


def _copy_native_to_base_env(base_env: Path, native_dependency_paths: list[Path]) -> None:
    """Flatten the per-version native trees into the bundle, lowest version first.

    ``native_dependency_paths`` is ordered by ascending Python version and the first tree
    to supply a path wins, overwriting the base environment. The base environment resolved
    these packages for whatever interpreter the build host happens to run, which need not
    be a version the bundle targets, so it must not decide which artifact ships.

    Which artifacts survive follows from how the wheels name their extension modules, so no
    rule is needed per package. A version-specific name is unique per version and so cannot
    collide: ``xxhash`` ships one wheel per version and every interpreter keeps its own
    ``xxhash/_xxhash.cp<tag>-win_amd64.pyd``, and ``pyyaml`` is the same case, one wheel per
    version installing ``yaml/_yaml.cp<tag>-win_amd64.pyd``. An abi3 name is the same for
    every version and so collides: ``awscrt`` publishes a separate abi3 wheel per Python
    from 3.11 on, each installing the same untagged ``_awscrt.pyd``, so the copies differ
    and only one can ship; abi3 is forward compatible, which makes the one built for the
    lowest supported abi3 Python the only copy that loads on all of them, and taking the
    first tree is what keeps it. (3.9 and 3.10 get version-specific awscrt wheels, which do
    not collide.)
    """
    copied: set[Path] = set()
    for native_dependency_path in native_dependency_paths:
        for file in native_dependency_path.rglob("*"):
            if file.is_file():
                relative = file.relative_to(native_dependency_path)
                if relative in copied:
                    continue
                in_base_env = base_env / relative
                in_base_env.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(str(file), str(in_base_env))
                copied.add(relative)


def _get_zip_path(working_directory: Path, project_dict: dict[str, Any]) -> Path:
    if "project" not in project_dict:
        raise Exception("pyproject.toml is missing project section")
    if "name" not in project_dict["project"]:
        raise Exception("pyproject.toml is missing name section")
    transformed_project_name = (
        f"{project_dict['project']['name'].replace('-', '_')}_submitter-deps.zip"
    )
    return working_directory / transformed_project_name


def _zip_bundle(base_env: Path, zip_path: Path) -> None:
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", str(base_env))


def _copy_zip_to_destination(zip_path: Path) -> None:
    dependency_bundle_dir = Path.cwd() / "dependency_bundle"
    dependency_bundle_dir.mkdir(exist_ok=True)
    zip_desntination = dependency_bundle_dir / zip_path.name
    if zip_desntination.exists():
        zip_desntination.unlink()
    shutil.copy(str(zip_path), str(zip_desntination))


def build_deps_bundle() -> None:
    with TemporaryDirectory() as temporary_directory:
        working_directory = Path(temporary_directory)
        project_dict = _get_project_dict()
        dependencies = _get_dependencies(project_dict)
        base_env = _build_base_environment(working_directory, dependencies)
        native_dependency_paths = _download_native_dependencies(working_directory, base_env)
        _copy_native_to_base_env(base_env, native_dependency_paths)
        zip_path = _get_zip_path(working_directory, project_dict)
        _zip_bundle(base_env, zip_path)
        print(list(working_directory.glob("*")))
        _copy_zip_to_destination(zip_path)


if __name__ == "__main__":
    build_deps_bundle()
