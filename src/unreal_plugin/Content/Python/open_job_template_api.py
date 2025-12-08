# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import yaml
import unreal
from typing import Any

from deadline.unreal_submitter.unreal_open_job.unreal_open_job import (
    UnrealOpenJobParameterDefinition,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step import (
    UnrealOpenJobStepParameterDefinition,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_parameters_consistency import (
    ParametersConsistencyChecker,
    ParametersConsistencyCheckResult,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step_host_requirements import (
    DEFAULT_HOST_REQUIREMENTS,
)


@unreal.uclass()
class PythonYamlLibraryImplementation(unreal.PythonYamlLibrary):
    """
    Implementation of the C++ PythonYamlLibrary for working with YAML template files.
    Do real execution of calls from C++
    """

    @staticmethod
    def job_parameter_to_u_parameter_definition(
        job_parameter: dict[str, Any],
    ) -> unreal.ParameterDefinition:
        """
        Convert given Job Parameter definition dictionary to unreal.ParameterDefinition.

        :param job_parameter: Job Parameter definition dictionary.
        :type job_parameter: dict[str, Any]

        :return: unreal.ParameterDefinition
        """
        u_parameter_definition = unreal.ParameterDefinition()
        u_parameter_definition.name = job_parameter["name"]
        u_parameter_definition.type = getattr(unreal.ValueType, job_parameter["type"])

        if job_parameter.get("value") is not None:
            u_parameter_definition.value = str(job_parameter["value"])

        elif job_parameter.get("default") is not None:
            u_parameter_definition.value = str(job_parameter["default"])

        # Map userInterface.control to UserInterfaceControl enum
        if "userInterface" in job_parameter and "control" in job_parameter["userInterface"]:
            control_value = job_parameter["userInterface"]["control"]
            # Map YAML control values to Unreal enum values
            control_mapping = {
                "LINE_EDIT": unreal.UserInterfaceControl.LINE_EDIT,
                "MULTILINE_EDIT": unreal.UserInterfaceControl.MULTILINE_EDIT,
                "DROPDOWN_LIST": unreal.UserInterfaceControl.DROPDOWN_LIST,
                "CHECK_BOX": unreal.UserInterfaceControl.CHECK_BOX,
                "HIDDEN": unreal.UserInterfaceControl.HIDDEN,
                "CHOOSE_INPUT_FILE": unreal.UserInterfaceControl.CHOOSE_INPUT_FILE,
                "CHOOSE_OUTPUT_FILE": unreal.UserInterfaceControl.CHOOSE_OUTPUT_FILE,
                "CHOOSE_DIRECTORY": unreal.UserInterfaceControl.CHOOSE_DIRECTORY,
                "SPIN_BOX": unreal.UserInterfaceControl.SPIN_BOX,
            }
            if control_value in control_mapping:
                u_parameter_definition.user_interface_control = control_mapping[control_value]
            else:
                # Default to LINE_EDIT if unknown control type
                u_parameter_definition.user_interface_control = (
                    unreal.UserInterfaceControl.LINE_EDIT
                )

        return u_parameter_definition

    @staticmethod
    def step_parameter_to_u_step_task_parameter(
        step_parameter: dict[str, str],
    ) -> unreal.StepTaskParameterDefinition:
        """
        Convert given Step Parameter definition dictionary to unreal.StepTaskParameterDefinition.

        :param step_parameter: Step Parameter definition dictionary.
        :type step_parameter: dict[str, Any]

        :return: unreal.StepTaskParameterDefinition
        """
        u_step_task_parameter_definition = unreal.StepTaskParameterDefinition()
        u_step_task_parameter_definition.name = step_parameter["name"]
        u_step_task_parameter_definition.type = getattr(unreal.ValueType, step_parameter["type"])
        u_step_task_parameter_definition.range = [str(v) for v in step_parameter.get("range", [])]

        return u_step_task_parameter_definition

    @staticmethod
    def environment_to_u_environment(environment: dict[str, Any]) -> unreal.EnvironmentStruct:
        """
        Convert given Environment dictionary to unreal.EnvironmentStruct.
        Use only name, descriptions and variables

        :param environment: Environment dictionary.
        :type environment: dict[str, Any]

        :return: unreal.EnvironmentStruct
        """
        u_environment = unreal.EnvironmentStruct()
        u_environment.name = environment["name"]
        u_environment.description = environment.get("description", "")

        u_variables: list[unreal.EnvVariable] = []
        for k, v in environment.get("variables", {}).items():
            u_variable = unreal.EnvVariable()
            u_variable.name = k
            u_variable.value = v

            u_variables.append(u_variable.copy())

        u_environment.variables = u_variables

        return u_environment

    @unreal.ufunction(override=True)
    def open_job_file(self, path: str) -> list[unreal.ParameterDefinition]:
        """
        Open given job template file and build the list of unreal.ParameterDefinition from its data

        :param path: Path to the job template file.
        :type path: str

        :return: list of unreal.ParameterDefinition
        """
        with open(path, "r") as f:
            job_template = yaml.safe_load(f)

        u_parameter_definitions: list[unreal.ParameterDefinition] = []

        for parameter_definition in job_template["parameterDefinitions"]:
            u_param = PythonYamlLibraryImplementation.job_parameter_to_u_parameter_definition(
                parameter_definition
            )
            u_parameter_definitions.append(u_param.copy())

        return u_parameter_definitions

    @staticmethod
    def _load_yaml(path: str) -> dict:
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}
        return data

    @staticmethod
    def _get_host_reqs_section(doc: dict) -> dict:
        if not isinstance(doc, dict) or "hostRequirements" not in doc:
            return {}
        section = doc["hostRequirements"] or {}
        return section

    @staticmethod
    def _is_blank(v: Any) -> bool:
        """
        Check if a value should be treated as an "open" bound (unset).
        Blank means None or an empty string.
        """
        return v is None or v == ""

    @staticmethod
    def _set_bound(bound, value: Any) -> None:
        """
        Apply a bound to a DeadlineCloud amount requirement.

        - If value is blank (None or ""), the bound becomes OPEN (no limit).
        - Otherwise, the bound is INCLUSIVE and stores the given numeric value.

        :param bound: The Unreal bound object (lower_bound or upper_bound).
        :param value: The value to apply (may be None).
        """
        if PythonYamlLibraryImplementation._is_blank(value):
            bound.type = unreal.RangeBoundTypes.OPEN
            bound.value = 0
        else:
            bound.type = unreal.RangeBoundTypes.INCLUSIVE
            bound.value = value

    @staticmethod
    def _new_amount_req() -> unreal.DeadlineCloudAmountRequirement:
        """
        Create a new Unreal DeadlineCloudAmountRequirement instance
        with its internal amount_requirement property initialized.
        """
        u = unreal.DeadlineCloudAmountRequirement()
        u.amount_requirement = u.get_editor_property("amount_requirement")
        return u

    @staticmethod
    def _apply_bounds(
        u_amount_req: unreal.DeadlineCloudAmountRequirement, min_val, max_val
    ) -> None:
        """
        Apply lower/upper bounds using inclusive or open semantics.

        :param u_amount_req: Unreal amount requirement instance to update.
        :param min_val: Minimum value or None for open bound.
        :param max_val: Maximum value or None for open bound.
        """
        PythonYamlLibraryImplementation._set_bound(
            u_amount_req.amount_requirement.lower_bound, min_val
        )
        PythonYamlLibraryImplementation._set_bound(
            u_amount_req.amount_requirement.upper_bound, max_val
        )

    @staticmethod
    def _to_str_list(values) -> list[str]:
        """
        Normalize input list to a list of strings.

        :param values: Value list or None.
        :return: List[str]
        """
        return [str(x) for x in (values or [])]

    @staticmethod
    def _copy_map(m: dict) -> dict:
        """
        Shallow copy map values, copying Unreal objects when possible.

        :param m: Original map.
        :return: New map with copied values.
        """
        out = {}
        for k, v in (m or {}).items():
            out[k] = v.copy() if hasattr(v, "copy") else v
        return out

    @staticmethod
    def _build_default_amounts() -> dict[str, unreal.DeadlineCloudAmountRequirement]:
        """
        Build the default amount requirements from DEFAULT_HOST_REQUIREMENTS.

        :return: dict[str, unreal.DeadlineCloudAmountRequirement]
        """
        result = {}
        for item in DEFAULT_HOST_REQUIREMENTS.get("amounts", []):
            u = PythonYamlLibraryImplementation._new_amount_req()
            PythonYamlLibraryImplementation._apply_bounds(u, item.get("min"), item.get("max"))
            result[item["name"]] = u.copy()
        return result

    @staticmethod
    def _build_default_attributes() -> dict[str, unreal.DeadlineCloudAttributeRequirements]:
        """
        Build the default attribute requirements from DEFAULT_HOST_REQUIREMENTS.

        :return: dict[str, unreal.DeadlineCloudAttributeRequirements]
        """
        result = {}
        for item in DEFAULT_HOST_REQUIREMENTS.get("attributes", []):
            u = unreal.DeadlineCloudAttributeRequirements()
            any_of = PythonYamlLibraryImplementation._to_str_list(item.get("anyOf"))
            all_of = PythonYamlLibraryImplementation._to_str_list(item.get("allOf"))
            if any_of:
                u.any_of = any_of
            if all_of:
                u.all_of = all_of
            result[item["name"]] = u.copy()
        return result

    @staticmethod
    def _merge_amounts_from_yaml_into_defaults(
        defaults: dict[str, unreal.DeadlineCloudAmountRequirement],
        amounts_data: list[dict],
    ) -> dict[str, unreal.DeadlineCloudAmountRequirement]:
        """
        Merge amount requirements from YAML over default ones.

        Conditions:
        - Known names: update bounds only if YAML provides min/max and they validate:
          min >= 0 (if provided), max >= 1 (if provided).
        - New names: allowed if at least one of min/max is present and valid.
        - Missing bound keeps the current/default value.

        :param defaults: Default amount map.
        :param amounts_data: List of YAML amount entries.
        :return: Updated amounts map.
        """
        result = PythonYamlLibraryImplementation._copy_map(defaults)
        if not amounts_data:
            return result

        for item in amounts_data:
            name = item.get("name")
            if not name:
                continue

            raw_min = item.get("min")
            raw_max = item.get("max")

            if not (raw_min is not None and raw_min >= 0) and not (
                raw_max is not None and raw_max >= 1
            ):
                continue

            if name in result:
                # Known amount: update both bounds atomically if validation passed
                u = result[name]

                final_min = raw_min
                final_max = raw_max

                # Apply both bounds (atomic update):
                PythonYamlLibraryImplementation._apply_bounds(u, final_min, final_max)

                result[name] = u.copy()
            else:
                # New amount: also apply bounds atomically
                u = PythonYamlLibraryImplementation._new_amount_req()
                PythonYamlLibraryImplementation._apply_bounds(u, raw_min, raw_max)
                result[name] = u.copy()

        return result

    @staticmethod
    def _merge_attributes_from_yaml_into_defaults(
        defaults: dict[str, unreal.DeadlineCloudAttributeRequirements],
        attributes_data: list[dict],
    ) -> dict[str, unreal.DeadlineCloudAttributeRequirements]:
        """
        Merge attribute requirements from YAML over default ones.

        - Known names: anyOf/allOf are replaced, but only values present in the default
          lists are kept (filtered per-list).
        - New names: added without filtering.

        :param defaults: Default attributes map.
        :param attributes_data: List of YAML attribute entries.
        :return: Updated attributes map.
        """
        result = PythonYamlLibraryImplementation._copy_map(defaults)
        if not attributes_data:
            return result

        for item in attributes_data:
            name = item.get("name")
            if not name:
                continue

            if name in result:
                def_attr = result[name]
                allowed_any = set(def_attr.any_of)
                allowed_all = set(def_attr.all_of)

                new_attr = unreal.DeadlineCloudAttributeRequirements()
                if "anyOf" in item:
                    yaml_any = PythonYamlLibraryImplementation._to_str_list(item.get("anyOf"))
                    new_attr.any_of = [v for v in yaml_any if v in allowed_any]
                else:
                    new_attr.any_of = def_attr.any_of

                if "allOf" in item:
                    yaml_all = PythonYamlLibraryImplementation._to_str_list(item.get("allOf"))
                    new_attr.all_of = [v for v in yaml_all if v in allowed_all]
                else:
                    new_attr.all_of = def_attr.all_of

                result[name] = new_attr.copy()
            else:
                new_attr = unreal.DeadlineCloudAttributeRequirements()
                if "anyOf" in item:
                    new_attr.any_of = PythonYamlLibraryImplementation._to_str_list(
                        item.get("anyOf")
                    )
                if "allOf" in item:
                    new_attr.all_of = PythonYamlLibraryImplementation._to_str_list(
                        item.get("allOf")
                    )
                result[name] = new_attr.copy()

        return result

    @unreal.ufunction(override=True)
    def open_host_requirements_file(self, path: str) -> unreal.DeadlineCloudHostRequirement:
        """
        Open given host requirements YAML file and construct a DeadlineCloudHostRequirement.

        Steps:
            1. Load base defaults from DEFAULT_HOST_REQUIREMENTS.
            2. Overlay YAML values with validation rules:
               - Amounts: range rules and allow new names.
               - Attributes: filtering only applies to known names; new names allowed.

        :param path: Path to the host requirements YAML file.
        :type path: str

        :return: Constructed Unreal DeadlineCloudHostRequirement instance.
        :rtype: unreal.DeadlineCloudHostRequirement
        """
        doc = self._load_yaml(path)
        host_reqs_yaml = self._get_host_reqs_section(doc)

        u_host_reqs = unreal.DeadlineCloudHostRequirement()

        default_amounts = self._build_default_amounts()
        default_attrs = self._build_default_attributes()

        u_host_reqs.amounts = default_amounts
        u_host_reqs.attributes = default_attrs

        if host_reqs_yaml:
            u_host_reqs.amounts = self._merge_amounts_from_yaml_into_defaults(
                default_amounts, host_reqs_yaml.get("amounts", [])
            )
            u_host_reqs.attributes = self._merge_attributes_from_yaml_into_defaults(
                default_attrs, host_reqs_yaml.get("attributes", [])
            )

        return u_host_reqs

    @unreal.ufunction(override=True)
    def open_step_file(self, path: str) -> unreal.StepStruct:
        """
        Open given step template file and build the unreal.StepStruct from its data

        :param path: Path to the step template file.
        :type path: str

        :return: unreal.StepStruct
        """

        with open(path, "r") as f:
            step_template = yaml.safe_load(f)

        u_step_task_parameter_definitions: list[unreal.StepTaskParameterDefinition] = []

        for param_definition in step_template["parameterSpace"]["taskParameterDefinitions"]:
            u_param = PythonYamlLibraryImplementation.step_parameter_to_u_step_task_parameter(
                param_definition
            )
            u_step_task_parameter_definitions.append(u_param.copy())

        u_step_struct = unreal.StepStruct()
        u_step_struct.name = step_template["name"]
        u_step_struct.parameters = u_step_task_parameter_definitions

        return u_step_struct

    @unreal.ufunction(override=True)
    def open_env_file(self, path: str) -> unreal.EnvironmentStruct:
        """
        Open given environment template file and build the unreal.EnvironmentStruct from its data

        :param path: Path to the environment template file.
        :type path: str

        :return: unreal.EnvironmentStruct
        """

        with open(path, "r") as f:
            environment_template = yaml.safe_load(f)

        u_environment = PythonYamlLibraryImplementation.environment_to_u_environment(
            environment_template
        )

        return u_environment


@unreal.uclass()
class ParametersConsistencyCheckerImplementation(unreal.PythonParametersConsistencyChecker):
    """
    Implementation of the C++ PythonParametersConsistencyChecker
    for checking/fixing parameters consistency.
    Do real execution of calls from C++
    """

    @staticmethod
    def check_result_to_u_check_result(
        consistency_check_result: ParametersConsistencyCheckResult,
    ) -> unreal.ParametersConsistencyCheckResult:
        """
        Convert python's ParametersConsistencyCheckResult to unreal.ParametersConsistencyCheckResult.

        :param consistency_check_result: ParametersConsistencyCheckResult instance
        :type consistency_check_result: ParametersConsistencyCheckResult

        :return: unreal.ParametersConsistencyCheckResult
        """

        result = unreal.ParametersConsistencyCheckResult()
        result.passed = consistency_check_result.passed
        result.reason = consistency_check_result.reason
        return result

    @unreal.ufunction(override=True)
    def check_job_parameters_consistency(
        self, open_job: unreal.DeadlineCloudJob
    ) -> unreal.ParametersConsistencyCheckResult:
        """
        Check parameters consistency of the given job.

        :param open_job: unreal.DeadlineCloudJob instance

        :return: unreal.ParametersConsistencyCheckResult
        """

        result = ParametersConsistencyChecker.check_job_parameters_consistency(
            job_template_path=open_job.path_to_template.file_path,
            job_parameters=[
                UnrealOpenJobParameterDefinition.from_unreal_param_definition(param).to_dict()
                for param in open_job.get_job_parameters()
            ],
        )
        return ParametersConsistencyCheckerImplementation.check_result_to_u_check_result(result)

    @unreal.ufunction(override=True)
    def fix_job_parameters_consistency(self, open_job: unreal.DeadlineCloudJob):
        """
        Fix parameters consistency of the given job.

        :param open_job: unreal.DeadlineCloudJob instance
        """

        fixed_parameters = ParametersConsistencyChecker.fix_job_parameters_consistency(
            job_template_path=open_job.path_to_template.file_path,
            job_parameters=[
                UnrealOpenJobParameterDefinition.from_unreal_param_definition(param).to_dict()
                for param in open_job.get_job_parameters()
            ],
        )

        if fixed_parameters:
            open_job.set_job_parameters(
                [
                    PythonYamlLibraryImplementation.job_parameter_to_u_parameter_definition(fixed)
                    for fixed in fixed_parameters
                ]
            )

    @unreal.ufunction(override=True)
    def check_step_parameters_consistency(
        self, open_job_step: unreal.DeadlineCloudStep
    ) -> unreal.ParametersConsistencyCheckResult:
        """
        Check parameters consistency of the given step.

        :param open_job_step: unreal.DeadlineCloudStep instance

        :return: unreal.ParametersConsistencyCheckResult
        """

        result = ParametersConsistencyChecker.check_step_parameters_consistency(
            step_template_path=open_job_step.path_to_template.file_path,
            step_parameters=[
                UnrealOpenJobStepParameterDefinition.from_unreal_param_definition(param).to_dict()
                for param in open_job_step.get_step_parameters()
            ],
        )
        return ParametersConsistencyCheckerImplementation.check_result_to_u_check_result(result)

    @unreal.ufunction(override=True)
    def fix_step_parameters_consistency(self, open_job_step: unreal.DeadlineCloudStep):
        """
        Fix parameters consistency of the given step.

        :param open_job_step: unreal.DeadlineCloudStep instance
        """
        fixed_parameters = ParametersConsistencyChecker.fix_step_parameters_consistency(
            step_template_path=open_job_step.path_to_template.file_path,
            step_parameters=[
                UnrealOpenJobStepParameterDefinition.from_unreal_param_definition(param).to_dict()
                for param in open_job_step.get_step_parameters()
            ],
        )

        if fixed_parameters:
            open_job_step.set_step_parameters(
                [
                    PythonYamlLibraryImplementation.step_parameter_to_u_step_task_parameter(fixed)
                    for fixed in fixed_parameters
                ]
            )

    @unreal.ufunction(override=True)
    def check_environment_variables_consistency(
        self, open_job_environment: unreal.DeadlineCloudEnvironment
    ) -> unreal.ParametersConsistencyCheckResult:
        """
        Check variables consistency of the given environment.

        :param open_job_environment: unreal.DeadlineCloudEnvironment instance

        :return: unreal.ParametersConsistencyCheckResult
        """

        result = ParametersConsistencyChecker.check_environment_variables_consistency(
            environment_template_path=open_job_environment.path_to_template.file_path,
            environment_variables=open_job_environment.variables.get_editor_property("variables"),
        )
        return ParametersConsistencyCheckerImplementation.check_result_to_u_check_result(result)

    @unreal.ufunction(override=True)
    def fix_environment_variables_consistency(
        self, open_job_environment: unreal.DeadlineCloudEnvironment
    ):
        """
        Fix variables consistency of the given environment.

        :param open_job_environment: unreal.DeadlineCloudEnvironment instance
        """
        fixed_variables = ParametersConsistencyChecker.fix_environment_variables_consistency(
            environment_template_path=open_job_environment.path_to_template.file_path,
            environment_variables=open_job_environment.variables.get_editor_property("variables"),
        )
        if fixed_variables:
            open_job_environment.variables.set_editor_property("variables", fixed_variables)
