# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import dataclasses
import hashlib
import logging
import os
import json
import pprint
import socket
import time
import getpass
from pathlib import Path
from typing import Optional

from deadline.unreal_logger import get_logger
from deadline.unreal_perforce_utils import perforce, secret_manager

logger = get_logger()

# Separate logger for events that need to surface in the OpenJD adaptor's
# captured output. The adaptor uses `logging.getLogger(__name__)` which
# propagates to root and gets picked up by OpenJD's log-capture. Our
# `get_logger()` returns a named `unreal_logger` whose StreamHandler
# writes to whatever `sys.stdout` was when the module first imported —
# in the daemon subprocess that's not the adaptor's captured stream.
# Using a standard __name__ logger for diagnostics restores propagation
# and gets these events into the task log alongside other ADAPTOR_OUTPUT.
_diag_logger = logging.getLogger(__name__)


def _diag(msg: str) -> None:
    """
    Emit a diagnostic line that surfaces in the adaptor's task log.

    Uses the propagating __name__ logger (matches the adaptor's own
    logger.info wiring, which is what actually reaches the captured
    ADAPTOR_OUTPUT stream). The named `unreal_logger` writes to a
    subprocess stdout that isn't captured, so events routed through
    ``get_logger()`` don't show up in task logs.
    """
    _diag_logger.info(msg)


@dataclasses.dataclass
class WorkspaceInfoFile:
    """Registry of previously created Perforce workspaces, stored as JSON alongside the workspace root."""

    stream_workspaces: dict[str, str] = dataclasses.field(default_factory=dict)
    view_workspace: Optional[str] = None

    @staticmethod
    def load(path: str) -> "WorkspaceInfoFile":
        """Load from JSON file. Returns empty registry on missing/corrupt file."""
        try:
            with open(path, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            logger.info(f"Workspace info file not found at {path}, starting with empty registry.")
            return WorkspaceInfoFile()
        except json.JSONDecodeError:
            logger.warning(
                f"Workspace info file at {path} contains invalid JSON, starting with empty registry."
            )
            return WorkspaceInfoFile()
        except OSError as e:
            logger.warning(
                f"Could not read workspace info file at {path}: {e}. Starting with empty registry."
            )
            return WorkspaceInfoFile()

        # Validate types — fall back to empty on bad data
        stream_workspaces = data.get("stream_workspaces", {})
        view_workspace = data.get("view_workspace")

        if not isinstance(stream_workspaces, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in stream_workspaces.items()
        ):
            logger.warning(f"Invalid stream_workspaces in {path}, starting with empty registry.")
            return WorkspaceInfoFile()

        if view_workspace is not None and not isinstance(view_workspace, str):
            logger.warning(f"Invalid view_workspace in {path}, starting with empty registry.")
            return WorkspaceInfoFile()

        return WorkspaceInfoFile(
            stream_workspaces=stream_workspaces,
            view_workspace=view_workspace,
        )

    def save(self, path: str) -> None:
        """Write to JSON file with sorted keys."""
        data = {
            "stream_workspaces": self.stream_workspaces,
            "view_workspace": self.view_workspace,
        }
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                json.dump(data, f, sort_keys=True)
        except OSError as e:
            logger.error(f"Could not write workspace info file at {path}: {e}")

    def lookup_stream(self, stream_path: str) -> Optional[str]:
        """Return workspace name for stream path, or None."""
        return self.stream_workspaces.get(stream_path)

    def lookup_view(self) -> Optional[str]:
        """Return the single shared view workspace name, or None."""
        return self.view_workspace

    def register_stream(self, stream_path: str, workspace_name: str) -> None:
        """Add stream_path -> workspace_name mapping."""
        self.stream_workspaces[stream_path] = workspace_name

    def register_view(self, workspace_name: str) -> None:
        """Set the single shared view workspace name."""
        self.view_workspace = workspace_name


def _normalize_root(root: str) -> str:
    """
    Normalize a workspace Root path for comparison: forward slashes, no trailing
    separator, casefolded (P4 stores Windows paths case-insensitively).
    """
    if not root:
        return ""
    return root.replace("\\", "/").rstrip("/").casefold()


# Fallback workspace root used when P4_CLIENTS_ROOT_DIRECTORY is unset.
# Matches the P4V convention of placing client workspaces under ~/Perforce.
_DEFAULT_CLIENTS_ROOT_NAME = "Perforce"


def _default_clients_root() -> str:
    """Return ``~/Perforce`` (expanded) — the fallback persistent workspace root."""
    return os.path.join(os.path.expanduser("~"), _DEFAULT_CLIENTS_ROOT_NAME)


def merge_view_mappings(existing_views: list[str], new_views: list[str]) -> list[str]:
    """
    Merge new view mappings into existing ones.
    Appends any mappings from new_views not already present in existing_views.
    Returns the merged list.
    """
    merged = list(existing_views)
    for view in new_views:
        if view not in merged:
            merged.append(view)
    return merged


@dataclasses.dataclass
class _ResolvedWorkspace:
    name: str
    reusing: bool


def _stream_path_to_name_component(stream_path: str) -> str:
    """
    Convert a P4 stream path like ``//MeerkatDemo/Mainline`` into a human-readable
    string safe for use in P4 client names and directory names.

    Strips leading ``//``, replaces ``/`` with ``_``, and appends a short hash
    suffix to avoid collisions when different stream paths produce the same
    readable portion (e.g. ``//A_B/C`` vs ``//A/B_C``).

    Example: ``//MeerkatDemo/Mainline`` → ``MeerkatDemo_Mainline_a3f2``
    """
    readable = stream_path.lstrip("/").replace("/", "_")
    short_hash = hashlib.sha256(stream_path.encode()).hexdigest()[:4]
    return f"{readable}_{short_hash}"


def _resolve_workspace_name(
    specification_template: dict,
    project_name: str,
    workspace_info: Optional[WorkspaceInfoFile],
) -> _ResolvedWorkspace:
    """Determine workspace name, consulting the registry if available."""
    if workspace_info is not None:
        if "Stream" in specification_template:
            stream_path = specification_template["Stream"]
            existing = workspace_info.lookup_stream(stream_path)
            if existing:
                logger.info(f"Reusing existing stream workspace: {existing}")
                return _ResolvedWorkspace(name=existing, reusing=True)
            stream_component = _stream_path_to_name_component(stream_path)
            name = get_workspace_name(project_name=stream_component)
            workspace_info.register_stream(stream_path, name)
            return _ResolvedWorkspace(name=name, reusing=False)

        if "View" in specification_template:
            existing = workspace_info.lookup_view()
            if existing:
                logger.info(f"Reusing existing view workspace: {existing}")
                return _ResolvedWorkspace(name=existing, reusing=True)
            name = get_workspace_name(project_name=project_name)
            workspace_info.register_view(name)
            return _ResolvedWorkspace(name=name, reusing=False)

    return _ResolvedWorkspace(name=get_workspace_name(project_name=project_name), reusing=False)


def get_workspace_name(project_name: str) -> str:
    """
    Build and return the workspace name based on the given project name:
    ``<USERNAME>_<HOST>_<PROJECT_NAME>``.

    If ``DEADLINE_WORKER_ID`` environment variable is set, it will be appended:
    ``<USERNAME>_<HOST>_<PROJECT_NAME>_<WORKER_ID>``

    :param project_name: Name of the project

    :return: Workspace name
    :rtype: str
    """

    workspace_name = f"{getpass.getuser()}_{socket.gethostname()}_{project_name}"
    if "DEADLINE_WORKER_ID" in os.environ:
        workspace_name += f"_{os.environ['DEADLINE_WORKER_ID']}"

    return workspace_name


def get_workspace_specification_template_from_file(
    workspace_specification_template_path: str,
) -> dict:
    """
    Read the given workspace specification template file path and return loaded content

    :param workspace_specification_template_path: Path to the workspace specification template file

    :return: Loaded workspace specification template dictionary
    :rtype: dict
    """

    if not os.path.exists(workspace_specification_template_path):
        raise FileNotFoundError(
            f"The workspace specification template does not exist: {workspace_specification_template_path}"
        )

    logger.info(
        f"Getting workspace specification template from file: {workspace_specification_template_path} ..."
    )
    with open(workspace_specification_template_path, "r", encoding="utf-8") as f:
        return json.load(f)


def create_perforce_workspace_from_template(
    specification_template: dict,
    project_name: str,
    overridden_workspace_root: Optional[str] = None,
) -> perforce.PerforceClient:
    """
    Creates Perforce workspace from the template.

    For template example see
    :meth:`deadline.unreal_perforce_utils.perforce.get_perforce_workspace_specification_template()`

    Replace ``{workspace_name}`` token in the template with the real workspace name in
    ``"Client"`` and ``"View"`` fields

    When ``P4_CLIENTS_ROOT_DIRECTORY`` is set, consults a workspace registry file
    (``workspace_info.json``) to reuse previously created workspaces instead of
    always creating new ones.

    :param specification_template: Workspace specification template dictionary
    :param project_name: Name of the project to build workspace name
    :param overridden_workspace_root: Workspace local path root (Optional, root from template is used by default)

    :return: :class:`p4utilsforunreal.perforce.PerforceClient` instance
    :rtype: :class:`p4utilsforunreal.perforce.PerforceClient`
    """

    logger.info(
        f"Creating perforce workspace from template: \n"
        f"Specification template: {specification_template}\n"
        f"Project: {project_name}\n"
        f"Overridden workspace root: {overridden_workspace_root}"
    )

    persistent_root = os.getenv("P4_CLIENTS_ROOT_DIRECTORY")
    if not persistent_root:
        persistent_root = _default_clients_root()
        # Informational only: ~/Perforce works fine on both CMF and SMF (on SMF
        # with persistent volumes, the worker user's home directory is junctioned
        # onto the persistent volume, so ~/Perforce ends up there automatically).
        # Set P4_CLIENTS_ROOT_DIRECTORY explicitly only if you need a path
        # outside the worker user's home (e.g. a separate persistent mount).
        logger.info(
            "P4_CLIENTS_ROOT_DIRECTORY is not set; using the default %r. "
            "Workspaces under this path are reused across jobs.",
            persistent_root,
        )

    # NOTE: Assumes single worker/session/adaptor per clients root — no file locking needed.
    workspace_info_path = os.path.join(persistent_root, "workspace_info.json")
    workspace_info = WorkspaceInfoFile.load(workspace_info_path)

    resolved = _resolve_workspace_name(specification_template, project_name, workspace_info)
    workspace_name = resolved.name
    reusing = resolved.reusing

    specification_template["Client"] = specification_template["Client"].replace(
        "{workspace_name}", workspace_name
    )
    if "View" in specification_template:
        updated_views = []
        for view in specification_template["View"]:
            updated_views.append(view.replace("{workspace_name}", workspace_name))
        specification_template["View"] = updated_views

    if overridden_workspace_root:
        specification_template["Root"] = overridden_workspace_root
    else:
        specification_template["Root"] = f"{persistent_root}/{workspace_name}"

    # Clear Host lock so the reusable workspace can be used from any host.
    # persistent_root is always set now (env var or ~/Perforce fallback), so
    # workspaces are always treated as reusable.
    specification_template["Host"] = ""

    logger.info(f"Specification: {specification_template}")

    connection = perforce.PerforceConnection()

    # Always fetch the existing server-side spec when using a persistent root.
    # The workspace may already exist on the server even if the local registry
    # (workspace_info.json) doesn't know about it (e.g. created by an older
    # version of the code before the registry was introduced).
    if persistent_root or reusing:
        existing_spec = connection.p4.fetch_client(workspace_name)

        # If Root changed since the workspace was last used, the server's have-list
        # still describes files at the old root. A subsequent `p4 sync` would then
        # report "file(s) up-to-date" and write nothing to the new root, leaving
        # the renderer to fail loading assets that aren't actually on disk.
        # Clear the have-list so the next sync transfers files to the new root.
        existing_root = _normalize_root(existing_spec.get("Root", ""))
        new_root = _normalize_root(specification_template.get("Root", ""))
        if existing_root and new_root and existing_root != new_root:
            logger.info(
                f"Workspace '{workspace_name}' Root changed "
                f"({existing_spec.get('Root')} -> {specification_template.get('Root')}); "
                f"clearing have-list so subsequent sync transfers files to the new root."
            )
            try:
                connection.p4.client = workspace_name
                connection.p4.run("sync", "-k", "//...#none")
            except Exception as e:
                # Don't fail workspace creation — a force-sync downstream can still
                # recover. Log loudly so operators can correlate later sync issues.
                logger.error(
                    f"Failed to clear have-list for workspace '{workspace_name}' "
                    f"after Root change: {e}"
                )

        if reusing and "View" in specification_template:
            # Stream workspaces: no view merge needed — P4 derives the view from the stream definition.
            # View workspaces: merge with existing spec to preserve mappings from prior jobs.
            existing_views = existing_spec.get("View", [])
            new_views = specification_template["View"]
            merged_views = merge_view_mappings(existing_views, new_views)
            specification_template["View"] = merged_views

    perforce_client = perforce.PerforceClient(
        connection=connection,
        name=workspace_name,
        specification=specification_template,
    )

    perforce_client.save()

    if workspace_info is not None and workspace_info_path is not None:
        workspace_info.save(workspace_info_path)

    logger.info("Perforce workspace created!")
    logger.info(pprint.pformat(perforce_client.spec))

    return perforce_client


def _parse_job_dependencies(
    workspace: perforce.PerforceClient, job_dependencies_descriptor_path: str
) -> list[str]:
    with open(job_dependencies_descriptor_path, "r", encoding="utf-8") as f:
        job_data = json.load(f)
        dependent_paths = job_data.get("job_dependencies", [])
        if not isinstance(dependent_paths, list):
            logger.info(
                f"Warning: job_dependencies must be a list, got {type(dependent_paths).__name__}"
            )
            return []

        # Convert dependency paths to local workspace paths
        dependent_paths_to_sync = []
        for dependent_path in dependent_paths:
            if not isinstance(dependent_path, str) or not dependent_path.strip():
                logger.warning(f"Warning: skipping invalid dependency path: {dependent_path}")
                continue

            local_path = workspace.where(dependent_path)
            if local_path:
                dependent_paths_to_sync.append(local_path.replace("\\", "/"))
            else:
                logger.warning(f"Can't convert {dependent_path} to local path.")
    return dependent_paths_to_sync


def initial_workspace_sync(
    workspace: perforce.PerforceClient,
    unreal_project_relative_path: str,
    changelist: Optional[str] = None,
    job_dependencies_descriptor_path: Optional[str] = None,
) -> None:
    """
    Do initial workspace synchronization:

    - .uproject file
    - Binaries folder
    - Config folder
    - Plugins folder
    - If ``job_dependencies_descriptor_path`` is provided, sync job dependencies as well.

    :param workspace: p4utilsforunreal.perforce.PerforceClient instance
    :param unreal_project_relative_path: path to the .uproject file relative to the workspace root
    :param changelist: Changelist number to sync workspace to
    :param job_dependencies_descriptor_path: Path to JSON file containing job dependencies to sync
    """

    logger.info("Workspace initial synchronizing ...")

    workspace_root = workspace.spec["Root"].replace("\\", "/")
    skeleton_paths = [f"{workspace_root}/{unreal_project_relative_path}"]
    unreal_project_directory = os.path.dirname(unreal_project_relative_path)
    for folder in ["Binaries", "Config", "Plugins"]:
        tokens = filter(
            lambda t: t not in [None, ""], [workspace_root, unreal_project_directory, folder, "..."]
        )
        skeleton_paths.append("/".join(tokens))

    # Sync skeleton files with force to ensure they're always correct
    logger.info(f"Paths to sync: {skeleton_paths}")
    for path in skeleton_paths:
        try:
            workspace.sync(path, changelist=changelist, force=True)
        except Exception as e:
            logger.error(f"Initial workspace sync exception: {str(e)}")

    # Sync job dependencies without force — P4's have-list will skip files
    # already at the correct revision, making reuse near-instant.
    if job_dependencies_descriptor_path and os.path.exists(job_dependencies_descriptor_path):
        dependency_paths = _parse_job_dependencies(workspace, job_dependencies_descriptor_path)
        logger.info(f"Dependency paths to sync: {dependency_paths}")
        for path in dependency_paths:
            try:
                workspace.sync(path, changelist=changelist, force=False)
            except Exception as e:
                logger.error(f"Dependency sync exception: {str(e)}")

    if job_dependencies_descriptor_path and os.path.exists(job_dependencies_descriptor_path):
        logger.info("openjd_env: DEPENDENCIES_SYNCED=true")


def configure_project_source_control_settings(
    workspace: perforce.PerforceClient, unreal_project_relative_path: str
):
    """
    Configure SourceControl settings (Saved/Config/WindowsEditor/SourceControlSettings.ini)
    with the current P4 connection settings

    :param workspace: p4utilsforunreal.perforce.PerforceClient instance
    :param unreal_project_relative_path: path to the .uproject file relative to the workspace root
    """

    logger.info("Configuring Unreal project SourceControl settings ...")
    unreal_project_directory = os.path.dirname(unreal_project_relative_path)
    tokens = filter(
        lambda t: t not in [None, ""],
        [
            workspace.spec["Root"],
            unreal_project_directory,
            "Saved/Config/WindowsEditor/SourceControlSettings.ini",
        ],
    )
    source_control_settings_path = "/".join(tokens)
    os.makedirs(os.path.dirname(source_control_settings_path), exist_ok=True)
    logger.info(f"Source Control settings file: {source_control_settings_path}")

    source_control_settings_lines = [
        "[PerforceSourceControl.PerforceSourceControlSettings]\n",
        "UseP4Config = False\n",
        f"Port = {workspace.p4.port}\n",
        f"UserName = {workspace.p4.user}\n",
        f"Workspace = {workspace.p4.client}\n\n",
        "[SourceControl.SourceControlSettings]\n",
        "Provider = Perforce\n",
    ]
    logger.info("source control settings:\n")
    for setting_line in source_control_settings_lines:
        logger.info(setting_line)

    with open(source_control_settings_path, "w+") as f:
        for setting_line in source_control_settings_lines:
            f.write(setting_line)


def create_workspace(
    perforce_specification_template_path: str,
    unreal_project_relative_path: str,
    unreal_project_name: Optional[str] = None,
    overridden_workspace_root: Optional[str] = None,
    changelist: Optional[str] = None,
    job_dependencies_descriptor_path: Optional[str] = None,
):
    """
    Create P4 workspace and execute next steps:

    - :meth:`deadline.unreal_perforce_utils.app.get_workspace_specification_template_from_file()`
    - :meth:`deadline.unreal_perforce_utils.app.initial_workspace_sync()`
    - :meth:`deadline.unreal_perforce_utils.app.configure_project_source_control_settings()`

    :param perforce_specification_template_path: Path to the perforce specification template file to read specification from
    :param unreal_project_relative_path: path to the .uproject file relative to the workspace root
    :param unreal_project_name: Name of the .uproject file
    :param overridden_workspace_root: Workspace local path root (Optional, root from template is used by default)
    :param changelist: Changelist to sync workspace to
    :param job_dependencies_descriptor_path: Path to JSON file containing job dependencies to sync
    """

    logger.info(
        "Creating workspace with the following settings:\n"
        f"Specification template: {perforce_specification_template_path}\n"
        f"Unreal project relative path: {unreal_project_relative_path}\n"
        f"Overridden workspace root: {overridden_workspace_root}\n"
        f"Changelist: {changelist}\n"
        f"job_dependencies_descriptor_path: {job_dependencies_descriptor_path}"
    )

    workspace_specification_template = get_workspace_specification_template_from_file(
        workspace_specification_template_path=perforce_specification_template_path
    )

    workspace = create_perforce_workspace_from_template(
        specification_template=workspace_specification_template,
        project_name=unreal_project_name or Path(unreal_project_relative_path).stem,
        overridden_workspace_root=overridden_workspace_root,
    )

    # Required to make DeadlineCloud set this variable to Environment
    p4_client_directory = workspace.spec["Root"].replace("\\", "/")
    logger.info(f"openjd_env: P4_CLIENT_DIRECTORY={p4_client_directory}")

    initial_workspace_sync(
        workspace=workspace,
        unreal_project_relative_path=unreal_project_relative_path,
        changelist=changelist,
        job_dependencies_descriptor_path=job_dependencies_descriptor_path,
    )

    configure_project_source_control_settings(
        workspace=workspace, unreal_project_relative_path=unreal_project_relative_path
    )


def delete_workspace(workspace_name: Optional[str] = None, project_name: Optional[str] = None):
    """
    No-op kept for backwards compatibility with the OpenJD `onExit` action in the
    P4/UGS sync environment templates.

    P4 workspaces are now always created under a persistent root — either the
    explicit ``P4_CLIENTS_ROOT_DIRECTORY`` env var, or the ``~/Perforce`` fallback.
    On both service-managed (with the EBS persistent-volume feature) and
    customer-managed fleets, the intent is to reuse the workspace across jobs to
    avoid the full re-sync cost on each render. Deleting it on exit defeats that.

    Previously this function would revert open files, sync the workspace to #0
    to remove local content, then ``p4 client -d`` the spec — that path was
    intended for SMF workers without EBS persistence (which don't exist anymore
    now that the persistent-volume feature has shipped).

    :param workspace_name: ignored (kept for signature compatibility)
    :param project_name: ignored (kept for signature compatibility)
    """
    if "P4_CLIENTS_ROOT_DIRECTORY" in os.environ:
        logger.info(
            "P4_CLIENTS_ROOT_DIRECTORY is set — skipping workspace deletion " "(reusable workspace)"
        )
    else:
        logger.info(
            "P4_CLIENTS_ROOT_DIRECTORY is not set — skipping workspace deletion "
            "to preserve the fallback persistent workspace under %r",
            _default_clients_root(),
        )


_TRANSIENT_SUBMIT_ERROR_FRAGMENTS = (
    # Another submit holds the depot path lock. Retrying after a brief pause
    # almost always succeeds — the conflicting submit is millisecond-scale.
    "currently locked",
    "file(s) locked by",
    # Generic transient: connection blip to the P4 server.
    "TCP connect to",
    "Connect to server failed",
)
# Deliberately NOT retryable by a bare re-submit:
#   - "must resolve" / "file(s) not on client": the depot head advanced under
#     us. A plain re-submit of the same CL fails identically until we run
#     `p4 sync` and `p4 resolve` first. Retrying without those steps just
#     burns the retry budget and adds latency before the same failure. If we
#     want to auto-recover from head advances we need a distinct code path
#     that syncs + resolves before re-submitting.


def _is_transient_submit_error(exc: Exception) -> bool:
    """Heuristic match against P4 error strings that indicate a retryable conflict."""
    msg = str(exc)
    return any(fragment in msg for fragment in _TRANSIENT_SUBMIT_ERROR_FRAGMENTS)


# Machine-parseable marker line prepended to render-shelve CL descriptions.
# AssembleShelves greps `p4 changes -l` output for this exact prefix + a
# Deadline job ID to discover which shelved CLs belong to a given job across
# all workers, without any client-side coordination.
#
# The two prefixes are deliberately distinct so `_find_shelved_cls_for_job`,
# which filters on ``DEADLINE_CL_MARKER_PREFIX`` only, cannot mistake an
# aggregate CL for a task shelve on a retry / re-submitted job. An
# aggregate stamped with ``DEADLINE_CL_AGGREGATE_MARKER_PREFIX`` is
# invisible to task-shelve discovery.
DEADLINE_CL_MARKER_PREFIX = "DeadlineCloudRenderShelve/"
DEADLINE_CL_AGGREGATE_MARKER_PREFIX = "DeadlineCloudRenderAggregate/"


def _build_changelist_description(
    job_name: Optional[str],
    extra_description: Optional[str],
    deadline_job_id: Optional[str] = None,
    marker_prefix: str = DEADLINE_CL_MARKER_PREFIX,
) -> str:
    """
    Build a CL description that traces back to the Deadline session that
    produced the renders. Reads the standard DEADLINE_* env vars the worker
    agent injects into every job.

    :param deadline_job_id: If provided, prepends a machine-parseable marker
        line ``<marker_prefix><job-id>`` as the first line of the description.
        AssembleShelves uses ``DEADLINE_CL_MARKER_PREFIX`` to discover task
        shelves, and stamps the aggregate CL with
        ``DEADLINE_CL_AGGREGATE_MARKER_PREFIX`` so the aggregate is never
        picked up by task-shelve discovery.
    :param marker_prefix: Marker prefix to use for the marker line. Defaults
        to ``DEADLINE_CL_MARKER_PREFIX``. Pass
        ``DEADLINE_CL_AGGREGATE_MARKER_PREFIX`` for the aggregate CL.
    """
    # Only stamp the marker when the caller explicitly passed a job ID —
    # falling back to os.getenv here would defeat callers that want to
    # suppress or override the marker (e.g. aggregate CLs, which must use
    # the aggregate prefix, not the task prefix).
    lines = []
    if deadline_job_id:
        # Marker line first so a `startswith` check on the description
        # first line is enough — no regex, no ambiguity.
        lines.append(f"{marker_prefix}{deadline_job_id}")
    lines.append("Deadline Cloud render output")
    if job_name:
        lines.append(f"Job: {job_name}")
    for env_var, label in [
        ("DEADLINE_FARM_ID", "Farm"),
        ("DEADLINE_QUEUE_ID", "Queue"),
        ("DEADLINE_JOB_ID", "Job ID"),
        ("DEADLINE_FLEET_ID", "Fleet"),
        ("DEADLINE_WORKER_ID", "Worker"),
        ("DEADLINE_SESSION_ID", "Session"),
    ]:
        value = os.getenv(env_var)
        if value:
            lines.append(f"{label}: {value}")
    if extra_description:
        lines.append("")
        lines.append(extra_description)
    return "\n".join(lines)


def submit_renders(
    unreal_project_name: str,
    output_directories: list[str],
    description: Optional[str] = None,
    mode: str = "",
    max_submit_retries: int = 3,
    submit_retry_sleep_seconds: float = 2.0,
    deadline_job_id: Optional[str] = None,
    explicit_files: Optional[list[str]] = None,
) -> Optional[int]:
    """
    Reconcile new and modified files under each given output directory into a
    new Perforce changelist and submit (or shelve) them.

    The set of files committed mirrors what Job Attachments would have uploaded:
    we use the same output-directory declaration the customer's
    ``asset_references.yaml`` provides, and rely on ``p4 reconcile`` to compute
    the diff against depot state. Files unchanged since the last sync are
    no-ops; new files are added; modified files are opened for edit.

    Job Attachments runs unconditionally regardless of this step. Calling
    submit_renders is purely additive — it does *not* replace JA upload, it
    pushes the same outputs into Perforce as well.

    :param unreal_project_name: Project name used to resolve the persistent
        workspace (same value passed to ``create_workspace``). The CLI usually
        derives this from the ``.uproject`` filename.
    :param output_directories: List of local directory paths to reconcile. These
        are typically the same paths the customer declared in
        ``asset_references.yaml`` ``outputs.directories``.
    :param description: Optional extra text appended to the CL description.
        Job/queue/farm/worker IDs are added automatically from the worker agent's
        ``DEADLINE_*`` env vars.
    :param mode: ``""`` (default) is a no-op — the function logs and returns
        without contacting P4, so customers who add the step to their template
        without committing to a write workflow get no surprises. ``"submit"``
        commits the CL immediately. ``"shelve"`` shelves it and emits the
        shelved CL number via ``openjd_env: SHELVED_CL=<n>`` so a downstream
        assembly task can pick it up. Submit failures classified as transient
        are retried.
    :param max_submit_retries: Number of submit attempts on transient errors
        (P4 lock contention, head-revision races). Defaults to 3.
    :param submit_retry_sleep_seconds: Pause between retries.
    :param explicit_files: When provided, reconcile only these exact file paths
        instead of the entire ``output_directories`` tree(s). This is how the
        render adaptor scopes each task's shelve to just the files that task
        produced (identified via a pre-render/post-render mtime diff), so
        chunked tasks sharing an output_path don't re-shelve each other's
        frames. ``output_directories`` is ignored when this is set.

    :return: The submitted (or shelved) changelist number, or None if there was
        nothing to commit (or mode was the default no-op).
    """
    _diag(
        f"submit_renders: ENTRY (mode={mode!r}, "
        f"explicit_files={len(explicit_files) if explicit_files else 0}, "
        f"output_directories={len(output_directories) if output_directories else 0}, "
        f"project={unreal_project_name!r})"
    )
    if mode not in ("", "submit", "shelve"):
        raise ValueError(f"submit_renders mode must be '', 'submit', or 'shelve', got {mode!r}")

    if mode == "":
        logger.info(
            "submit_renders: mode is empty (default); skipping. Job Attachments "
            "still runs as configured by the queue. Set mode to 'submit' or "
            "'shelve' to also push outputs to Perforce."
        )
        return None

    if not output_directories and not explicit_files:
        logger.info(
            "submit_renders: no output directories or explicit files provided; " "nothing to do."
        )
        return None

    workspace_name = get_workspace_name(project_name=unreal_project_name)
    _diag(
        f"submit_renders: using workspace {workspace_name!r} "
        f"(mode={mode!r}, explicit_files={len(explicit_files) if explicit_files else 0}, "
        f"output_directories={len(output_directories)})"
    )

    connection = perforce.PerforceConnection()
    connection.p4.client = workspace_name

    # Step 1: reconcile the files/dirs into the default changelist.
    # -e: open changed files for edit; -a: open new files for add.
    # We deliberately omit -d (delete missing) — for renders, "missing" usually
    # means the customer didn't render every frame this run, not that they want
    # the prior frames removed from depot.
    #
    # When ``explicit_files`` is set we reconcile that exact list (the render
    # adaptor already narrowed it to just this task's files); otherwise we
    # recurse under each output directory.
    if explicit_files:
        reconcile_targets: list[str] = [f.replace("\\", "/") for f in explicit_files]
        _diag(
            f"submit_renders: reconciling {len(reconcile_targets)} explicit "
            f"file(s) (scoped to this task's output)."
        )
    else:
        reconcile_targets = [
            f"{d.replace(chr(92), '/').rstrip('/')}/..." for d in output_directories
        ]

    # Step 1a-pre: revert any stale opens of the exact files we're about to
    # reconcile. Prior task runs could have left files opened in the default
    # changelist (e.g. a task that crashed after `reconcile` but before
    # `submit`). If reopen `//...` later swept those into our new CL, we'd
    # inherit unrelated file state and end up shelving frames this task
    # never produced. Scoping the revert to this task's file list keeps the
    # blast radius tight — we don't touch anything outside our own outputs.
    if explicit_files:
        try:
            revert_stale = connection.p4.run("revert", "-k", *reconcile_targets)
            if revert_stale:
                _diag(
                    f"submit_renders: pre-reconcile revert -k cleared {len(revert_stale)} "
                    f"stale open(s) on this task's files"
                )
        except Exception as e:
            # `revert -k` raises when there's nothing opened — benign.
            if "not opened on this client" not in str(e) and "file(s) not opened" not in str(e):
                logger.warning(f"submit_renders: pre-reconcile revert -k failed: {e}")

    # Step 1a: align the workspace's have-list to depot head for the exact
    # files we're about to reconcile. `create_workspace` only syncs the
    # project to PerforceChangelistNumber at env-setup time, and no later
    # step re-syncs after our own aggregate submits. That leaves have stale
    # for files we've written to depot in prior jobs — reconcile then can't
    # decide what to do (file's in depot, not in have) and refuses to open
    # them. `sync -k <path>@head` updates have in place without transferring
    # any bytes; safe because we're about to overwrite these paths anyway.
    # Skip for dir-recursion callers (untargeted sync -k across the whole
    # tree could touch files we shouldn't).
    if explicit_files:
        _diag(
            f"submit_renders: sync -k on {len(reconcile_targets)} explicit file(s) "
            f"to align have-list with depot head before reconcile"
        )
        sync_ok = 0
        sync_no_file = 0
        sync_up_to_date = 0
        sync_other_err = 0
        first_other_err_msg = ""
        for path in reconcile_targets:
            try:
                connection.p4.run("sync", "-k", f"{path}#head")
                sync_ok += 1
            except Exception as e:
                msg = str(e)
                # p4python raises P4Exception on non-fatal warnings; classify
                # by content so we can tell "benign no-op" from a real error.
                if "no such file" in msg or "file(s) not in client view" in msg:
                    # File not in depot yet: reconcile -a will add it.
                    sync_no_file += 1
                elif "up-to-date" in msg or "already synced" in msg:
                    # have already at head — nothing to do.
                    sync_up_to_date += 1
                else:
                    sync_other_err += 1
                    if not first_other_err_msg:
                        first_other_err_msg = msg
        _diag(
            f"submit_renders: sync -k summary — ok={sync_ok}, "
            f"no-file-yet={sync_no_file}, up-to-date={sync_up_to_date}, "
            f"other-err={sync_other_err}"
            + (f", first-other-err={first_other_err_msg!r}" if first_other_err_msg else "")
        )

    any_files_opened = False
    for reconcile_path in reconcile_targets:
        _diag(f"submit_renders: reconciling {reconcile_path}")
        try:
            result = connection.p4.run("reconcile", "-e", "-a", reconcile_path)
            if result:
                any_files_opened = True
                _diag(
                    f"submit_renders: reconcile opened {len(result)} file(s) under {reconcile_path}"
                )
            else:
                _diag(f"submit_renders: nothing to reconcile under {reconcile_path}")
        except Exception as e:
            # P4 raises when reconcile finds no changes ("- no file(s) to reconcile");
            # treat that as a clean no-op rather than a failure.
            if "no file(s) to reconcile" in str(e):
                _diag(
                    f"submit_renders: nothing to reconcile under {reconcile_path} "
                    f"(P4 said: {e})"
                )
                continue
            logger.error(f"submit_renders: reconcile failed for {reconcile_path}: {e}")
            raise

    if not any_files_opened:
        _diag("submit_renders: no files changed since last sync; nothing to commit.")
        return None

    # Step 2: create a numbered changelist with the description.
    #
    # `fetch_change()` returns a spec whose ``Files:`` field is populated
    # with every file currently open in the default changelist. If we let
    # ``save_change`` see that populated list, stale opens left in default
    # by a prior task/job would ride along into this CL — the exact
    # over-shelving scenario the scoped `reopen`/`revert -a` below is
    # meant to prevent. Explicitly zero ``Files`` before save so the new
    # CL starts empty; the subsequent `reopen -c <cl> <reconcile_targets>`
    # then brings in only this task's files.
    cl_description = _build_changelist_description(
        job_name=os.getenv("DEADLINE_JOB_ID"),
        extra_description=description,
        deadline_job_id=deadline_job_id,
    )
    change_spec = connection.p4.fetch_change()
    change_spec["Description"] = cl_description
    change_spec["Files"] = []
    saved = connection.p4.save_change(change_spec)
    # save_change returns ['Change <num> created.'] on success.
    cl_number = int(saved[0].split()[1])
    logger.info(f"submit_renders: created changelist {cl_number}")

    # Step 3: move opened files into the new CL.
    #
    # Scoping this matters: `reopen -c <cl> //...` picks up EVERY opened file
    # in the client, including stale opens from prior tasks/jobs that never
    # got reverted. That's how p4test7-10 ended up shelving 2521 files per
    # task even though each task only produced a few hundred — a p4test5-era
    # bug left 2175 files opened in default, and every later Task 0 swept
    # them into its new CL via `//...`.
    #
    # For explicit_files callers we scope reopen to this task's own file
    # list; for directory-recursion callers we still use `//...` since we
    # don't have an exact list.
    reopen_targets = reconcile_targets if explicit_files else ["//..."]
    try:
        connection.p4.run("reopen", "-c", str(cl_number), *reopen_targets)
    except Exception as e:
        # If there's nothing opened at this point, P4 raises; that would mean
        # reconcile found things but they were closed before reopen, which
        # shouldn't happen in our flow. Surface loudly.
        logger.error(f"submit_renders: reopen into CL {cl_number} failed: {e}")
        raise

    # Step 3.5: revert opens whose content is identical to depot. The adaptor
    # calls `p4 edit` on the entire output dir before staging copy (to clear
    # the read-only bit on previously-submitted frames it's about to overwrite),
    # so we end up with files opened-for-edit that the new render didn't
    # actually change. `revert -a` strips those from the CL server-side via
    # content diff — keeping each commit limited to the frames that actually
    # differ. Cheap; runs entirely in P4.
    #
    # Scope revert -a to the same file list as reopen — same reason: don't
    # touch anything outside this task's outputs.
    revert_targets = reconcile_targets if explicit_files else ["//..."]
    try:
        revert_result = connection.p4.run("revert", "-a", "-c", str(cl_number), *revert_targets)
        if revert_result:
            _diag(
                f"submit_renders: revert -a stripped {len(revert_result)} "
                f"unchanged file(s) from CL {cl_number}"
            )
    except Exception as e:
        # `revert -a` returns no error when there's nothing to revert; any
        # raise here is a real P4 problem worth flagging but not failing on
        # — submit will still work, the CL will just contain no-op revisions.
        logger.warning(f"submit_renders: revert -a on CL {cl_number} failed: {e}")

    # If revert -a stripped *everything* the CL is now empty. Submit on an
    # empty CL fails with "No files to submit." — detect and clean up so the
    # caller sees the same "nothing changed" return as the no-reconcile path.
    try:
        opened = connection.p4.run("opened", "-c", str(cl_number))
    except Exception:
        opened = []
    if not opened:
        _diag(
            f"submit_renders: CL {cl_number} is empty after revert -a "
            f"(no frames changed since last sync); deleting empty CL."
        )
        try:
            connection.p4.run("change", "-d", str(cl_number))
        except Exception as e:
            logger.warning(f"submit_renders: failed to delete empty CL {cl_number}: {e}")
        return None

    # Step 4: submit (with retry on transient errors) or shelve.
    if mode == "shelve":
        logger.info(f"submit_renders: shelving CL {cl_number}")
        connection.p4.run("shelve", "-c", str(cl_number))
        # Emit so a downstream OpenJD task can pick it up.
        logger.info(f"openjd_env: SHELVED_CL={cl_number}")
        logger.info(f"openjd_status: Shelved CL {cl_number}")
        # `p4 shelve` leaves files opened in the source CL. If we don't revert
        # them, a downstream AssembleShelves step's `unshelve -c <aggregate>`
        # will fail silently on every file ("already opened for add in change
        # N") and only Task 0's frames land in the aggregate. Revert -k drops
        # the local open metadata without touching the working file, so the
        # source CL becomes empty and unshelve can move the file cleanly.
        try:
            revert_after = connection.p4.run("revert", "-k", "-c", str(cl_number), "//...")
            _diag(
                f"submit_renders: reverted local opens on shelved CL "
                f"{cl_number} ({len(revert_after) if revert_after else 0} file(s)) "
                f"so downstream unshelve can move them"
            )
        except Exception as e:
            logger.warning(
                f"submit_renders: revert -k on shelved CL {cl_number} failed: {e}. "
                f"Downstream unshelve may fail to pick up files."
            )
        return cl_number

    last_exc: Optional[Exception] = None
    for attempt in range(1, max_submit_retries + 1):
        try:
            connection.p4.run("submit", "-c", str(cl_number))
            logger.info(f"openjd_status: Submitted CL {cl_number}")
            return cl_number
        except Exception as e:
            last_exc = e
            if not _is_transient_submit_error(e):
                logger.error(f"submit_renders: non-transient submit error: {e}")
                raise
            if attempt >= max_submit_retries:
                logger.error(
                    f"submit_renders: submit of CL {cl_number} failed after "
                    f"{max_submit_retries} attempts: {e}"
                )
                raise
            logger.warning(
                f"submit_renders: transient submit error on attempt {attempt}/"
                f"{max_submit_retries}, retrying in {submit_retry_sleep_seconds}s: {e}"
            )
            time.sleep(submit_retry_sleep_seconds)

    # Unreachable — the loop either returns or raises — but keeps mypy happy.
    raise last_exc or RuntimeError("submit_renders: unreachable")


def _find_shelved_cls_for_job(
    connection: "perforce.PerforceConnection",
    deadline_job_id: str,
    p4_user: Optional[str] = None,
) -> list[int]:
    """
    Discover shelved changelists produced by all render tasks of a given
    Deadline job across all workers.

    Uses the marker line stamped into every task-shelved CL description by
    ``_build_changelist_description``: ``DeadlineCloudRenderShelve/<job-id>``
    on the first line. Zero client-side coordination — resilient to worker
    death mid-job because we're querying P4 server state.

    :param connection: Live PerforceConnection.
    :param deadline_job_id: The Deadline job whose task shelves we want.
    :param p4_user: Optional P4 user to scope the query. When set, filters
        with ``-u`` for a much smaller server-side set. Defaults to the
        connected P4USER.

    :return: Sorted list of shelved CL numbers (ascending, so unshelve
        applies task 1's frames before task 2's — order doesn't matter for
        correctness since we `revert -a` no-ops later, but it makes the log
        deterministic).
    """
    args = ["changes", "-s", "shelved", "-l"]
    if p4_user:
        args += ["-u", p4_user]
    try:
        rows = connection.p4.run(*args)
    except Exception as e:
        logger.error(
            f"assemble_shelves: `p4 changes -s shelved` failed: {e}. "
            f"Cannot discover task shelves for job {deadline_job_id!r}."
        )
        raise

    marker = f"{DEADLINE_CL_MARKER_PREFIX}{deadline_job_id}"
    matched: list[int] = []
    for row in rows:
        # `changes -l` returns dicts with 'change' and 'desc'. The marker
        # is on the first line of the description.
        desc = (row.get("desc") or "").strip()
        first_line = desc.splitlines()[0] if desc else ""
        if first_line.strip() == marker:
            try:
                matched.append(int(row["change"]))
            except (KeyError, ValueError):
                continue
    matched.sort()
    return matched


def assemble_shelves(
    unreal_project_name: str,
    deadline_job_id: str,
    final_mode: str,
    max_submit_retries: int = 3,
    submit_retry_sleep_seconds: float = 2.0,
) -> Optional[int]:
    """
    Aggregate every render task's shelved CL for this Deadline job into a
    single new changelist, then either shelve or submit that aggregate CL
    based on ``final_mode``.

    Runs once per job as a downstream OpenJD step (dependencies:
    ``[{ dependsOn: "Render" }]``). Discovers per-task shelves via the
    ``DeadlineCloudRenderShelve/<job-id>`` marker in each shelved CL's
    description — no client-side coordination needed.

    Best-effort semantics on partial task success: aggregates whatever
    shelves it finds. Deadline's ``maxFailedTasksCount`` is the customer's
    lever for "abort if too many render tasks failed" — when the job is
    canceled from failure count, this step never runs. When the job runs
    to completion but tasks that succeeded produced fewer shelves than
    expected (e.g. some tasks rendered content already in depot), we still
    aggregate what we have. Only zero shelves fails.

    :param unreal_project_name: Project name used to resolve the workspace
        (must match what the render tasks used — same P4 client is required
        for unshelve operations).
    :param deadline_job_id: The Deadline job ID (from ``DEADLINE_JOB_ID``).
        Used to discover which shelves belong to this job.
    :param final_mode: ``"submit"`` or ``"shelve"``. Determines what happens
        to the aggregated CL after unshelving all task shelves into it.
    :param max_submit_retries: Passed through to submit retry logic when
        ``final_mode="submit"``.
    :param submit_retry_sleep_seconds: Passed through.

    :return: The final aggregated CL number (submitted or shelved), or
        ``None`` if the job produced zero task shelves in a way that's
        acceptable (currently unreachable — zero shelves raises).
    :raises RuntimeError: If zero task shelves were found. This indicates
        either every render task no-op'd (all frames already in depot,
        which suggests a broken job configuration), or the marker convention
        broke. Either way the operator needs to see it.
    """
    if final_mode not in ("submit", "shelve"):
        raise ValueError(
            f"assemble_shelves final_mode must be 'submit' or 'shelve', got {final_mode!r}"
        )
    if not deadline_job_id:
        raise ValueError("assemble_shelves: deadline_job_id is required")

    workspace_name = get_workspace_name(project_name=unreal_project_name)
    logger.info(
        f"assemble_shelves: using workspace {workspace_name!r} for job {deadline_job_id!r}, "
        f"final_mode={final_mode!r}"
    )
    connection = perforce.PerforceConnection()
    connection.p4.client = workspace_name

    # Step 1: discover all task shelves for this Deadline job.
    task_shelved_cls = _find_shelved_cls_for_job(
        connection=connection,
        deadline_job_id=deadline_job_id,
        p4_user=connection.p4.user,
    )
    if not task_shelved_cls:
        # Failing loudly here is intentional — see docstring. If every
        # render task really produced no diffs (e.g. deterministic re-render
        # of already-committed frames), an operator seeing "no CL from a
        # 100-task job" is far better served by a failure than silent
        # success.
        raise RuntimeError(
            f"assemble_shelves: no shelved CLs found for Deadline job "
            f"{deadline_job_id!r}. Either every render task produced no diffs "
            f"vs depot (unusual for a real render job), or the marker "
            f"convention is broken. Check task logs for shelve errors."
        )
    logger.info(
        f"assemble_shelves: discovered {len(task_shelved_cls)} task shelve(s): "
        f"{task_shelved_cls}"
    )

    # Step 2: create a fresh CL for the aggregate.
    #
    # Stamp the aggregate with ``DEADLINE_CL_AGGREGATE_MARKER_PREFIX``, NOT
    # the task-shelve prefix. `_find_shelved_cls_for_job` filters on the
    # task prefix only, so the aggregate is invisible to task-shelve
    # discovery on a retry / re-submitted job — otherwise, a re-run would
    # find the previously-shelved aggregate and re-wrap it as if it were
    # a task shelve. We still record the job ID (via the aggregate marker
    # AND via the standard `Job ID:` env-var line) so a human grepping
    # `p4 changes -l` can trace the aggregate back to its Deadline job.
    aggregate_desc = _build_changelist_description(
        job_name=os.getenv("DEADLINE_JOB_ID"),
        extra_description=(
            f"Aggregate of {len(task_shelved_cls)} render task shelve(s): " f"{task_shelved_cls}"
        ),
        deadline_job_id=deadline_job_id,
        marker_prefix=DEADLINE_CL_AGGREGATE_MARKER_PREFIX,
    )
    change_spec = connection.p4.fetch_change()
    change_spec["Description"] = aggregate_desc
    # Same defensive Files clear as submit_renders: `fetch_change` auto-
    # populates Files from the default CL, so anything stale in default
    # would ride along into the aggregate on save. Unshelve then explicitly
    # brings in only the task-shelve content we want.
    change_spec["Files"] = []
    saved = connection.p4.save_change(change_spec)
    aggregate_cl = int(saved[0].split()[1])
    logger.info(f"assemble_shelves: created aggregate CL {aggregate_cl}")

    # Step 3: unshelve each task's files into the aggregate CL, then delete
    # both the source shelve and the (now-empty) source CL. Once the files
    # have been consumed into the aggregate, the empty source CL number
    # carries no useful information — its description marker only helped us
    # find the shelve. Leaving hundreds of empty pending CLs behind after
    # every job pollutes `p4 changes` output for no benefit.
    # In a distributed job each render worker created its per-task
    # shelves on its own P4 client, but the assemble step runs on a
    # different worker's client. `p4 unshelve -s <src>` reads the
    # shelved content cross-client (that's what shelves are for). But
    # the source CL's own management ops (`shelve -d -c <src>`,
    # `change -d <src>`) modify the source CL and P4 requires the
    # connection to present as the owning client.
    #
    # We handle this by leaving unshelve alone (cross-client is fine)
    # and temporarily switching the p4python connection's `.client`
    # attribute to the source CL's owner for the two cleanup ops. This
    # is a local-only relabeling of the connection — no lock, no
    # file-system access on that other worker, no interference with any
    # concurrent work happening there. Same P4 user, just presenting a
    # different client identity to the server.
    aggregate_client = connection.p4.client
    unshelved_ok: list[int] = []
    unshelve_failures: list[tuple[int, str]] = []
    for src_cl in task_shelved_cls:
        # Unshelve the source's content into the aggregate CL. This is the
        # only step that must succeed for correctness.
        #
        # We intentionally do NOT delete the source shelve/source CL here.
        # If finalize (Step 5) fails after we've already destroyed the
        # sources, a Deadline retry of this step would find zero shelves
        # via `_find_shelved_cls_for_job` and abort — the whole job would
        # be unrecoverable. Instead, we defer source cleanup until after
        # finalize succeeds so this step stays retryable.
        try:
            # -f (force): overwrite workspace files even if they exist
            # and are writable. Each per-task shelve leaves its rendered
            # frames on the worker's disk (writable, not tracked by P4
            # after our revert -k). Without -f, unshelve refuses to
            # 'clobber' them.
            connection.p4.run("unshelve", "-f", "-s", str(src_cl), "-c", str(aggregate_cl))
            unshelved_ok.append(src_cl)
        except Exception as e:
            unshelve_failures.append((src_cl, f"unshelve: {e}"))
            _diag(
                f"assemble_shelves: unshelve -f -s {src_cl} -c "
                f"{aggregate_cl} FAILED: {e}. Skipping this task's shelve."
            )
            continue

    _diag(
        f"assemble_shelves: unshelved {len(unshelved_ok)}/{len(task_shelved_cls)} "
        f"task shelve(s) into aggregate CL {aggregate_cl}"
    )
    if unshelve_failures:
        _diag(
            f"assemble_shelves: {len(unshelve_failures)} task shelve(s) could "
            f"not be aggregated: {unshelve_failures}"
        )

    # Step 4: verify the aggregate has anything at all before finalizing.
    try:
        opened = connection.p4.run("opened", "-c", str(aggregate_cl))
    except Exception:
        opened = []
    if not opened:
        # Every unshelve failed. Delete the empty aggregate CL and fail —
        # same reasoning as zero-shelves: operator must see this.
        logger.error(
            f"assemble_shelves: aggregate CL {aggregate_cl} is empty after "
            f"unshelving all {len(task_shelved_cls)} source shelves. "
            f"Deleting empty CL and failing."
        )
        try:
            connection.p4.run("change", "-d", str(aggregate_cl))
        except Exception:
            # Best-effort cleanup of the empty aggregate CL. The real error we
            # want the operator to see is the RuntimeError below; a stray
            # pending CL is cosmetic compared to the aggregation failure.
            pass
        raise RuntimeError(
            f"assemble_shelves: aggregate CL was empty; every unshelve failed. "
            f"Failures: {unshelve_failures}"
        )

    # Step 5: finalize based on the customer's SubmitMode choice.
    #
    # Source-shelve/source-CL cleanup happens only after finalize succeeds
    # (via `_cleanup_task_shelves` below). If we cleaned up before finalize
    # and finalize then failed, a Deadline retry of this step would find
    # zero task shelves and give up — the whole job would be unrecoverable.
    if final_mode == "shelve":
        connection.p4.run("shelve", "-c", str(aggregate_cl))
        # Also revert the local opened files so the workspace doesn't sit
        # with pending changes after we shelve.
        connection.p4.run("revert", "-c", str(aggregate_cl), "//...")
        logger.info(f"openjd_env: SHELVED_CL={aggregate_cl}")
        logger.info(f"assemble_shelves: complete. Final aggregate CL {aggregate_cl} shelved.")
        _cleanup_task_shelves(connection, unshelved_ok, aggregate_client)
        return aggregate_cl

    # final_mode == "submit"
    last_exc: Optional[Exception] = None
    for attempt in range(1, max_submit_retries + 1):
        try:
            connection.p4.run("submit", "-c", str(aggregate_cl))
            logger.info(f"assemble_shelves: complete. Final aggregate CL {aggregate_cl} submitted.")
            _cleanup_task_shelves(connection, unshelved_ok, aggregate_client)
            return aggregate_cl
        except Exception as e:
            last_exc = e
            if not _is_transient_submit_error(e):
                logger.error(f"assemble_shelves: non-transient submit error: {e}")
                raise
            if attempt >= max_submit_retries:
                logger.error(
                    f"assemble_shelves: submit of aggregate CL {aggregate_cl} "
                    f"failed after {max_submit_retries} attempts: {e}"
                )
                raise
            logger.warning(
                f"assemble_shelves: transient submit error on attempt "
                f"{attempt}/{max_submit_retries}, retrying in "
                f"{submit_retry_sleep_seconds}s: {e}"
            )
            time.sleep(submit_retry_sleep_seconds)

    raise last_exc or RuntimeError("assemble_shelves: unreachable")


def _cleanup_task_shelves(
    connection: "perforce.PerforceConnection",
    task_shelved_cls: list[int],
    aggregate_client: str,
) -> None:
    """
    Best-effort cleanup of source shelves and source CLs after their content
    has been unshelved into the aggregate CL AND the aggregate has been
    successfully finalized.

    Runs after finalize so a finalize failure leaves the source shelves
    intact for a Deadline step retry to find via
    ``_find_shelved_cls_for_job``. If cleanup itself fails, we log and move
    on — a stray shelve or empty pending CL doesn't affect correctness of
    the already-finalized aggregate.

    In a distributed job each worker created its per-task shelves on its
    own client. ``shelve -d -c <src>`` and ``change -d <src>`` require the
    connection to present as the owning client, so we swap
    ``connection.p4.client`` around those two ops per source CL and
    restore the aggregate client afterward.
    """
    for src_cl in task_shelved_cls:
        try:
            src_describe = connection.p4.run("describe", "-s", str(src_cl))
            src_client = src_describe[0].get("client") if src_describe else None
        except Exception as e:
            logger.warning(
                f"assemble_shelves cleanup: could not describe CL {src_cl}: {e}. "
                f"Leaving source shelve/CL."
            )
            continue

        switched = bool(src_client) and src_client != aggregate_client
        if switched:
            connection.p4.client = src_client
        try:
            try:
                connection.p4.run("shelve", "-d", "-c", str(src_cl))
            except Exception as e:
                logger.warning(
                    f"assemble_shelves cleanup: failed to delete source shelve "
                    f"on CL {src_cl}: {e}"
                )
            try:
                connection.p4.run("change", "-d", str(src_cl))
            except Exception as e:
                logger.warning(
                    f"assemble_shelves cleanup: failed to delete now-empty source "
                    f"CL {src_cl}: {e}"
                )
        finally:
            if switched:
                connection.p4.client = aggregate_client


def apply_perforce_secrets() -> None:
    """
    Apply secrets from Boto3 SecretsManager to Perforce environment variables. Try to find secret
    by name stored in AWS_SECRET_P4INFO and apply all key/value pairs from it as environment variables.

    The following environment variables can be set:

    - P4USER
    - P4PASSWD
    - P4PORT

    """

    logger.info("Applying perforce secrets from Boto3 SecretsManager ...")

    p4_info = secret_manager.get_perforce_info()
    if not p4_info:
        logger.info("No perforce secrets found in Boto3 SecretsManager. Skip applying")
        return

    for env_name, env_value in p4_info.items():
        # For some reason, adaptor doesn't show logger records, need to R&D
        logger.info(f"openjd_redacted_env: {env_name}={env_value}")
