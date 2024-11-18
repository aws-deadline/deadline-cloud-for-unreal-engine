#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import yaml
from typing import Any
from dataclasses import dataclass
from deadline.unreal_logger import get_logger


logger = get_logger()


@dataclass
class ParametersConsistencyCheckResult:
    passed: bool
    reason: str

    def __str__(self):
        return f"{self.__class__.__name__}: {self.passed}; {self.reason}"


class ParametersConsistencyChecker:

    @staticmethod
    def symmetric_difference(
        left: list[tuple[Any, Any]], right: list[tuple[Any, Any]]
    ) -> tuple[list[tuple[Any, Any]], list[tuple[Any, Any]]]:
        missed_in_left = list(set(right).difference(set(left)))
        missed_in_right = list(set(left).difference(set(right)))
        return missed_in_left, missed_in_right

    @staticmethod
    def check_parameters_consistency(
        yaml_parameters: list[tuple[str, str]], data_asset_parameters: list[tuple[str, str]]
    ) -> ParametersConsistencyCheckResult:
        """
        Check the consistency of the parameters described in the YAML and OpenJob asset (Job, Step, Environment).
        Parameters are not consensual if:
        1. OpenJob asset's parameters are missed in YAML
        2. YAML parameters are missed in OpenJob asset
        """

        reasons = []
        passed = True

        missed_in_yaml, missed_in_data_asset = ParametersConsistencyChecker.symmetric_difference(
            left=yaml_parameters, right=data_asset_parameters
        )

        if missed_in_yaml:
            passed = False
            missed_in_yaml_str = [f"{p[0]} ({p[1]})" for p in missed_in_yaml]
            warn_message = "Data Asset's parameters missed in YAML: {}".format(
                ", ".join(missed_in_yaml_str)
            )
            logger.warning(warn_message)
            reasons.append(warn_message)

        if missed_in_data_asset:
            passed = False
            missed_in_data_asset_str = [f"{p[0]} ({p[1]})" for p in missed_in_data_asset]
            warn_message = "YAML's parameters missed in Data Asset: {}".format(
                ", ".join(missed_in_data_asset_str)
            )
            logger.warning(warn_message)
            reasons.append(warn_message)

        reason = "\n".join(reasons) if not passed else "Parameters are consensual"

        result = ParametersConsistencyCheckResult(passed, reason)

        logger.info(result)

        return result

    @staticmethod
    def fix_parameters_consistency(
        missed_in_yaml: list[tuple[str, str]],
        missed_in_data_asset: list[tuple[str, str]],
        yaml_parameters: list[dict[str, Any]],
        data_asset_parameters: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

        logger.info(f"Fixing missed parameters in YAML: {missed_in_yaml}")
        logger.info(f"Fixing missed parameters in Data Asset: {missed_in_data_asset}")

        fixed_parameters = []
        if missed_in_yaml or missed_in_data_asset:
            for p in data_asset_parameters:
                if (p["name"], p["type"]) not in missed_in_yaml:
                    fixed_parameters.append(p)
            for p in yaml_parameters:
                if (p["name"], p["type"]) in missed_in_data_asset:
                    fixed_param = {"name": p["name"], "type": p["type"]}
                    if "default" in p:
                        fixed_param["default"] = p["default"]
                    fixed_parameters.append(p)

            fixed_parameters.sort(key=lambda x: x["name"])
        else:
            fixed_parameters = yaml_parameters

        logger.info(f"Fixed parameters: {fixed_parameters}")

        return fixed_parameters

    @staticmethod
    def fix_variables_consistency(
        missed_in_yaml: list[tuple[str, str]],
        missed_in_data_asset: list[tuple[str, str]],
        yaml_variables: dict[str, str],
        data_asset_variables: dict[str, str],
    ) -> dict[str, str]:

        logger.info(f"Fixing missed variables in YAML: {missed_in_yaml}")
        logger.info(f"Fixing missed variables in Data Asset: {missed_in_data_asset}")

        fixed_variables = {}

        if missed_in_yaml or missed_in_data_asset:
            for key, value in data_asset_variables.items():
                if (key, "VARIABLE") not in missed_in_yaml:
                    fixed_variables[key] = value

            for key, value in yaml_variables.items():
                if (key, "VARIABLE") in missed_in_data_asset:
                    fixed_variables[key] = value
        else:
            fixed_variables = yaml_variables

        logger.info(f"Fixed variables: {fixed_variables}")

        return fixed_variables

    @staticmethod
    def check_job_parameters_consistency(
        job_template_path: str, job_parameters: list[dict[str, Any]]
    ) -> ParametersConsistencyCheckResult:

        logger.info("Checking OpenJob parameters consistency ...")

        with open(job_template_path, "r") as f:
            job_template = yaml.safe_load(f)

        return ParametersConsistencyChecker.check_parameters_consistency(
            yaml_parameters=[(p["name"], p["type"]) for p in job_template["parameterDefinitions"]],
            data_asset_parameters=[(p["name"], p["type"]) for p in job_parameters],
        )

    @staticmethod
    def fix_job_parameters_consistency(
        job_template_path: str, job_parameters: list[dict[str, Any]]
    ) -> list[dict[str, str]]:

        logger.info("Fixing OpenJob parameters consistency ...")

        with open(job_template_path, "r") as f:
            job_template = yaml.safe_load(f)

        missed_in_yaml, missed_in_data_asset = ParametersConsistencyChecker.symmetric_difference(
            left=[(p["name"], p["type"]) for p in job_template["parameterDefinitions"]],
            right=[(p["name"], p["type"]) for p in job_parameters],
        )

        fixed_parameters = ParametersConsistencyChecker.fix_parameters_consistency(
            missed_in_yaml=missed_in_yaml,
            missed_in_data_asset=missed_in_data_asset,
            yaml_parameters=job_template["parameterDefinitions"],
            data_asset_parameters=job_parameters,
        )

        logger.info(f"Fixed OpenJob parameters: {fixed_parameters}")

        return fixed_parameters

    @staticmethod
    def check_step_parameters_consistency(
        step_template_path: str,
        step_parameters: list[dict[str, Any]],
    ) -> ParametersConsistencyCheckResult:

        logger.info("Checking OpenJobStep parameters consistency ...")

        with open(step_template_path, "r") as f:
            step_template = yaml.safe_load(f)

        return ParametersConsistencyChecker.check_parameters_consistency(
            yaml_parameters=[
                (p["name"], p["type"])
                for p in step_template["parameterSpace"]["taskParameterDefinitions"]
            ],
            data_asset_parameters=[(p["name"], p["type"]) for p in step_parameters],
        )

    @staticmethod
    def fix_step_parameters_consistency(
        step_template_path: str,
        step_parameters: list[dict[str, Any]],
    ) -> list[dict[str, str]]:

        logger.info("Fixing OpenJobStep parameters consistency ...")

        with open(step_template_path, "r") as f:
            step_template = yaml.safe_load(f)

        missed_in_yaml, missed_in_data_asset = ParametersConsistencyChecker.symmetric_difference(
            left=[
                (p["name"], p["type"])
                for p in step_template["parameterSpace"]["taskParameterDefinitions"]
            ],
            right=[(p["name"], p["type"]) for p in step_parameters],
        )

        fixed_parameters = ParametersConsistencyChecker.fix_parameters_consistency(
            missed_in_yaml=missed_in_yaml,
            missed_in_data_asset=missed_in_data_asset,
            yaml_parameters=step_template["parameterSpace"]["taskParameterDefinitions"],
            data_asset_parameters=step_parameters,
        )

        logger.info(f"Fixed OpenJobStep parameters: {fixed_parameters}")

        return fixed_parameters

    @staticmethod
    def check_environment_variables_consistency(
        environment_template_path: str,
        environment_variables: dict[str, str],
    ) -> ParametersConsistencyCheckResult:

        logger.info("Checking OpenJobEnvironment variables consistency ...")

        with open(environment_template_path, "r") as f:
            environment_template = yaml.safe_load(f)

        return ParametersConsistencyChecker.check_parameters_consistency(
            yaml_parameters=[(k, "VARIABLE") for k in environment_template["variables"].keys()],
            data_asset_parameters=[(v, "VARIABLE") for v in environment_variables.keys()],
        )

    @staticmethod
    def fix_environment_variables_consistency(
        environment_template_path: str,
        environment_variables: dict[str, str],
    ):

        logger.info("Fixing OpenJobEnvironment variables consistency ...")

        with open(environment_template_path, "r") as f:
            environment_template = yaml.safe_load(f)

        missed_in_yaml, missed_in_data_asset = ParametersConsistencyChecker.symmetric_difference(
            left=[(k, "VARIABLE") for k in environment_template["variables"].keys()],
            right=[(v, "VARIABLE") for v in environment_variables.keys()],
        )

        fixed_variables = ParametersConsistencyChecker.fix_variables_consistency(
            missed_in_yaml=missed_in_yaml,
            missed_in_data_asset=missed_in_data_asset,
            yaml_variables=environment_template["variables"],
            data_asset_variables=environment_variables,
        )

        logger.info(f"Fixed OpenJobEnvironment variables: {fixed_variables}")

        return fixed_variables
