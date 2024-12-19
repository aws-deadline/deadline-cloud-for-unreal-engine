#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import yaml
from typing import Any
from dataclasses import dataclass
from deadline.unreal_logger import get_logger


logger = get_logger()


@dataclass
class ParametersConsistencyCheckResult:
    """
    Data class to store the result of the parameter consistency check

    :cvar passed: Result of consistency check, True if passed, False otherwise
    :cvar reason: Description of consistency check
    """

    passed: bool
    reason: str

    def __str__(self):
        return f"{self.__class__.__name__}: {self.passed}; {self.reason}"


class ParametersConsistencyChecker:
    """Class contains helper methods to check and fix the consistency of the parameters"""

    @staticmethod
    def symmetric_difference(
        left: list[tuple[Any, Any]], right: list[tuple[Any, Any]]
    ) -> tuple[list[tuple[Any, Any]], list[tuple[Any, Any]]]:
        """
        Return symmetric difference of two lists:
            1. What contained in right, but missed in left
            2. What contained in left, but missed in right

        Example:
            - left = [("ParamA", "INT"), ("ParamB", "STRING")]
            - right = [("ParamB", "STRING"), ("ParamC", "FLOAT")]
            - missed_in_left = [("ParamC", "FLOAT")]
            - missed_in_right = [("ParamA", "INT")]

        :param left: First list to compare
        :type left: list[tuple[Any, Any]]
        :param right: Second list to compare
        :type right: list[tuple[Any, Any]]

        :return: Symmetric difference of two lists
        :rtype: tuple[list[tuple[Any, Any]], list[tuple[Any, Any]]]
        """

        missed_in_left = list(set(right).difference(set(left)))
        missed_in_right = list(set(left).difference(set(right)))
        return missed_in_left, missed_in_right

    @staticmethod
    def check_parameters_consistency(
        yaml_parameters: list[tuple[str, str]], data_asset_parameters: list[tuple[str, str]]
    ) -> ParametersConsistencyCheckResult:
        """
        Check the consistency of the parameters described in the YAML and
        OpenJob asset (Job, Step, Environment).
        Each parameter is a tuple of two strings: name and type

        Parameters are not consistent if:
            1. OpenJob asset's parameters are missed in YAML
            2. YAML parameters are missed in OpenJob asset

        Example:
            - yaml_parameters = [("ParamA", "INT"), ("ParamB", "STRING")]
            - data_asset_parameters = [("ParamB", "STRING"), ("ParamC", "FLOAT")]
            - ParametersConsistencyCheckResult:
                - passed = False
                - reason = "Data Asset's parameters missed in YAML: ParamA (INT), ParamC (FLOAT)"

        :param yaml_parameters: YAML parameters to check
        :type yaml_parameters: list[tuple[str, str]]
        :param data_asset_parameters: Data asset parameters to check
        :type data_asset_parameters: list[tuple[str, str]]

        :return: Parameters consistency check result
        :rtype: ParametersConsistencyCheckResult
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

        reason = "\n".join(reasons) if not passed else "Parameters are consistent"

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
        """
        Fix the consistency of the parameters described in the YAML and DataAsset.
        Expect lists of missed parameters and current parameters in both sources.

        Each missed parameter is a tuple of two strings: name and type

        If both lists of the missed parameters is empty that means current parameters is equal, so
        return YAML parameters without any changes.

        :param missed_in_yaml: List of parameters missed in YAML
        :type missed_in_yaml: list[tuple[str, str]]
        :param missed_in_data_asset: List of parameters missed in Data Asset
        :type missed_in_data_asset: list[tuple[str, str]]
        :param yaml_parameters: Complete list of YAML parameters
        :type yaml_parameters: list[dict[str, Any]]
        :param data_asset_parameters: Complete list of Data Asset parameters
        :type data_asset_parameters: list[dict[str, Any]]

        :return: List of fixed parameters
        :rtype: list[dict[str, Any]]
        """

        logger.info(f"Fixing missed parameters in YAML: {missed_in_yaml}")
        logger.info(f"Fixing missed parameters in Data Asset: {missed_in_data_asset}")

        if not (missed_in_yaml or missed_in_data_asset):
            logger.info("No parameters to fix")
            return yaml_parameters

        fixed_parameters = []

        for p in data_asset_parameters:
            if (p["name"], p["type"]) not in missed_in_yaml:
                fixed_parameters.append(p)
        for p in yaml_parameters:
            if (p["name"], p["type"]) in missed_in_data_asset:
                fixed_param = {"name": p["name"], "type": p["type"]}
                if "default" in p:
                    fixed_param["default"] = p["default"]
                fixed_parameters.append(fixed_param)

        fixed_parameters.sort(key=lambda x: x["name"])

        logger.info(f"Fixed parameters: {fixed_parameters}")

        return fixed_parameters

    @staticmethod
    def fix_variables_consistency(
        missed_in_yaml: list[tuple[str, str]],
        missed_in_data_asset: list[tuple[str, str]],
        yaml_variables: dict[str, str],
        data_asset_variables: dict[str, str],
    ) -> dict[str, str]:
        """
        Fix the consistency of the environment variables described in the YAML and DataAsset
        Expect lists of missed parameters and current parameters in both sources.

        Each missed parameter is a tuple of two strings: name and type

        If both lists of the missed parameters is empty that means current variables is equal, so
        return YAML variables without any changes.

        :param missed_in_yaml: List of variables missed in YAML
        :type missed_in_yaml: list[tuple[str, str]]
        :param missed_in_data_asset: List of variables missed in Data Asset
        :type missed_in_data_asset: list[tuple[str, str]]
        :param yaml_variables: Complete list of YAML variables
        :type yaml_variables: list[dict[str, Any]]
        :param data_asset_variables: Complete list of Data Asset variables
        :type data_asset_variables: list[dict[str, Any]]

        :return: Fixed environment variables dictionary
        :rtype: dict[str, str]
        """

        logger.info(f"Fixing missed variables in YAML: {missed_in_yaml}")
        logger.info(f"Fixing missed variables in Data Asset: {missed_in_data_asset}")

        if not (missed_in_yaml or missed_in_data_asset):
            logger.info("No variables to fix")
            return yaml_variables

        fixed_variables = {}

        for key, value in data_asset_variables.items():
            if (key, "VARIABLE") not in missed_in_yaml:
                fixed_variables[key] = value

        for key, value in yaml_variables.items():
            if (key, "VARIABLE") in missed_in_data_asset:
                fixed_variables[key] = value

        logger.info(f"Fixed variables: {fixed_variables}")

        return fixed_variables

    @staticmethod
    def check_job_parameters_consistency(
        job_template_path: str, job_parameters: list[dict[str, Any]]
    ) -> ParametersConsistencyCheckResult:
        """
        Check if the job parameters are consistent.

        :param job_template_path: Path to the job template to read YAML parameters
        :type job_template_path: str
        :param job_parameters: List of job parameters in DataAsset
        :type job_parameters: list[dict[str, Any]]

        :return: Parameters consistency check result that indicates parameters consistent or not
        :rtype: ParametersConsistencyCheckResult
        """

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
        """
        Fix the job parameters to make them consistent.

        :param job_template_path: Path to the job template to read YAML parameters
        :type job_template_path: str
        :param job_parameters: List of job parameters in DataAsset
        :type job_parameters: list[dict[str, Any]]

        :return: List of fixed parameters
        :rtype: list[dict[str, str]]
        """

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
        """
        Check if the job parameters are consistent.

        :param step_template_path: Path to the step template to read YAML parameters
        :type step_template_path: str
        :param step_parameters: List of step parameters in DataAsset
        :type step_parameters: list[dict[str, Any]]

        :return: Parameters consistency check result that indicates parameters consistent or not
        :rtype: ParametersConsistencyCheckResult
        """

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
        """
        Fix the step parameters to make them consistent.

        :param step_template_path: Path to the step template to read YAML parameters
        :type step_template_path: str
        :param step_parameters: List of step parameters in DataAsset
        :type step_parameters: list[dict[str, Any]]

        :return: List of fixed parameters
        :rtype: list[dict[str, str]]
        """

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
        """
        Check if the environment variables are consistent.

        :param environment_template_path: Path to the environment template to read YAML variables
        :type environment_template_path: str
        :param environment_variables: Environment variables dictionary in DataAsset
        :type environment_variables: dict[str, str]

        :return: Parameters consistency check result that indicates variables consistent or not
        :rtype: ParametersConsistencyCheckResult
        """

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
        """
        Fix the environment variables to make them consistent.

        :param environment_template_path: Path to the environment template to read YAML variables
        :type environment_template_path: str
        :param environment_variables: Environment variables dictionary in DataAsset
        :type environment_variables: dict[str, str]

        :return: Dictionary of fixed environment variables
        :rtype: dict[str, str]
        """

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
