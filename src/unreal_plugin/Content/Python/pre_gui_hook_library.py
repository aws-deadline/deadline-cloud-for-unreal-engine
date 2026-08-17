# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Python implementation of the C++ ``UDeadlineCloudPreGuiHookLibrary`` bridge.

``FDeadlineCloudJobDetails::CustomizeDetails`` (C++) calls ``RunPreGuiHooks`` once per
``UDeadlineCloudJob`` instance, before the Details-panel field widgets are built, so studios
can pre-populate the Job Shared Settings from ``DEADLINE_HOOKS_DIR`` pre-GUI hooks — the true
"pre-GUI" hook point for Unreal.

This runs deadline-cloud's public ``run_pre_gui_hooks`` and routes the merged output through its
public ``apply_pre_gui_output`` (the same contract the standalone submitter and the other DCCs
use, so the panel never drifts from it), then marshals the routed result into a
``FDeadlineCloudPreGuiHookOutput`` UStruct for the C++ side to apply onto the ``UDeadlineCloudJob``.
The only Unreal-specific step layered on top is mapping the ``deadline:`` shared settings onto the
struct's typed fields (priority/initial state/max failed/max retries).
"""

import unreal

from deadline.unreal_logger import get_logger

logger = get_logger()

# deadline: shared-setting keys, each mapped onto a JobSharedSettings field (with a bHas* flag
# so C++ only overwrites a field the hook actually provided).
_DEADLINE_PRIORITY = "deadline:priority"
_DEADLINE_INITIAL_STATE = "deadline:targetTaskRunStatus"
_DEADLINE_MAX_FAILED = "deadline:maxFailedTasksCount"
_DEADLINE_MAX_RETRIES = "deadline:maxRetriesPerTask"

# OpenJD template parameters the Unreal submitter resolves from the machine at submit time (project path,
# extra cmd args, Perforce/UGS settings, conda packages, and the dynamic-chunking frame range). A pre-GUI
# hook must NOT set these: RenderUnrealOpenJob's _build_parameter_values fills them only when their value is
# still unset, so a hook-supplied value would suppress the machine-correct one and bake a stale/wrong value
# onto the submitted job (e.g. a hook that sets Frames makes _build_frames_parameter_value short-circuit,
# so the MRQ playback range is never computed and the job renders whatever the hook guessed). This is the
# same protection the (removed) submit-time path enforced via cli_provided_param_names, applied here at the
# one entry point that remains. Keep in sync with the job-level auto-resolved names in OpenJobParameterNames
# (deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity).
_SUBMITTER_MANAGED_PARAMETER_NAMES = frozenset(
    {
        "ProjectFilePath",
        "ProjectName",
        "ProjectRelativePath",
        "ExtraCmdArgs",
        "ExtraCmdArgsFile",
        "ExecutableRelativePath",
        "MrqJobDependenciesDescriptor",
        "CondaPackages",
        "MarketplacePluginsDir",
        "PerforceStreamPath",
        "PerforceChangelistNumber",
        "PerforceWorkspaceSpecificationTemplate",
        # Dynamic chunking (TASK_CHUNKING) job-level parameters — derived from the MRQ playback range /
        # chunking settings; a hook value silently suppresses the machine-computed range.
        "Frames",
        "TargetRuntimeSeconds",
        "RangeConstraint",
    }
)


def _unreal_hook_confirmation(sources):
    """Unreal-native confirmation for pre-GUI hooks (Unreal has no Qt).

    Lists the hooks that will run and asks the user through ``unreal.EditorDialog``; returns True
    to proceed. The detailed per-hook listing relies on deadline-cloud internals
    (``_generate_hooks_confirmation_message`` and the ``HookManager._original_bundle_dir`` /
    ``source_label`` attributes). If those private symbols change or disappear within the supported
    deadline range, we degrade to a generic consent prompt rather than letting the confirmation
    raise (which would bubble out as a failed hook run and silently skip the hooks) — this dialog
    remains the informed-consent point for running arbitrary code from ``DEADLINE_HOOKS_DIR``.
    """
    try:
        from deadline.client.job_bundle._hooks import _generate_hooks_confirmation_message

        confirmation_msg = "".join(
            _generate_hooks_confirmation_message(m.hooks, m._original_bundle_dir, m.source_label)
            for m in sources
            if m.hooks
        )
    except Exception:
        logger.warning(
            "Could not build the detailed pre-GUI hook confirmation message (deadline-cloud "
            "internals changed?); falling back to a generic consent prompt.",
            exc_info=True,
        )
        source_count = sum(1 for m in sources if getattr(m, "hooks", None))
        confirmation_msg = (
            f"{source_count} environment pre-GUI hook source(s) from DEADLINE_HOOKS_DIR "
            "will run.\n\n"
        )

    reply = unreal.EditorDialog.show_message(
        "Job Submission Confirmation",
        confirmation_msg + "Do you want to run these hooks?",
        unreal.AppMsgType.YES_NO,
        unreal.AppReturnType.NO,
    )
    return reply == unreal.AppReturnType.YES


def _value_type_for(value):
    """Best-effort parameter value type for a hook-provided value.

    Note: the C++ enum is ``EValueType``, but UnrealEngine's Python bindings strip the leading ``E``
    from UENUM names, so it is addressed here as ``unreal.ValueType`` (matching the rest of the
    plugin, e.g. ``open_job_template_api.py``). ``unreal.EValueType`` raises ``AttributeError``.
    """
    if isinstance(value, bool):
        return unreal.ValueType.STRING
    if isinstance(value, int):
        return unreal.ValueType.INT
    if isinstance(value, float):
        return unreal.ValueType.FLOAT
    return unreal.ValueType.STRING


class _HookSettings:
    """Assignable ``name`` / ``description`` target for deadline-cloud's ``apply_pre_gui_output``.

    ``apply_pre_gui_output`` is duck-typed: it only needs a settings object with assignable
    ``name`` / ``description`` and an optional ``parameters`` list. The panel has no job-template
    parameter list at hook time — the C++ side (``ApplyOutputToJob``) matches parameters onto the
    job by name afterward — so we expose no ``parameters`` attribute, which makes the router treat
    every hook parameter as a shared value and route it into our shared-values dict for us to map
    onto the struct. ``None`` means "the hook did not set this field".
    """

    def __init__(self):
        self.name = None
        self.description = None


def _build_output(settings=None, shared_values=None):
    """Marshal pre-GUI hook results into a ``FDeadlineCloudPreGuiHookOutput`` UStruct.

    ``settings is None`` => a clean no-op output (``ran = False``) so the C++ caller leaves the
    panel untouched (used for every "no hooks / declined / unavailable / errored" path). Otherwise
    ``ran = True`` and only the fields the hook actually set (``settings.name``/``description`` and
    the ``deadline:`` keys in ``shared_values``) are written; other ``shared_values`` become
    template ``parameters`` or, for unknown ``deadline:`` keys, ``unapplied_keys``.

    Property names: UnrealEngine's Python bindings strip the leading ``b`` from ``bool`` UPROPERTYs,
    so the C++ ``bRan``/``bHasName``/... fields are addressed here as ``"ran"``/``"has_name"``/...
    (NOT ``"b_ran"``, which raises "Failed to find property"). Non-bool fields keep their snake_case
    name (``name``, ``priority``, ``parameters``, ...). This function is the single place that names
    struct properties, so ``test_pre_gui_hook_library`` can pin them against the real struct.
    """
    out = unreal.DeadlineCloudPreGuiHookOutput()
    if settings is None:
        out.set_editor_property("ran", False)
        return out

    out.set_editor_property("ran", True)

    if settings.name is not None:
        out.set_editor_property("has_name", True)
        out.set_editor_property("name", str(settings.name))
    if settings.description is not None:
        out.set_editor_property("has_description", True)
        out.set_editor_property("description", str(settings.description))

    template_params = []
    unapplied = []
    for key, value in (shared_values or {}).items():
        if key == _DEADLINE_PRIORITY:
            out.set_editor_property("has_priority", True)
            out.set_editor_property("priority", int(value))
        elif key == _DEADLINE_INITIAL_STATE:
            out.set_editor_property("has_initial_state", True)
            out.set_editor_property("initial_state", str(value))
        elif key == _DEADLINE_MAX_FAILED:
            out.set_editor_property("has_max_failed_tasks_count", True)
            out.set_editor_property("maximum_failed_tasks_count", int(value))
        elif key == _DEADLINE_MAX_RETRIES:
            out.set_editor_property("has_max_retries_per_task", True)
            out.set_editor_property("maximum_retries_per_task", int(value))
        elif key.startswith("deadline:"):
            # A deadline: property this Unreal panel has no field for.
            unapplied.append(key)
        elif key in _SUBMITTER_MANAGED_PARAMETER_NAMES:
            # Submitter-managed at submit time (ProjectFilePath / ExtraCmdArgs / Perforce / ...); a hook
            # value here would suppress the machine-resolved one, so route it to unapplied instead of
            # baking it onto the job. See _SUBMITTER_MANAGED_PARAMETER_NAMES.
            unapplied.append(key)
        else:
            # Job-template parameter — the C++ side applies these onto ParameterDefinition
            # by name; values that don't match a template param are effectively ignored.
            pd = unreal.ParameterDefinition()
            pd.set_editor_property("name", str(key))
            pd.set_editor_property("type", _value_type_for(value))
            pd.set_editor_property("value", str(value))
            template_params.append(pd)

    if template_params:
        out.set_editor_property("parameters", template_params)
    if unapplied:
        out.set_editor_property("unapplied_keys", [str(k) for k in unapplied])
        logger.warning(
            "Pre-GUI hook parameter(s) %s have no corresponding Unreal Job Shared Setting "
            "and were not applied." % ", ".join(sorted(unapplied))
        )

    return out


@unreal.uclass()
class DeadlineCloudPreGuiHookLibraryImplementation(unreal.DeadlineCloudPreGuiHookLibrary):
    @unreal.ufunction(override=True)
    def run_pre_gui_hooks(self, job_name, priority, current_parameters):
        """Run env-only pre-GUI hooks and return merged output as FDeadlineCloudPreGuiHookOutput.

        ``job_name`` / ``priority`` / ``current_parameters`` carry the job's *current* state into the
        hook context so hooks can adjust (not just set) it — matching the other DCCs (e.g. "cap
        priority at 60", "if OutputPath is under /scratch, SUSPEND"). ``current_parameters`` is the
        list of ``unreal.ParameterDefinition`` the C++ side reads from the job's template params.

        Every failure path (API unavailable, no hooks, user declined, error) returns
        ``_build_output()`` (``ran = False``) so the C++ caller treats it as a clean no-op.
        """
        try:
            from deadline.client.config import config_file
            from deadline.client.exceptions import DeadlineOperationCanceled
            from deadline.client.ui.pre_gui_hooks import (
                PreGuiHookContext,
                apply_pre_gui_output,
                run_pre_gui_hooks,
            )
        except Exception:
            logger.warning(
                "Pre-GUI hooks unavailable (deadline.client.ui.pre_gui_hooks not importable); "
                "skipping panel pre-population."
            )
            return _build_output()

        # Confirmation gated by settings.auto_accept, matching the submitter and the other DCCs.
        try:
            auto_accept = config_file.str2bool(config_file.get_setting("settings.auto_accept"))
        except Exception:
            auto_accept = False
        confirm_callback = None if auto_accept else _unreal_hook_confirmation

        # "Untitled" / "" is the C++ default (unset) Job name; normalize to "" so a hook can tell
        # "unset" from a real name — matching the ["", "Untitled"] filter in
        # UnrealOpenJob.from_data_asset. (The final submitted name is resolved later on the MRQ path.)
        normalized_job_name = "" if str(job_name) in ("", "Untitled") else str(job_name)

        # Current template parameters (unreal.ParameterDefinition list) -> {name: value}, so a hook
        # can read the job's current parameters and adjust them, matching the other DCCs. Each entry
        # is read defensively (a malformed one is skipped rather than aborting the whole context).
        current_params: dict = {}
        for pd in current_parameters or []:
            try:
                current_params[str(pd.get_editor_property("name"))] = str(
                    pd.get_editor_property("value")
                )
            except Exception:
                continue

        try:
            merged = run_pre_gui_hooks(
                PreGuiHookContext(
                    bundle_dir=None,
                    job_name=normalized_job_name,
                    priority=int(priority),
                    parameters=current_params,
                    submitter_name="unreal",
                ),
                confirm_callback=confirm_callback,
            )
        except DeadlineOperationCanceled as e:
            logger.info(f"Pre-GUI hooks declined by user: {e}")
            return _build_output()
        except Exception:
            import traceback

            logger.warning(
                f"Pre-GUI hooks failed; leaving panel unchanged:\n{traceback.format_exc()}"
            )
            return _build_output()

        if not merged:
            return _build_output()

        # Route name/description + the template-param vs shared-value split through deadline-cloud's
        # public apply_pre_gui_output — the same contract the standalone submitter and the other
        # DCCs use — so this panel never drifts from it. _HookSettings exposes no `parameters` list,
        # so every hook parameter lands in shared_values; the C++ side (ApplyOutputToJob) matches
        # template params onto the job by name afterward. _build_output then maps the deadline:
        # shared settings onto the typed FDeadlineCloudPreGuiHookOutput fields.
        #
        # Wrapped so a surprise in the apply/mapping contract (e.g. apply_pre_gui_output requiring a
        # `parameters` attribute _HookSettings intentionally omits) degrades to a bRan=False no-op
        # rather than escaping into the C++ BlueprintImplementableEvent caller.
        try:
            settings = _HookSettings()
            shared_values: dict = {}
            apply_pre_gui_output(merged, settings, shared_values)
            return _build_output(settings, shared_values)
        except Exception:
            import traceback

            logger.warning(
                "Applying pre-GUI hook output failed; leaving panel unchanged:\n"
                f"{traceback.format_exc()}"
            )
            return _build_output()
