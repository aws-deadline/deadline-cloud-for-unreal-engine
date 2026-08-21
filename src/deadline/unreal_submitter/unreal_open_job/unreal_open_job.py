# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import re
import sys
import json
import inspect
import unreal

from enum import IntEnum
from typing import Any, Optional
from collections import OrderedDict
from dataclasses import dataclass, asdict
from pathlib import Path
import glob
from openjd.model import parse_model
from openjd.model.v2023_09 import JobTemplate, ExtensionName

from deadline.client.job_bundle.submission import AssetReferences
from deadline.client.job_bundle import deadline_yaml_dump, create_job_history_bundle_dir
from deadline.unreal_cmd_utils import merge_cmd_args_with_priority
from deadline.unreal_submitter import common, exceptions, settings
from deadline.unreal_submitter.unreal_dependency_collector import (
    DependencyCollector,
    DependencyFilters,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity import (
    Template,
    UnrealOpenJobEntity,
    OpenJobParameterNames,
    PARAMETER_DEFINITION_MAPPING,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step import (
    UnrealOpenJobStep,
    RenderUnrealOpenJobStep,
    UnrealOpenJobStepParameterDefinition,
    P4AssembleShelvesUnrealOpenJobStep,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_environment import (
    InstallMarketplacePluginsEnvironment,
    UnrealOpenJobEnvironment,
    UgsUnrealOpenJobEnvironment,
    P4UnrealOpenJobEnvironment,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_shared_settings import (
    JobSharedSettings,
)

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_parameters_consistency import (
    ParametersConsistencyChecker,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step_host_requirements import (
    HostRequirementsHelper,
)

from deadline.unreal_logger import get_logger
from deadline.unreal_perforce_utils import perforce, unreal_source_control

logger = get_logger()


class TransferProjectFilesStrategy(IntEnum):
    """
    Enumeration of ways of transferring project files

    :cvar S3: Default, with S3 file manager
    :cvar P4: with Perforce API
    :cvar UGS: with UnrealGameSync API
    """

    S3 = 0
    P4 = 1
    UGS = 2


@dataclass
class UnrealOpenJobParameterDefinition:
    """
    Dataclass for storing and managing OpenJob Parameter Definitions

    :cvar name: Name of the parameter
    :cvar type: OpenJD Type of the parameter (INT, FLOAT, STRING, PATH)
    :cvar value: Parameter value
    """

    name: str
    type: str
    value: Any = None

    @classmethod
    def from_unreal_param_definition(cls, u_param: unreal.ParameterDefinition):
        """
        Create UnrealOpenJobParameterDefinition instance from unreal.ParameterDefinition
        object.

        :return: UnrealOpenJobParameterDefinition instance
        :rtype: UnrealOpenJobParameterDefinition
        """

        build_kwargs = dict(name=u_param.name, type=u_param.type.name)
        if u_param.value:
            python_class = PARAMETER_DEFINITION_MAPPING[u_param.type.name].python_class
            # Unreal's ValueType enum never maps to task-only types such as CHUNK[INT],
            # so a python_class is always available here.
            assert python_class is not None
            build_kwargs["value"] = python_class(u_param.value)
        return cls(**build_kwargs)

    @classmethod
    def from_dict(cls, param_dict: dict):
        """
        Create UnrealOpenJobParameterDefinition instance python dict.
        If source dict has "default" key, use its value

        :return: UnrealOpenJobParameterDefinition instance
        :rtype: UnrealOpenJobParameterDefinition
        """

        build_kwargs = dict(name=param_dict["name"], type=param_dict["type"])
        if "default" in param_dict:
            build_kwargs["value"] = param_dict["default"]

        return cls(**build_kwargs)

    def to_dict(self):
        """
        Return UnrealOpenJobParameterDefinition as dictionary

        :return: UnrealOpenJobParameterDefinition as python dictionary
        :rtype: dict[str, Any]
        """

        return asdict(self)


@dataclass
class ProfilingSettings:
    insights_cpu: bool = False
    insights_gpu: bool = False
    insights_memory: bool = False
    csv_profiler: bool = False
    csv_capture_frames: int = 300
    memreport: bool = False

    @staticmethod
    def _read_unreal_property(source: Any, *property_names: str) -> Any:
        getter = getattr(source, "get_editor_property", None)
        read_errors = []
        for property_name in property_names:
            try:
                inspect.getattr_static(source, property_name)
            except AttributeError:
                pass
            else:
                try:
                    return getattr(source, property_name)
                except Exception as exc:
                    read_errors.append(exc)

            if getter:
                try:
                    return getter(property_name)
                except Exception as exc:
                    read_errors.append(exc)

        supported_names = ", ".join(f"'{name}'" for name in property_names)
        error = exceptions.SubmitterInputValidationError(
            f"Unable to read required profiling property '{property_names[0]}'. "
            f"Supported property names: {supported_names}."
        )
        if read_errors:
            raise error from read_errors[-1]
        raise error

    @staticmethod
    def _coerce_bool(value: Any, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int) and not isinstance(value, bool):
            return bool(value)
        return default

    @staticmethod
    def _coerce_int(value: Any, default: int) -> int:
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        return default

    @classmethod
    def from_u_deadline_cloud_profiling_settings(
        cls, profiling_settings: Optional[unreal.DeadlineCloudProfilingSettingsStruct]
    ) -> "ProfilingSettings":
        if profiling_settings is None:
            return cls()

        return cls(
            insights_cpu=cls._coerce_bool(
                cls._read_unreal_property(profiling_settings, "insights_cpu", "bInsightsCpu")
            ),
            insights_gpu=cls._coerce_bool(
                cls._read_unreal_property(profiling_settings, "insights_gpu", "bInsightsGpu")
            ),
            insights_memory=cls._coerce_bool(
                cls._read_unreal_property(
                    profiling_settings,
                    "insights_memory",
                    "bInsightsMemory",
                )
            ),
            csv_profiler=cls._coerce_bool(
                cls._read_unreal_property(profiling_settings, "csv_profiler", "bCsvProfiler")
            ),
            csv_capture_frames=max(
                1,
                cls._coerce_int(
                    cls._read_unreal_property(
                        profiling_settings, "csv_capture_frames", "CsvCaptureFrames"
                    ),
                    300,
                ),
            ),
            memreport=cls._coerce_bool(
                cls._read_unreal_property(
                    profiling_settings, "memreport", "mem_report", "bMemReport"
                )
            ),
        )

    def is_insights_enabled(self) -> bool:
        return self.insights_cpu or self.insights_gpu or self.insights_memory

    def is_enabled(self) -> bool:
        return self.is_insights_enabled() or self.csv_profiler or self.memreport

    def build_cmd_args(self) -> str:
        trace_categories: OrderedDict[str, str] = OrderedDict()
        if self.insights_cpu:
            for category in ("cpu", "frame", "bookmark", "loadtime"):
                trace_categories.setdefault(category, category)
        if self.insights_gpu:
            trace_categories.setdefault("gpu", "gpu")
        if self.insights_memory:
            trace_categories.setdefault("memory", "memory")

        cmd_args = []
        if trace_categories:
            cmd_args.append(f'-DeadlineCloudInsights={",".join(trace_categories.values())}')
        if self.csv_profiler:
            cmd_args.append("-csvGpuStats")
            if self.csv_capture_frames > 0:
                cmd_args.append(f"-csvCaptureFrames={self.csv_capture_frames}")
        if self.memreport:
            cmd_args.append("-MemReport")

        return " ".join(cmd_args)

    def get_output_directories(self, profiling_directory: str) -> list[str]:
        profiling_root = profiling_directory.replace("\\", "/").rstrip("/")
        output_directories = []
        if self.is_insights_enabled():
            output_directories.append(f"{profiling_root}/DeadlineCloud")
        if self.csv_profiler:
            output_directories.append(f"{profiling_root}/CSV")
        if self.memreport:
            output_directories.append(f"{profiling_root}/MemReports")
        return output_directories


# Base Open Job implementation
class UnrealOpenJob(UnrealOpenJobEntity):
    """
    Open Job for Unreal Engine
    """

    def __init__(
        self,
        file_path: Optional[str] = None,
        name: Optional[str] = None,
        steps: Optional[list[UnrealOpenJobStep]] = None,
        environments: Optional[list[UnrealOpenJobEnvironment]] = None,
        extra_parameters: Optional[list[UnrealOpenJobParameterDefinition]] = None,
        job_shared_settings: Optional[JobSharedSettings] = None,
        asset_references: Optional[AssetReferences] = None,
    ):
        """
        :param file_path: Path to the open job template file
        :type file_path: str

        :param name: Name of the job
        :type name: str

        :param steps: List of steps to be executed by deadline cloud
        :type steps: list[UnrealOpenJobStep]

        :param environments: List of environments to be used by deadline cloud
        :type environments: list[UnrealOpenJobEnvironment]

        :param extra_parameters: List of additional parameters to be added to the job
        :type extra_parameters: list[UnrealOpenJobParameterDefinition]

        :param job_shared_settings: JobSharedSettings instance
        :type job_shared_settings: JobSharedSettings

        :param asset_references: AssetReferences object
        :type asset_references: AssetReferences
        """

        super().__init__(JobTemplate, file_path, name)

        self._extra_parameters: list[UnrealOpenJobParameterDefinition] = extra_parameters or []
        self._create_missing_extra_parameters_from_template()

        self._steps: list[UnrealOpenJobStep] = steps or []
        self._environments: list[UnrealOpenJobEnvironment] = environments or []

        # Auto-inject Marketplace plugins installer if marketplace plugins exist
        # and it's not already in the environment list
        if UnrealOpenJob.get_marketplace_plugins_dir() and not any(
            isinstance(e, InstallMarketplacePluginsEnvironment) for e in self._environments
        ):
            self._environments.insert(0, InstallMarketplacePluginsEnvironment())

        self._job_shared_settings = job_shared_settings or JobSharedSettings()
        self._asset_references = asset_references or AssetReferences()

        self._transfer_files_strategy = TransferProjectFilesStrategy.S3

        # Optional Job description; only emitted into the template when set. Populated from the
        # UDeadlineCloudJob Details panel's Job Shared Settings (which a pre-GUI hook may have
        # pre-populated) via :meth:`from_data_asset`.
        self._description: str = ""

    @property
    def job_shared_settings(self) -> JobSharedSettings:
        return self._job_shared_settings

    @job_shared_settings.setter
    def job_shared_settings(self, value: JobSharedSettings):
        self._job_shared_settings = value

    @property
    def description(self) -> str:
        """Returns the Job description (empty unless set from the Details panel)."""
        return self._description

    @description.setter
    def description(self, value: str):
        self._description = value

    @staticmethod
    def _description_from_data_asset(shared_settings) -> str:
        """Return the Details-panel Job description to carry into the Job, or "" if unset.

        The description is set on the panel either by an artist or by a pre-GUI hook
        (``FDeadlineCloudJobDetails`` runs the hook and writes ``JobSharedSettings.Description``
        before the artist edits). ``"No description"`` is the C++ default (an unset sentinel), so
        it maps to ``""``. Shared by both ``from_data_asset`` implementations so the description
        reaches the template on the render (MRQ) path too — not only the base path.
        """
        description = shared_settings.description
        if description and description != "No description":
            return description
        return ""

    @classmethod
    def from_data_asset(cls, data_asset: unreal.DeadlineCloudJob) -> "UnrealOpenJob":
        """
        Create the instance of UnrealOpenJob from unreal.DeadlineCloudJob.
        Call same method on data_asset's steps, environments.

        :param data_asset: unreal.DeadlineCloudJob instance

        :return: UnrealOpenJob instance
        :rtype: UnrealOpenJob
        """

        steps = [UnrealOpenJobStep.from_data_asset(step) for step in data_asset.steps]

        shared_settings = data_asset.job_preset_struct.job_shared_settings
        result_job = cls(
            file_path=data_asset.path_to_template.file_path,
            name=None if shared_settings.name in ["", "Untitled"] else shared_settings.name,
            steps=steps,
            environments=[
                UnrealOpenJobEnvironment.from_data_asset(env) for env in data_asset.environments
            ],
            extra_parameters=[
                UnrealOpenJobParameterDefinition.from_unreal_param_definition(param)
                for param in data_asset.get_job_parameters()
            ],
            job_shared_settings=JobSharedSettings.from_u_deadline_cloud_job_shared_settings(
                shared_settings
            ),
        )

        # Carry a non-default Job description from the Details panel into the Job (see
        # _description_from_data_asset) so it reaches the job template.
        result_job.description = cls._description_from_data_asset(shared_settings)

        for step in result_job._steps:
            step.open_job = result_job

        return result_job

    @staticmethod
    def serialize_template(template: Template) -> dict[str, Any]:
        """
        Serialize given template and return ordered dictionary
        (spec version, name, parameters, envs, steps).

        :param template: Template (JobTemplate, StepTemplate, Environment)
        :type template: Union[JobTemplate, StepTemplate, Environment]

        :return: Ordered python dictionary
        :rtype: dict[str, Any]
        """

        template_json = json.loads(template.json(exclude_none=True))
        ordered_keys = [
            "specificationVersion",
            "extensions",
            "name",
            "description",
            "parameterDefinitions",
            "jobEnvironments",
            "steps",
        ]
        ordered_data = dict(
            OrderedDict((key, template_json[key]) for key in ordered_keys if key in template_json)
        )
        return ordered_data

    @staticmethod
    def update_job_parameter_values(
        job_parameter_values: list[dict[str, Any]],
        job_parameter_name: str,
        job_parameter_value: Any,
    ) -> list[dict[str, Any]]:
        """
        Try to find parameter in given list by the provided name
        and update its value wih provided value.

        :param job_parameter_values: List of parameter values dictionaries (name and value)
        :type job_parameter_values: list[dict[str, Any]]
        :param job_parameter_name: Name of the parameter to update
        :type job_parameter_name: str
        :param job_parameter_value: Value of the parameter to set
        :type job_parameter_value: Any

        :return: Given list of parameter values with possibly updated parameter
        :rtype: list[dict[str, Any]]
        """

        param = next((p for p in job_parameter_values if p["name"] == job_parameter_name), None)
        if param:
            param["value"] = job_parameter_value
        return job_parameter_values

    def _create_missing_extra_parameters_from_template(self):
        """
        Update parameters with YAML template data. Mostly needed for custom job submission process.

        If no template file found, skip updating and log warning.
        This is not an error and should not break the building process.
        """

        try:
            extra_param_names = [p.name for p in self._extra_parameters]
            for p in self.get_template_object()["parameterDefinitions"]:
                if p["name"] not in extra_param_names:
                    self._extra_parameters.append(UnrealOpenJobParameterDefinition.from_dict(p))
        except FileNotFoundError:
            logger.warning("No template file found to read parameters from.")

    def _find_extra_parameter(
        self, parameter_name: str, parameter_type: str
    ) -> Optional[UnrealOpenJobParameterDefinition]:
        """
        Find extra parameter by given name and type

        :param parameter_name: Parameter name
        :param parameter_type: Parameter type (INT, FLOAT, STRING, PATH)

        :return: Parameter if found, None otherwise
        :rtype: Optional[UnrealOpenJobParameterDefinition]
        """

        return next(
            (
                p
                for p in self._extra_parameters
                if p.name == parameter_name and p.type == parameter_type
            ),
            None,
        )

    def _build_parameter_values(self) -> list:
        """
        Build and return list of parameter values for the OpenJob. Use YAML parameter names and
        extra parameter values/YAML defaults if exists.

        :return: Parameter values list of dictionaries
        :rtype: list
        """

        job_template_object = self.get_template_object()
        parameter_values = []
        for yaml_p in job_template_object["parameterDefinitions"]:
            extra_p = self._find_extra_parameter(yaml_p["name"], yaml_p["type"])
            value = extra_p.value if extra_p else yaml_p.get("default")
            parameter_values.append(dict(name=yaml_p["name"], value=value))

        if self._job_shared_settings:
            parameter_values += self._job_shared_settings.serialize()

        if not UnrealOpenJob.check_conda_package_version(parameter_values):
            raise exceptions.UserCancelledSubmissionMismatchedUEVersion(
                "CondaPackages Unreal Engine version mismatch"
            )

        return parameter_values

    def _check_parameters_consistency(self):
        """
        Check Job parameters consistency

        :return: Result of parameters consistency check
        :rtype: ParametersConsistencyCheckResult
        """

        result = ParametersConsistencyChecker.check_job_parameters_consistency(
            job_template_path=self.file_path,
            job_parameters=[p.to_dict() for p in self._extra_parameters],
        )

        result.reason = f"OpenJob {self.name}: " + result.reason

        return result

    def _build_template(self) -> JobTemplate:
        """
        Build JobTemplate OpenJD model.

        Build process:
            1. Fill specification version for the Job
            2. Fill Job parameter definition list
            3. Build given Steps
            4. Build given Environments

        :return: JobTemplate instance
        :rtype: JobTemplate
        """

        parameter_definitions = []
        for param in self.get_template_object()["parameterDefinitions"]:
            job_parameter_class = PARAMETER_DEFINITION_MAPPING[
                param["type"]
            ].job_parameter_openjd_class
            if job_parameter_class is None:
                # Task-only types (e.g. CHUNK[INT]) have no job-level equivalent
                raise exceptions.SubmitterInputValidationError(
                    f'Job parameter "{param.get("name")}" has type "{param["type"]}" '
                    f"which is not valid at the job level"
                )
            parameter_definitions.append(job_parameter_class(**param))

        template_dict = {
            "specificationVersion": settings.JOB_TEMPLATE_VERSION,
            "name": self.name,
            "parameterDefinitions": parameter_definitions,
            "steps": [s.build_template() for s in self._steps],
        }

        # Panel/hook description wins; otherwise fall back to a top-level `description` declared in
        # the user's YAML job template (mirrors the `extensions` read-back below), so a
        # template-author's description is not silently dropped.
        description = self._description or self.get_template_object().get("description")
        if description:
            template_dict["description"] = description

        extension_list = self.get_template_object().get("extensions")

        if extension_list:
            template_dict["extensions"] = extension_list

        if self._environments:
            template_dict["jobEnvironments"] = [e.build_template() for e in self._environments]

        # Use all available extension names from the ExtensionName enum
        supported_extensions = [extension.value for extension in ExtensionName]

        job_template = parse_model(
            model=self.template_class, obj=template_dict, supported_extensions=supported_extensions
        )
        return job_template

    def get_asset_references(self) -> AssetReferences:
        """
        Return AssetReferences of itself that union given Environments and Steps' AssetReferences

        :return: AssetReferences from this Job and its Environments and Steps
        :rtype: AssetReferences
        """

        asset_references = super().get_asset_references()

        if self._asset_references:
            asset_references = asset_references.union(self._asset_references)

        for step in self._steps:
            asset_references = asset_references.union(step.get_asset_references())

        for environment in self._environments:
            asset_references = asset_references.union(environment.get_asset_references())

        return asset_references

    @staticmethod
    def _scan_plugin_dirs(path: str) -> list[tuple[str, str]]:
        """Scan a directory for .uplugin files.

        :return: List of (plugin_name, plugin_directory) tuples
        """
        results = {}
        pattern = os.path.join(path, "**", "*.uplugin")
        for uplugin in glob.iglob(pattern, recursive=True):
            name = Path(uplugin).stem
            plugin_dir = str(Path(uplugin).parent)
            results[name] = plugin_dir
        return list(results.items())

    @staticmethod
    def get_marketplace_plugins_dir() -> str:
        """Return the engine Marketplace plugins directory if it exists, empty string otherwise."""
        # engine_plugins_dir() returns the engine's plugins root directory
        # (e.g., "C:/Program Files/Epic Games/UE_5.x/Engine/Plugins/").
        # Stock plugins can be found in this folder.
        engine_plugins = unreal.Paths.convert_relative_path_to_full(
            unreal.Paths.engine_plugins_dir()
        )

        # Note: "Marketplace" is the conventional install path used by the Fab/Launcher;
        # this is not formally documented by Epic and may change in the future.
        # "Marketplace" folder is created when user installs the very first marketplace plugin.
        marketplace_dir = os.path.join(engine_plugins, "Marketplace")
        return marketplace_dir if os.path.isdir(marketplace_dir) else ""

    @staticmethod
    def get_plugins_references() -> AssetReferences:
        result = AssetReferences()
        lib = unreal.PluginBlueprintLibrary
        enabled_plugins = set(lib.get_enabled_plugin_names())

        # Directories to scan for non-stock plugins.
        # We only scan directories where user-installed plugins live, skipping the
        # stock engine plugins that ship with every UE installation.
        scan_dirs = []

        # Project-level plugins (<Project>/Plugins/)
        project_plugins = unreal.Paths.convert_relative_path_to_full(
            unreal.Paths.project_plugins_dir()
        )
        scan_dirs.append(project_plugins)

        # Engine Marketplace plugins — user-installed via Fab or the Epic Games Launcher.
        marketplace_dir = UnrealOpenJob.get_marketplace_plugins_dir()
        if marketplace_dir:
            scan_dirs.append(marketplace_dir)

        for scan_dir in scan_dirs:
            for plugin_name, plugin_dir in UnrealOpenJob._scan_plugin_dirs(scan_dir):
                if plugin_name == "UnrealDeadlineCloudService":
                    continue
                if plugin_name in enabled_plugins:
                    result.input_directories.add(plugin_dir)

        if result.input_directories:
            logger.info(
                f"Auto-detected {len(result.input_directories)} non-stock plugin(s) "
                f"as job attachments: {result.input_directories}"
            )

        return result

    def create_job_bundle(self):
        """
        Create Job bundle directory with next files inside:
            1. template.yaml - Full OpenJD Job template with steps, envs, parameters, etc.
            2. parameter_values.yaml - List of Job parameter values + Shared settings values
            3. asset_references.yaml - Input directories/files, outputs to sync with S3 on submit

        :return: Job bundle directory path
        :rtype: str
        """

        job_template = self.build_template()

        job_bundle_path = create_job_history_bundle_dir("Unreal", self.name)
        logger.info(f"Job bundle path: {job_bundle_path}")

        with open(job_bundle_path + "/template.yaml", "w", encoding="utf8") as f:
            job_template_dict = UnrealOpenJob.serialize_template(job_template)
            deadline_yaml_dump(job_template_dict, f, indent=1)

        with open(job_bundle_path + "/parameter_values.yaml", "w", encoding="utf8") as f:
            param_values = self._build_parameter_values()
            deadline_yaml_dump(dict(parameterValues=param_values), f, indent=1)

        with open(job_bundle_path + "/asset_references.yaml", "w", encoding="utf8") as f:
            asset_references = self.get_asset_references()
            deadline_yaml_dump(asset_references.to_dict(), f, indent=1)

        return job_bundle_path

    @staticmethod
    def get_current_ue_version():
        """
        Get current Unreal Engine version in x.y format

        :return: Current Unreal Engine version
        :rtype: str
        """

        current_ue_version = unreal.SystemLibrary.get_engine_version()
        logger.info(f"Current Unreal Engine version: {current_ue_version}")
        current_version_match = re.search(r"\b\d+\.\d+\b", current_ue_version)
        if not current_version_match:
            logger.warning(f"Could not parse current UE version: {current_ue_version}")
            raise exceptions.UEVersionParseError(
                f"Could not parse current UE version: {current_ue_version}"
            )

        return current_version_match.group(0)

    @staticmethod
    def normalize_openjd_version_param(param_value: str) -> str:
        """
        Check if the given CondaPackages parameter value contains openjd version.
        If not, append "unrealengine-openjd=*.*.*" to the value.
        :param param_value: CondaPackages parameter value
        :return: Updated CondaPackages parameter value
        :rtype: str
        """
        match = re.search(r"unrealengine-openjd=(?:\d+|\*)\.(?:\d+|\*)\.(?:\d+|\*)", param_value)
        if match:
            return param_value

        if re.search(r"unrealengine-openjd=[^\s]+", param_value):
            return re.sub(r"unrealengine-openjd=[^\s]+", "unrealengine-openjd=*.*.*", param_value)

        return param_value + " unrealengine-openjd=*.*.*"

    @staticmethod
    def check_conda_package_version(parameter_values: list[dict[str, Any]]) -> bool:
        """
        Check if the CondaPackages parameter contains Unreal Engine version and compare with current UE version.

        :return: True if version check passes or user confirms, False if user cancels
        :rtype: bool
        """

        conda_packages_param = next(
            (p for p in parameter_values if p["name"] == OpenJobParameterNames.CONDA_PACKAGES), None
        )

        if not conda_packages_param:
            return True

        current_version = UnrealOpenJob.get_current_ue_version()

        conda_packages_value = conda_packages_param.get("value", "")
        if not conda_packages_value:
            conda_packages_param["value"] = UnrealOpenJob.normalize_openjd_version_param(
                f"unrealengine={current_version}"
            )
            return True

        # Check for unrealengine=x.x pattern
        ue_version_match = re.search(r"unrealengine=(\d+\.\d+)", conda_packages_value)
        if not ue_version_match:
            conda_packages_param["value"] = UnrealOpenJob.normalize_openjd_version_param(
                f"unrealengine={current_version} " + conda_packages_value
            )
            return True

        template_ue_version = ue_version_match.group(1)
        logger.info(f"Template specifies Unreal Engine version: {template_ue_version}")

        # Compare versions
        if not template_ue_version == current_version:
            # Versions don't match
            result = unreal.EditorDialog.show_message(
                "Version Mismatch Warning",
                f"You are attempting to render a UE {current_version} project using UE {template_ue_version}. Do you wish to continue?",
                unreal.AppMsgType.YES_NO,
                unreal.AppReturnType.YES,
            )

            if result != unreal.AppReturnType.YES:
                return False

        conda_packages_param["value"] = UnrealOpenJob.normalize_openjd_version_param(
            conda_packages_value
        )
        logger.info("Unreal Engine versions match, continuing with submission")
        return True


# Render Open Job
class RenderUnrealOpenJob(UnrealOpenJob):
    """
    Unreal Open Job for rendering Unreal Engine projects

    :cvar job_environment_map: Map for converting C++ environment classes to Python classes
    :cvar job_step_map: Map for converting C++ step classes to Python classes
    """

    default_template_path = settings.RENDER_JOB_TEMPLATE_DEFAULT_PATH

    job_environment_map = {
        unreal.DeadlineCloudUgsEnvironment: UgsUnrealOpenJobEnvironment,
        unreal.DeadlineCloudPerforceEnvironment: P4UnrealOpenJobEnvironment,
    }

    job_step_map = {unreal.DeadlineCloudRenderStep: RenderUnrealOpenJobStep}

    def __init__(
        self,
        file_path: Optional[str] = None,
        name: Optional[str] = None,
        steps: Optional[list[UnrealOpenJobStep]] = None,
        environments: Optional[list[UnrealOpenJobEnvironment]] = None,
        extra_parameters: Optional[list[UnrealOpenJobParameterDefinition]] = None,
        job_shared_settings: Optional[JobSharedSettings] = None,
        profiling_settings: Optional[ProfilingSettings] = None,
        asset_references: Optional[AssetReferences] = None,
        mrq_job: Optional[unreal.MoviePipelineExecutorJob] = None,
    ):
        """
        Construct RenderUnrealOpenJob instance.

        :param file_path: Path to the open job template file
        :type file_path: str

        :param name: Name of the job
        :type name: str

        :param steps: List of steps to be executed by deadline cloud
        :type steps: list[UnrealOpenJobStep]

        :param environments: List of environments to be used by deadline cloud
        :type environments: list[UnrealOpenJobEnvironment]

        :param extra_parameters: List of additional parameters to be added to the job
        :type extra_parameters: list[UnrealOpenJobParameterDefinition]

        :param job_shared_settings: JobSharedSettings instance
        :type job_shared_settings: JobSharedSettings

        :param profiling_settings: ProfilingSettings instance
        :type profiling_settings: ProfilingSettings

        :param asset_references: AssetReferences object
        :type asset_references: AssetReferences

        :param mrq_job: unreal.MoviePipelineExecutorJob instance to take render data from
        :type mrq_job: unreal.MoviePipelineExecutorJob
        """
        super().__init__(
            file_path,
            name,
            steps,
            environments,
            extra_parameters,
            job_shared_settings,
            asset_references,
        )
        self._profiling_settings = profiling_settings or ProfilingSettings()

        self._mrq_job = None
        if mrq_job:
            self.mrq_job = mrq_job

        self._dependency_collector = DependencyCollector()

        if self._name is None and isinstance(self.mrq_job, unreal.MoviePipelineExecutorJob):
            self._name = self.mrq_job.job_name

        ugs_envs = [e for e in self._environments if isinstance(e, UgsUnrealOpenJobEnvironment)]
        p4_envs = [e for e in self._environments if isinstance(e, P4UnrealOpenJobEnvironment)]
        if ugs_envs and p4_envs:
            raise exceptions.FailedToDetectFilesTransferStrategy(
                "Failed to detect how to transfer project files to render because "
                f"there are multiple options selected: "
                f"{[e.name for e in ugs_envs]} and {[e.name for e in p4_envs]}. "
                f"Use only Perforce OR only UnrealGameSync environments inside single OpenJob"
            )
        if ugs_envs:
            self._transfer_files_strategy = TransferProjectFilesStrategy.UGS
        elif p4_envs:
            self._transfer_files_strategy = TransferProjectFilesStrategy.P4

    @property
    def profiling_settings(self) -> ProfilingSettings:
        return getattr(self, "_profiling_settings", ProfilingSettings())

    @profiling_settings.setter
    def profiling_settings(self, value: ProfilingSettings):
        self._profiling_settings = value or ProfilingSettings()

    @property
    def mrq_job(self):
        return self._mrq_job

    @mrq_job.setter
    def mrq_job(self, value):
        """
        Set mrq_job as given value.
        Updates next objects:
            1. Job extra parameters from mrq job parameter definition overrides
            2. Step's parameters and environments from mrq job step overrides for each step
            3. Environment's variables from mrq job environment overrides for each environment
            4. Job name if not set by next priority:
                I. Job preset override - (highest priority)
                II. Data asset job preset struct
                III. YAML template
                IV. MRQ Job name (shot name) - lowest priority

        :param value: unreal.MoviePipelineExecutorJob instance
        :type value: unreal.MoviePipelineExecutorJob
        """

        self._mrq_job = value
        self._update_steps_settings_from_mrq_job(self._mrq_job)
        self._update_environments_settings_from_mrq_job(self._mrq_job)

        if (
            self._mrq_job is not None
            and self._mrq_job.job_template_overrides is not None
            and self._mrq_job.job_template_overrides.parameters
        ):
            extra_params_override = [
                UnrealOpenJobParameterDefinition.from_unreal_param_definition(p)
                for p in self._mrq_job.job_template_overrides.parameters
            ]
            for p in extra_params_override:
                param = self._find_extra_parameter(p.name, p.type)
                if param:
                    param.value = p.value

        if (
            self._mrq_job is not None
            and self._mrq_job.preset_overrides is not None
            and self._mrq_job.preset_overrides.job_shared_settings is not None
        ):
            override_shared_settings = self._mrq_job.preset_overrides.job_shared_settings
            self.job_shared_settings = JobSharedSettings.from_u_deadline_cloud_job_shared_settings(
                override_shared_settings
            )
            # Description lives in the same shared-settings struct. Mirror the name handling below:
            # the MRQ preset override wins only when it actually carries a description; the default
            # "No description" sentinel (mapped to "" by _description_from_data_asset) is treated as
            # "unset" and leaves the underlying data-asset / pre-GUI-hook description in place rather
            # than clearing it. PresetOverrides is a stale snapshot, so a description set (by an
            # artist or the pre-GUI hook) after the preset was assigned would otherwise be silently
            # erased while the name — which uses the same guard — survived.
            override_description = self._description_from_data_asset(override_shared_settings)
            if override_description:
                self._description = override_description

        if self._mrq_job is not None and self._mrq_job.preset_overrides is not None:
            profiling_settings = getattr(self._mrq_job.preset_overrides, "profiling_settings", None)
            if profiling_settings is not None:
                self.profiling_settings = (
                    ProfilingSettings.from_u_deadline_cloud_profiling_settings(profiling_settings)
                )

        # Job name set order:
        #   0. Job preset override (high priority)
        #   1. Get from data asset job preset struct
        #   2. Get from YAML template
        #   4. Get from mrq job name (shot name)
        if (
            self._mrq_job is not None
            and self._mrq_job.preset_overrides is not None
            and self._mrq_job.preset_overrides.job_shared_settings is not None
        ):
            preset_override_name = self._mrq_job.preset_overrides.job_shared_settings.name
            if preset_override_name not in ["", "Untitled"]:
                self._name = preset_override_name

        if self._name is None:
            self._name = self._mrq_job.job_name

    @classmethod
    def from_data_asset(cls, data_asset: unreal.DeadlineCloudRenderJob) -> "RenderUnrealOpenJob":
        """
        Create the instance of RenderUnrealOpenJob from unreal.DeadlineCloudRenderJob.
        Call same method on data_asset's steps, environments.
        Create appropriate Steps and Environments listed in job_step_map, job_environment_map

        :param data_asset: unreal.DeadlineCloudRenderJob instance

        :return: RenderUnrealOpenJob instance
        :rtype: RenderUnrealOpenJob
        """

        render_steps_count = RenderUnrealOpenJob.render_steps_count(data_asset)
        if render_steps_count != 1:
            raise exceptions.RenderStepCountConstraintError(
                f"RenderJob data asset should have exactly 1 Render Step. "
                f"Currently it has {render_steps_count} Render Steps"
            )

        steps = []
        for source_step in data_asset.steps:
            job_step_cls = cls.job_step_map.get(type(source_step), UnrealOpenJobStep)
            job_step = job_step_cls.from_data_asset(source_step)

            steps.append(job_step)

        environments = []
        for source_environment in data_asset.environments:
            job_env_cls = cls.job_environment_map.get(
                type(source_environment), UnrealOpenJobEnvironment
            )
            job_env = job_env_cls.from_data_asset(source_environment)
            environments.append(job_env)

        shared_settings = data_asset.job_preset_struct.job_shared_settings
        profiling_settings = getattr(data_asset.job_preset_struct, "profiling_settings", None)

        result_job = cls(
            file_path=data_asset.path_to_template.file_path,
            name=None if shared_settings.name in ["", "Untitled"] else shared_settings.name,
            steps=steps,
            environments=environments,
            extra_parameters=[
                UnrealOpenJobParameterDefinition.from_unreal_param_definition(param)
                for param in data_asset.get_job_parameters()
            ],
            job_shared_settings=JobSharedSettings.from_u_deadline_cloud_job_shared_settings(
                shared_settings
            ),
            profiling_settings=ProfilingSettings.from_u_deadline_cloud_profiling_settings(
                profiling_settings
            ),
        )

        # Carry the panel/hook-set description on the render (MRQ) path too — this override does not
        # call super().from_data_asset(), so it must apply the shared helper itself.
        result_job.description = cls._description_from_data_asset(shared_settings)

        for step in result_job._steps:
            step.open_job = result_job

        return result_job

    @classmethod
    def from_mrq_job(
        cls, mrq_job: unreal.MoviePipelineDeadlineCloudExecutorJob
    ) -> "RenderUnrealOpenJob":
        """
        Create the instance of RenderUnrealOpenJob from unreal.MoviePipelineDeadlineCloudExecutorJob.
        Use it job_preset to create from data asset and set mrq_job as given mrq_job.

        :param mrq_job: unreal.MoviePipelineDeadlineCloudExecutorJob instance

        :return: RenderUnrealOpenJob instance
        :rtype: RenderUnrealOpenJob
        """

        render_unreal_open_job = cls.from_data_asset(mrq_job.job_preset)
        render_unreal_open_job.mrq_job = mrq_job
        return render_unreal_open_job

    @staticmethod
    def render_steps_count(data_asset: unreal.DeadlineCloudRenderJob) -> int:
        """
        Count unreal.DeadlineCloudRenderStep in the given Render Job data asset

        :param data_asset: unreal.DeadlineCloudRenderJob instance

        :return: unreal.DeadlineCloudRenderStep count
        :rtype: int
        """

        return sum(isinstance(s, unreal.DeadlineCloudRenderStep) for s in data_asset.steps)

    @staticmethod
    def get_required_project_directories() -> list[str]:
        """
        Returns a list of required project directories such as Config and Binaries

        :return: list of required project directories
        :rtype: list
        """

        required_project_directories = []
        for sub_dir in ["Config", "Binaries"]:
            directory = common.os_abs_from_relative(sub_dir)
            if os.path.exists(directory):
                required_project_directories.append(directory)
        return required_project_directories

    def _update_steps_settings_from_mrq_job(
        self, mrq_job: unreal.MoviePipelineDeadlineCloudExecutorJob
    ):
        """
        Iterate through the Job's Steps and update settings with overrides of given MRQ Job
        for each Step.

        Settings to update:
            1. Host requirements
            2. MRQ Job (If step is RenderUnrealOpenJobStep)
            3. Step depends on list
            4. Environment variables for each Environment of the Step
            5. Step parameters

        :param mrq_job: unreal.MoviePipelineDeadlineCloudExecutorJob instance
        :type mrq_job: unreal.MoviePipelineDeadlineCloudExecutorJob
        """

        for step in self._steps:
            # set mrq job to render step
            if isinstance(step, RenderUnrealOpenJobStep):
                step.mrq_job = mrq_job

            # find appropriate step override
            step_override = next(
                (
                    override
                    for override in mrq_job.job_template_overrides.steps_overrides
                    if override.name == step.name
                ),
                None,
            )
            if not step_override:
                continue

            # update depends on
            step.step_dependencies = list(step_override.depends_on)

            # update host_req
            step_host_requirements_override = step_override.host_requirements_override
            step.host_requirements = HostRequirementsHelper.add_overrides(
                step.host_requirements,
                step_host_requirements_override,
            )

            # update step environments
            for env in step.environments:
                step_environment_override = next(
                    (
                        env_override
                        for env_override in step_override.environments_overrides
                        if env_override.name == env.name
                    ),
                    None,
                )
                if step_environment_override:
                    env.variables = step_environment_override.variables.variables

            # update step parameters
            for override_param in step_override.task_parameter_definitions.parameters:
                step.update_extra_parameter(
                    UnrealOpenJobStepParameterDefinition.from_unreal_param_definition(
                        override_param
                    )
                )

    def _update_environments_settings_from_mrq_job(
        self, mrq_job: unreal.MoviePipelineDeadlineCloudExecutorJob
    ):
        """
        Iterate through the Job's Environments and update variables map with overrides of given MRQ Job
        for each Environment.

        :param mrq_job: unreal.MoviePipelineDeadlineCloudExecutorJob instance
        :type mrq_job: unreal.MoviePipelineDeadlineCloudExecutorJob
        """

        for env in self._environments:
            override_environment = next(
                (
                    env_override
                    for env_override in mrq_job.job_template_overrides.environments_overrides
                    if env_override.name == env.name
                ),
                None,
            )
            if override_environment:
                env.variables = override_environment.variables.variables

    @staticmethod
    def _get_project_path_relative_to_workspace_root(workspace_root: str) -> str:
        workspace_root = workspace_root.replace("\\", "/")
        unreal_project_path = common.get_project_file_path().replace("\\", "/")
        if not unreal_project_path.lower().startswith(workspace_root.lower()):
            raise exceptions.ProjectIsNotUnderWorkspaceError(
                f"Project {unreal_project_path} is not under the workspace root: {workspace_root}"
            )

        pattern = re.compile(re.escape(workspace_root), re.IGNORECASE)

        unreal_project_relative_path = pattern.sub("", unreal_project_path, count=1).lstrip("/")
        if unreal_project_relative_path == unreal_project_path:
            raise RuntimeError(
                "Something went wrong during getting Unreal Project Path relative to "
                f"Perforce Workspace Root. Project path is {unreal_project_path}. "
                f"Workspace Root: {workspace_root}"
            )

        return unreal_project_relative_path

    def _build_parameter_values_for_ugs(self, parameter_values: list[dict]) -> list[dict]:
        """
        Build and return list of parameter values for the OpenJob in the Unreal Game Sync integration.

        Parameters to be updated:

        - Perforce Changelist Number
        - Perforce Stream Path
        - Unreal Project Name
        - Unreal Project Path relative to P4 workspace root
        - Unreal Executable Path relative to P4 workspace root

        .. note:: If expected parameter missed, it will be skipped

        :param parameter_values: list of parameter values to be updated
        :type parameter_values: list[dict]

        :return: list of updated parameter values
        :rtype: list[dict]
        """

        conn_settings = unreal_source_control.get_connection_settings_from_ue_source_control()
        p4_conn = perforce.PerforceConnection(
            port=conn_settings["port"],
            user=conn_settings["user"],
            client=conn_settings["workspace"],
        )

        parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
            job_parameter_values=parameter_values,
            job_parameter_name=OpenJobParameterNames.PERFORCE_STREAM_PATH,
            job_parameter_value=p4_conn.get_stream_path(),
        )

        parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
            job_parameter_values=parameter_values,
            job_parameter_name=OpenJobParameterNames.PERFORCE_CHANGELIST_NUMBER,
            job_parameter_value=str(p4_conn.get_latest_changelist_number() or "latest"),
        )

        parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
            job_parameter_values=parameter_values,
            job_parameter_name=OpenJobParameterNames.UNREAL_PROJECT_NAME,
            job_parameter_value=common.get_project_name(),
        )

        client_root = p4_conn.get_client_root()
        if isinstance(client_root, str):
            unreal_project_relative_path = self._get_project_path_relative_to_workspace_root(
                workspace_root=client_root,
            )

            parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
                job_parameter_values=parameter_values,
                job_parameter_name=OpenJobParameterNames.UNREAL_PROJECT_RELATIVE_PATH,
                job_parameter_value=unreal_project_relative_path,
            )

            unreal_executable_path = sys.executable.replace("\\", "/")
            unreal_executable_relative_path = unreal_executable_path.replace(client_root, "")
            unreal_executable_relative_path = unreal_executable_relative_path.lstrip("/")

            parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
                job_parameter_values=parameter_values,
                job_parameter_name=OpenJobParameterNames.UNREAL_EXECUTABLE_RELATIVE_PATH,
                job_parameter_value=unreal_executable_relative_path,
            )

        return parameter_values

    def _build_parameter_values_for_p4(self, parameter_values: list[dict]) -> list[dict]:
        """
        Build and return list of parameter values for the OpenJob in the Perforce integration.

        Parameters to be updated:

        - Perforce Changelist Number
        - Unreal Project Name
        - Unreal Project Path relative to P4 workspace root
        - Perforce Workspace Specification template
          (see :meth:`deadline.unreal_perforce_utils.perforce.get_perforce_workspace_specification_template()`)
        - Job Dependencies Descriptor
          (see :meth:`deadline.unreal_submitter.unreal_open_job.unreal_open_job.RenderUnrealOpenJob._get_mrq_job_dependency_depot_paths()`)

        .. note:: If expected parameter missed, it will be skipped

        :param parameter_values: list of parameter values to be updated
        :type parameter_values: list[dict]

        :return: list of updated parameter values
        :rtype: list[dict]
        """

        conn_settings = unreal_source_control.get_connection_settings_from_ue_source_control()
        p4 = perforce.PerforceConnection(
            port=conn_settings["port"],
            user=conn_settings["user"],
            client=conn_settings["workspace"],
        )

        latest_changelist_number = str(p4.get_latest_changelist_number() or "latest")
        parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
            job_parameter_values=parameter_values,
            job_parameter_name=OpenJobParameterNames.PERFORCE_CHANGELIST_NUMBER,
            job_parameter_value=latest_changelist_number,
        )

        parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
            job_parameter_values=parameter_values,
            job_parameter_name=OpenJobParameterNames.UNREAL_PROJECT_NAME,
            job_parameter_value=common.get_project_name(),
        )

        client_root = p4.get_client_root()
        if isinstance(client_root, str):
            unreal_project_relative_path = self._get_project_path_relative_to_workspace_root(
                workspace_root=client_root,
            )

            parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
                job_parameter_values=parameter_values,
                job_parameter_name=OpenJobParameterNames.UNREAL_PROJECT_RELATIVE_PATH,
                job_parameter_value=unreal_project_relative_path,
            )

        workspace_spec_template = common.create_deadline_cloud_temp_file(
            file_prefix=OpenJobParameterNames.PERFORCE_WORKSPACE_SPECIFICATION_TEMPLATE,
            file_data=perforce.get_perforce_workspace_specification_template(
                port=conn_settings["port"],
                user=conn_settings["user"],
                client=conn_settings["workspace"],
            ),
            file_ext=".json",
        )
        parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
            job_parameter_values=parameter_values,
            job_parameter_name=OpenJobParameterNames.PERFORCE_WORKSPACE_SPECIFICATION_TEMPLATE,
            job_parameter_value=workspace_spec_template,
        )
        self._asset_references.input_filenames.add(workspace_spec_template)

        # We need to collect job dependencies on the Artist node because some of them of
        # type "soft" and references to them in other downloaded assets will be None on the
        # Render node. So we can't sync them and their dependencies until we don't know their paths
        job_dependencies_descriptor = common.create_deadline_cloud_temp_file(
            file_prefix=OpenJobParameterNames.UNREAL_MRQ_JOB_DEPENDENCIES_DESCRIPTOR,
            file_data={
                "job_dependencies": self._get_mrq_job_dependency_depot_paths(
                    latest_changelist_number,
                )
            },
            file_ext=".json",
        )
        parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
            job_parameter_values=parameter_values,
            job_parameter_name=OpenJobParameterNames.UNREAL_MRQ_JOB_DEPENDENCIES_DESCRIPTOR,
            job_parameter_value=job_dependencies_descriptor,
        )
        self._asset_references.input_filenames.add(job_dependencies_descriptor)

        return parameter_values

    def _is_using_dynamic_chunking(self) -> bool:
        """
        Check if any step in this job uses dynamic chunking (CHUNK[INT] type).

        :return: True if any step uses dynamic chunking, False otherwise
        :rtype: bool
        """
        from deadline.unreal_submitter.unreal_open_job.unreal_open_job_dynamic_chunking import (
            DynamicChunkingHelper,
        )

        for step in self._steps:
            try:
                step_template_object = step.get_template_object()
                if DynamicChunkingHelper.is_using_dynamic_chunking(step_template_object):
                    return True
            except FileNotFoundError:
                # A step without a resolvable template file cannot declare
                # CHUNK[INT]; other exceptions propagate so real bugs surface.
                continue
        return False

    def _build_frames_parameter_value(self, parameter_values: list[dict]) -> list[dict]:
        """
        Build and return the Frames parameter value for dynamic chunking templates.

        Extracts the frame range from MRQ settings:
        - If custom playback range is enabled, uses custom_start_frame and custom_end_frame
        - Otherwise, uses the level sequence's playback range

        The frame range is formatted as "<start>-<end>" (e.g., "0-99" for 100 frames).

        :param parameter_values: list of parameter values to be updated
        :type parameter_values: list[dict]

        :return: list of updated parameter values
        :rtype: list[dict]
        """
        # Check if Frames parameter exists in the parameter values (indicates dynamic chunking)
        frames_param = next(
            (p for p in parameter_values if p["name"] == OpenJobParameterNames.FRAMES), None
        )
        if not frames_param:
            return parameter_values

        # Skip if Frames already has a value
        if frames_param.get("value") is not None:
            return parameter_values

        # Need MRQ job to extract frame range
        if not self._mrq_job:
            raise exceptions.SubmitterInputValidationError(
                "Cannot populate Frames parameter: MRQ job is not set. "
                "Dynamic chunking requires frame range from MRQ settings."
            )

        # Load output settings and level sequence from MRQ job
        output_settings = self._mrq_job.get_configuration().find_setting_by_class(
            unreal.MoviePipelineOutputSetting
        )
        level_sequence = unreal.EditorAssetLibrary.load_asset(
            unreal.SystemLibrary.conv_soft_object_reference_to_string(
                unreal.SystemLibrary.conv_soft_obj_path_to_soft_obj_ref(self._mrq_job.sequence)
            )
        )

        if not level_sequence:
            raise exceptions.SubmitterInputValidationError(
                "Cannot populate Frames parameter: Level sequence could not be loaded. "
                "Dynamic chunking requires frame range from a valid MRQ level sequence."
            )

        # Extract frame range from MRQ settings
        if output_settings and output_settings.use_custom_playback_range:
            start_frame = output_settings.custom_start_frame
            end_frame = output_settings.custom_end_frame
            logger.info(
                f"Using custom playback range for Frames parameter: {start_frame}-{end_frame}"
            )
        else:
            start_frame = level_sequence.get_playback_range().get_start_frame()
            end_frame = level_sequence.get_playback_range().get_end_frame()
            logger.info(
                f"Using level sequence playback range for Frames parameter: {start_frame}-{end_frame}"
            )

        # Format as "<start>-<end>" for OpenJD IntRangeExpr. MRQ end frames
        # (custom_end_frame / playback range end) are EXCLUSIVE, while OpenJD
        # integer range expressions are INCLUSIVE on both ends ("10-20" is 11
        # frames) - subtract 1 so the last chunk doesn't render a frame past
        # the end of the sequence.
        inclusive_end_frame = end_frame - 1
        if inclusive_end_frame < start_frame:
            raise exceptions.SubmitterInputValidationError(
                "Cannot populate Frames parameter from an empty or descending MRQ frame range: "
                f"[{start_frame}, {end_frame})."
            )

        frames_value = f"{start_frame}-{inclusive_end_frame}"

        parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
            job_parameter_values=parameter_values,
            job_parameter_name=OpenJobParameterNames.FRAMES,
            job_parameter_value=frames_value,
        )

        return parameter_values

    def _build_parameter_values(self) -> list:
        """
        Build and return list of parameter values for the OpenJob. Use YAML parameter names and
        extra parameter values/ YAML defaults if exists.

        Fill parameters that were not filled by user on in YAML. Typically, this parameters
        should not be filled by user (such as Project Path, Extra Cmd Args File, UGS settings, etc.)

        Parameters to be updated:

        - Unreal Extra Cmd Arguments (set to "")
        - Unreal Extra Cmd Arguments File (write all the arguments to file to avoid OpenJD limitation of 1024 chars)
        - Unreal Project Path (local path to the project)
        - Parameters for UGS if UGS is used
          (see :meth:`deadline.unreal_submitter.unreal_open_job.unreal_open_job.RenderUnrealOpenJob._build_parameter_values_for_ugs()`)
        - Parameters for P4 if P4 is used
          (see :meth:`deadline.unreal_submitter.unreal_open_job.unreal_open_job.RenderUnrealOpenJob._build_parameter_values_for_p4()`)
        - Frames parameter for dynamic chunking templates
          (see :meth:`deadline.unreal_submitter.unreal_open_job.unreal_open_job.RenderUnrealOpenJob._build_frames_parameter_value()`)

        .. note:: If expected parameter missed, it will be skipped

        .. note:: Set ExtraCmdArgs parameter as empty string "" since Adaptor read args only from file.

        :return: list of parameter values
        :rtype: list[dict[str, Any]]
        """

        parameter_values = super()._build_parameter_values()

        # skip params with filled values (in YAML or by User in UI)
        # if it is not ExtraCmdArgs since we want to update them with mrq job args
        unfilled_parameter_values = [
            p
            for p in parameter_values
            if p["value"] is None
            or p["name"] == OpenJobParameterNames.UNREAL_EXTRA_CMD_ARGS
            or p["name"] == OpenJobParameterNames.UNREAL_EXTRA_CMD_ARGS_FILE
        ]
        filled_parameter_values = [
            p for p in parameter_values if p not in unfilled_parameter_values
        ]

        # Unreal Engine can handle long CMD args strings and OpenJD has a limit of 1024 chars.
        # Therefore, we need to write them to file and set ExtraCmdArgs parameter as empty string.
        # Unreal Adaptor uses only ExtraCmdArgsFile parameter to read args from file.
        extra_cmd_args_file_value = None
        for p in parameter_values:
            if p["name"] == OpenJobParameterNames.UNREAL_EXTRA_CMD_ARGS_FILE:
                extra_cmd_args_file_value = p["value"]
                break

        # Read EXTRA_CMD_ARGS_FILE file value if file exists, and append its content to user_extra_cmd_args
        args_from_file = None
        if extra_cmd_args_file_value:
            args_from_file = self.get_user_extra_cmd_args_from_file(str(extra_cmd_args_file_value))
        user_extra_cmd_args = self.get_user_extra_cmd_args()

        if args_from_file:
            user_extra_cmd_args = merge_cmd_args_with_priority(user_extra_cmd_args, args_from_file)
        executor_cmd_args = self.get_executor_cmd_args()
        profiling_cmd_args = self.get_profiling_cmd_args()

        merged_cmd_args = merge_cmd_args_with_priority(user_extra_cmd_args, executor_cmd_args)
        if profiling_cmd_args:
            merged_cmd_args = merge_cmd_args_with_priority(merged_cmd_args, profiling_cmd_args)
        merged_cmd_args = self.clear_cmd_args(merged_cmd_args)

        unfilled_parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
            job_parameter_values=unfilled_parameter_values,
            job_parameter_name=OpenJobParameterNames.UNREAL_EXTRA_CMD_ARGS,
            job_parameter_value="",
        )
        # Write the .txt file using the original temp file logic
        extra_cmd_args_file = common.create_deadline_cloud_temp_file(
            file_prefix=OpenJobParameterNames.UNREAL_EXTRA_CMD_ARGS_FILE,
            file_data=merged_cmd_args,
            file_ext=".txt",
        )

        unfilled_parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
            job_parameter_values=unfilled_parameter_values,
            job_parameter_name=OpenJobParameterNames.UNREAL_EXTRA_CMD_ARGS_FILE,
            job_parameter_value=extra_cmd_args_file,
        )
        self._asset_references.input_filenames.add(extra_cmd_args_file)

        unfilled_parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
            job_parameter_values=unfilled_parameter_values,
            job_parameter_name=OpenJobParameterNames.UNREAL_PROJECT_PATH,
            job_parameter_value=common.get_project_file_path(),
        )

        # Set the Marketplace plugins dir so the worker can find and install them
        marketplace_dir = UnrealOpenJob.get_marketplace_plugins_dir()
        unfilled_parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
            job_parameter_values=unfilled_parameter_values,
            job_parameter_name=OpenJobParameterNames.MARKETPLACE_PLUGINS_DIR,
            job_parameter_value=marketplace_dir,
        )

        if self._transfer_files_strategy == TransferProjectFilesStrategy.UGS:
            unfilled_parameter_values = self._build_parameter_values_for_ugs(
                parameter_values=unfilled_parameter_values
            )

        if self._transfer_files_strategy == TransferProjectFilesStrategy.P4:
            unfilled_parameter_values = self._build_parameter_values_for_p4(
                parameter_values=unfilled_parameter_values
            )

        # Populate Frames parameter for dynamic chunking templates
        if self._is_using_dynamic_chunking():
            unfilled_parameter_values = self._build_frames_parameter_value(
                parameter_values=unfilled_parameter_values
            )

        all_parameter_values = filled_parameter_values + unfilled_parameter_values
        return all_parameter_values

    def get_executor_cmd_args(self) -> str:
        """
        Returns the cleaned list of command line arguments from the executor settings and MRQ job.
        """

        cmd_args = common.get_in_process_executor_cmd_args()
        if self._mrq_job:
            cmd_args.extend(common.get_mrq_job_cmd_args(self._mrq_job))

        return " ".join(a for a in cmd_args)

    def get_profiling_cmd_args(self) -> str:
        return self.profiling_settings.build_cmd_args()

    def get_user_extra_cmd_args(self) -> str:
        """
        Returns the cleaned list of user-specified extra command line arguments (UNREAL_EXTRA_CMD_ARGS),
        with any -execcmds arguments removed.
        """

        extra_cmd_args_param = self._find_extra_parameter(
            parameter_name=OpenJobParameterNames.UNREAL_EXTRA_CMD_ARGS,
            parameter_type="STRING",
        )
        if extra_cmd_args_param and extra_cmd_args_param.value:
            extra_cmd_args = str(extra_cmd_args_param.value)
            return extra_cmd_args

        return ""

    @staticmethod
    def clear_cmd_args(cmd_args: str) -> str:
        """
        Cleans the command line arguments by removing any -execcmds arguments.
        This is useful to ensure that no unintended execution commands are passed.

        :param cmd_args: The command line arguments as a string.
        :return: Cleaned command line arguments.
        """
        cleared_cmd_args = re.sub(
            pattern='(-execcmds="[^"]*")', repl="", string=cmd_args, flags=re.IGNORECASE
        )
        cleared_cmd_args = re.sub(
            pattern="(-execcmds='[^']*')",
            repl="",
            string=cleared_cmd_args,
            flags=re.IGNORECASE,
        )

        if cleared_cmd_args != cmd_args:
            logger.warning(
                "Appearance of custom '-execcmds' argument on the Render node can cause unpredictable "
                "issues. Argument '-execcmds' of Unreal Open Job's "
                "Extra Command Line arguments will be ignored."
            )

        return cleared_cmd_args

    def get_user_extra_cmd_args_from_file(self, file_path: str) -> str:
        """
        Reads the given EXTRA_CMD_ARGS_FILE and returns the string as-is (stripped).
        Returns an empty string if the file is missing or empty. Logs if file is empty or error reading.
        """

        if not file_path or not os.path.isfile(file_path):
            logger.info(f"EXTRA_CMD_ARGS_FILE '{file_path}' does not exist or is not specified.")
            return ""
        try:
            with open(file_path, "r", encoding="utf8") as f:
                extra_data = f.read()
            if not extra_data.strip():
                logger.info(f"EXTRA_CMD_ARGS_FILE '{file_path}' is empty.")
                return ""
            return extra_data.strip()
        except Exception as e:
            logger.error(f"Error reading EXTRA_CMD_ARGS_FILE '{file_path}': {e}")
            return ""

    def _collect_mrq_job_dependencies(self) -> list[str]:
        """
        Collects the dependencies of the Level and LevelSequence that used in MRQ Job.

        Use :class:`deadline.unreal_submitter.unreal_dependency_collector.collector.DependencyCollector` for collecting

        :return: List of the dependencies
        :rtype: list[str]
        """
        if not self._mrq_job:
            raise exceptions.MrqJobIsMissingError("MRQ Job must be provided")

        level_sequence_path = common.soft_obj_path_to_str(self._mrq_job.sequence)
        level_sequence_path = os.path.splitext(level_sequence_path)[0]

        level_path = common.soft_obj_path_to_str(self._mrq_job.map)
        level_path = os.path.splitext(level_path)[0]

        level_sequence_dependencies = self._dependency_collector.collect(
            level_sequence_path, filter_method=DependencyFilters.dependency_in_game_folder
        )

        level_dependencies = self._dependency_collector.collect(
            level_path, filter_method=DependencyFilters.dependency_in_game_folder
        )

        all_dependencies = (
            level_sequence_dependencies + level_dependencies + [level_sequence_path, level_path]
        )
        unique_dependencies = list(set(all_dependencies))

        return unique_dependencies

    def _get_mrq_job_dependency_paths(self):
        """
        Collects the dependencies of the Level and LevelSequence that used in MRQ Job and
        returns paths converted from UE relative (i.e. /Game/...) to OS absolute (D:/...)

        :return: List of the dependencies
        :rtype: list[str]
        """

        os_dependencies = []

        job_dependencies = self._collect_mrq_job_dependencies()
        for dependency in job_dependencies:
            os_dependency = common.os_path_from_unreal_path(dependency, with_ext=True)
            if os.path.exists(os_dependency):
                os_dependencies.append(os_dependency)

        return os_dependencies

    def _get_mrq_job_dependency_depot_paths(
        self, changelist_number: Optional[str] = None
    ) -> list[str]:
        """
        Collects the dependencies if Level and LevelSequence of MRQ Job and returns paths
        converted from UE relative (i.e. /Game/...) to Perforce Depot (//MyProject/Mainline/...).
        Using depot file paths allow to sync in any locations other than User's ones.

        If `changelist_number` is provided, append it to the end of each path with
        "@" prefix, i.e. //MyProject/Mainline/Assets/MyAsset.uasset@12345

        :param changelist_number: Perforce changelist number
        :type changelist_number: Optional[str]
        :return: List of the dependency depot paths
        :rtype: list[str]
        """

        local_dependencies = self._get_mrq_job_dependency_paths()

        conn_settings = unreal_source_control.get_connection_settings_from_ue_source_control()
        p4_conn = perforce.PerforceConnection(
            port=conn_settings["port"],
            user=conn_settings["user"],
            client=conn_settings["workspace"],
        )
        depot_dependencies = p4_conn.get_depot_file_paths(local_dependencies)

        if changelist_number and changelist_number != "latest":
            depot_dependencies = [f"{path}@{changelist_number}" for path in depot_dependencies]

        return depot_dependencies

    def _get_mrq_job_attachments_input_files(self) -> list[str]:
        """
        Get Job Attachments Input Files from MRQ Job preset overrides

        :return: List of MRQ Job Attachments Input Files
        :rtype: list[str]
        """

        input_files = []

        job_input_files = self.mrq_job.preset_overrides.job_attachments.input_files.files.paths
        for job_input_file in job_input_files:
            input_file = common.os_abs_from_relative(job_input_file.file_path)
            if os.path.exists(input_file):
                input_files.append(input_file)

        return input_files

    def _get_mrq_job_attachments_input_directories(self) -> list[str]:
        """
        Get Job Attachments Input Directories from MRQ Job preset overrides

        :return: List of MRQ Job Attachments Input Directories
        :rtype: list[str]
        """

        input_directories = []

        job_input_directories = (
            self.mrq_job.preset_overrides.job_attachments.input_directories.directories.paths
        )
        for job_input_dir in job_input_directories:
            input_dir = common.os_abs_from_relative(job_input_dir.path)
            if os.path.exists(input_dir):
                input_directories.append(input_dir)

        return input_directories

    def _get_mrq_job_attachments_output_directories(self) -> list[str]:
        """
        Get Job Attachments Output Directories from MRQ Job preset overrides

        :return: List of MRQ Job Attachments Output Directories
        :rtype: list[str]
        """

        output_directories = []

        job_output_directories = (
            self.mrq_job.preset_overrides.job_attachments.output_directories.directories.paths
        )
        for job_output_dir in job_output_directories:
            output_dir = common.os_abs_from_relative(job_output_dir.path)
            if os.path.exists(output_dir):
                output_directories.append(output_dir)

        return output_directories

    def _get_profiling_output_directories(self) -> list[str]:
        if not self.profiling_settings.is_enabled():
            return []

        profiling_directory = unreal.Paths.convert_relative_path_to_full(
            unreal.Paths.profiling_dir()
        )
        return self.profiling_settings.get_output_directories(profiling_directory)

    def _get_mrq_job_output_directory(self) -> str:
        """
        Get the output directory path from  MRQ Job Configuration, resolve all possible tokens
        (e.g. job_name, level, map, etc.) and return resulted path.

        :return: MRQ Job Configuration's resolved Output Directory
        :rtype: str
        """

        output_setting = self.mrq_job.get_configuration().find_setting_by_class(
            unreal.MoviePipelineOutputSetting
        )
        output_path = output_setting.output_directory.path
        common.validate_path_does_not_contain_non_valid_chars(output_path)

        path_context = common.get_path_context_from_mrq_job(self.mrq_job)
        output_path = output_path.format_map(path_context).rstrip("/")

        return output_path

    def get_asset_references(self) -> AssetReferences:
        """
        Build asset references of the OpenJob with the given MRQ Job.

        Return :class:`deadline.client.job_bundle.submission.AssetReferences` instance

        :return: AssetReferences dataclass instance
        :rtype: :class:`deadline.client.job_bundle.submission.AssetReferences`
        """

        asset_references = super().get_asset_references()

        if self._transfer_files_strategy == TransferProjectFilesStrategy.S3:
            # add dependencies to attachments
            asset_references.input_filenames.update(self._get_mrq_job_dependency_paths())

            # required input directories
            asset_references.input_directories.update(
                RenderUnrealOpenJob.get_required_project_directories()
            )
            plugins = UnrealOpenJob.get_plugins_references()
            if plugins:
                asset_references.input_directories.update(plugins.input_directories)

        # add attachments from preset overrides
        if self.mrq_job:
            # input files
            asset_references.input_filenames.update(self._get_mrq_job_attachments_input_files())

            # input directories
            asset_references.input_directories.update(
                self._get_mrq_job_attachments_input_directories()
            )

            # output directories
            asset_references.output_directories.update(
                self._get_mrq_job_attachments_output_directories()
            )

            # Render output path
            asset_references.output_directories.add(self._get_mrq_job_output_directory())

        profiling_output_directories = set(self._get_profiling_output_directories())
        asset_references.output_directories.update(profiling_output_directories)

        # When SubmitMode is set on a Perforce job template, render outputs are
        # delivered to Perforce and MUST NOT be re-uploaded to S3 as Job
        # Attachments. But we can't just drop the output paths: OpenJD derives
        # path-mapping rules from them so the worker knows to remap the
        # submitter-side output path (e.g. C:/Users/Administrator/Perforce/...)
        # to its local session/workspace path. Move them to referenced_paths
        # instead, which participates in path-mapping without triggering the
        # post-task S3 output upload.
        #
        # Gate on the SubmitMode parameter existing + being non-empty so non-P4
        # templates (which don't declare SubmitMode) are unaffected.
        if self._submit_mode_active():
            render_output_directories = (
                asset_references.output_directories - profiling_output_directories
            )
            asset_references.referenced_paths.update(render_output_directories)
            asset_references.output_directories.difference_update(render_output_directories)

        return asset_references

    def _submit_mode_active(self) -> bool:
        """
        True if the SubmitMode parameter is set to a non-empty value ('submit'
        or 'shelve'). Only Perforce render templates declare this parameter;
        other templates return False.
        """
        param = self._find_extra_parameter("SubmitMode", "STRING")
        if param is None:
            return False
        return bool(param.value) and param.value != ""

    def _has_assemble_shelves_step(self) -> bool:
        return any(isinstance(s, P4AssembleShelvesUnrealOpenJobStep) for s in self._steps)

    def _ensure_assemble_shelves_step(self) -> None:
        """
        Add the AssembleShelves step to the job when SubmitMode is set.
        Idempotent — re-runs of _build_template won't stack duplicates.

        Every render task shelves its own CL; AssembleShelves runs once
        after all Render tasks and merges them into one final CL.
        """
        param = self._find_extra_parameter("SubmitMode", "STRING")
        active = self._submit_mode_active()
        has_step = self._has_assemble_shelves_step()
        logger.info(
            "RenderUnrealOpenJob._ensure_assemble_shelves_step: "
            "class=%s, SubmitMode param exists=%s, value=%r, active=%s, "
            "has_step=%s, steps_before=%s",
            type(self).__name__,
            param is not None,
            getattr(param, "value", None),
            active,
            has_step,
            [type(s).__name__ for s in self._steps],
        )
        if not active:
            return
        if has_step:
            return
        self._steps.append(P4AssembleShelvesUnrealOpenJobStep())
        logger.info(
            "RenderUnrealOpenJob._ensure_assemble_shelves_step: "
            "appended AssembleShelves step; steps_after=%s",
            [type(s).__name__ for s in self._steps],
        )

    def _build_template(self) -> JobTemplate:
        # Inject AssembleShelves before the base builds the template so it
        # ends up in the emitted `steps` list.
        logger.info(
            "RenderUnrealOpenJob._build_template called; class=%s",
            type(self).__name__,
        )
        self._ensure_assemble_shelves_step()
        return super()._build_template()


# UGS Jobs
class UgsRenderUnrealOpenJob(RenderUnrealOpenJob):
    """Class for predefined UGS Render Job"""

    default_template_path = settings.UGS_RENDER_JOB_TEMPLATE_DEFAULT_PATH


# Perforce (non UGS) Jobs
class P4RenderUnrealOpenJob(RenderUnrealOpenJob):
    """Class for predefined Perforce Render Job.

    The MRQ submit UI actually instantiates the parent RenderUnrealOpenJob and
    picks the template from the data asset, so the SubmitMode-driven behavior
    (AssembleShelves injection + JA output skip) lives on the parent. This
    subclass exists for the programmatic submission path (see
    submit_actions/p4_render_job_submission.py), which constructs a P4 job
    explicitly and relies on default_template_path.
    """

    default_template_path = settings.P4_RENDER_JOB_TEMPLATE_DEFAULT_PATH
