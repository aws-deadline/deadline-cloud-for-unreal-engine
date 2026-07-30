# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import re
from typing import Optional

from deadline.unreal_logger import get_logger
from deadline.unreal_submitter.exceptions import SubmitterInputValidationError

logger = get_logger()


class DynamicChunkingHelper:
    """
    Helper class for TASK_CHUNKING extension.

    Contains all logic related to dynamic chunking:
    - Template detection (CHUNK[INT] type)
    - RangeConstraint validation (CONTIGUOUS only; MRQ cannot render non-contiguous ranges)
    - Frames parameter format validation (IntRangeList/IntRangeExpr)
    - Single CHUNK[INT] per step constraint
    """

    @staticmethod
    def is_chunk_parameter_type(param_type: str) -> bool:
        """
        Check if a parameter type is a CHUNK type (e.g., CHUNK[INT]).

        :param param_type: The parameter type string to check
        :return: True if the type contains "CHUNK", False otherwise
        """
        return "CHUNK" in param_type

    @staticmethod
    def is_using_dynamic_chunking(step_template_object: dict) -> bool:
        """
        Detect if a step template uses TASK_CHUNKING extension.

        Checks if any task parameter in the step template has a type containing "CHUNK"
        (e.g., CHUNK[INT]), which indicates the template uses dynamic chunking.

        :param step_template_object: Parsed YAML step template dictionary
        :return: True if any task parameter has type containing "CHUNK", False otherwise
        """
        try:
            task_param_definitions = step_template_object.get("parameterSpace", {}).get(
                "taskParameterDefinitions", []
            )
            for param in task_param_definitions:
                param_type = param.get("type", "")
                if DynamicChunkingHelper.is_chunk_parameter_type(param_type):
                    return True
            return False
        except (TypeError, AttributeError):
            logger.warning(
                "Malformed step_template_object in is_using_dynamic_chunking - "
                "CHUNK parameters is only expected in step_template_object"
            )
            return False

    @staticmethod
    def _validate_range_constraint(range_constraint: str) -> None:
        """
        Validate that RangeConstraint value is CONTIGUOUS.

        Only CONTIGUOUS is supported: Unreal's Movie Render Queue renders frame
        windows via custom_start_frame/custom_end_frame and cannot render an
        arbitrary (non-contiguous) frame list, so a NONCONTIGUOUS chunk would
        fail at render time on the worker. Rejecting it at submission surfaces
        the error to the user immediately instead.

        :param range_constraint: The RangeConstraint value to validate
        :type range_constraint: str

        :raises SubmitterInputValidationError: If value is not CONTIGUOUS
        """
        if range_constraint != "CONTIGUOUS":
            raise SubmitterInputValidationError(
                f'Invalid RangeConstraint value "{range_constraint}". '
                "Only CONTIGUOUS is supported: Unreal's Movie Render Queue cannot "
                "render non-contiguous frame lists."
            )

    @staticmethod
    def _validate_single_chunk_parameter_per_step(step_template_object: dict) -> None:
        """
        Validate that a step template contains at most one CHUNK[INT] task parameter.

        The OpenJobDescription TASK_CHUNKING extension only supports a single CHUNK[INT]
        parameter per step. This function counts CHUNK[INT] parameters and raises an
        error if more than one is found.

        :param step_template_object: Parsed YAML step template dictionary
        :raises SubmitterInputValidationError: If more than one CHUNK[INT] parameter is found
        """
        try:
            task_param_definitions = step_template_object.get("parameterSpace", {}).get(
                "taskParameterDefinitions", []
            )
            chunk_params = []
            for param in task_param_definitions:
                param_type = param.get("type", "")
                if DynamicChunkingHelper.is_chunk_parameter_type(param_type):
                    chunk_params.append(param.get("name", "unknown"))

            if len(chunk_params) > 1:
                raise SubmitterInputValidationError(
                    f"Step template contains {len(chunk_params)} CHUNK[INT] task parameters "
                    f"({', '.join(chunk_params)}), but only one CHUNK[INT] parameter is allowed per step. "
                    f"Please remove the extra CHUNK[INT] parameters from the step template."
                )
        except (TypeError, AttributeError):
            logger.warning(
                "Malformed step_template_object in _validate_single_chunk_parameter_per_step - "
                "skipping CHUNK parameter count validation"
            )

    @staticmethod
    def validate_chunk_parameter(step_template_object: dict, frames: Optional[str] = None) -> None:
        """
        Validate all elements of CHUNK[INT] parameters in a step template.

        This method consolidates all CHUNK[INT] validation:
        1. Validates only one CHUNK[INT] parameter exists per step
        2. Validates rangeConstraint value if it's a literal (not a template expression)
        3. Validates frames parameter format if provided

        :param step_template_object: Parsed YAML step template dictionary
        :param frames: Optional frames parameter value to validate
        :raises SubmitterInputValidationError: If validation fails
        """
        # Validate single CHUNK[INT] per step
        DynamicChunkingHelper._validate_single_chunk_parameter_per_step(step_template_object)

        # Find and validate CHUNK[INT] parameter's chunks configuration
        try:
            task_param_definitions = step_template_object.get("parameterSpace", {}).get(
                "taskParameterDefinitions", []
            )
            for param in task_param_definitions:
                param_type = param.get("type", "")
                if DynamicChunkingHelper.is_chunk_parameter_type(param_type):
                    chunks_config = param.get("chunks", {})

                    # Validate rangeConstraint if it's a literal value (not a template expression)
                    range_constraint = chunks_config.get("rangeConstraint", "")
                    if range_constraint and not range_constraint.startswith("{{"):
                        DynamicChunkingHelper._validate_range_constraint(range_constraint)

        except (TypeError, AttributeError):
            logger.warning(
                "Malformed step_template_object in validate_chunk_parameter - "
                "skipping chunks configuration validation"
            )

        # Validate frames parameter if provided
        if frames:
            DynamicChunkingHelper.validate_frames_parameter(frames)

    @staticmethod
    def validate_frames_parameter(frames: str) -> None:
        """
        Validate that frames parameter conforms to IntRangeList or IntRangeExpr format.
        Reference: https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/wiki/2023-09-Template-Schemas.md

        Valid formats per OpenJD specification:
        - Single integer: "5", "100", "-10"
        - Range: "1-100", "0-50", "-10-49", "-100--76"
        - Range with step: "1-100:2", "0-100:5"
        - Comma-separated list (IntRangeList): "1-10,15,20-30", "1,2,3"
        - Mixed formats: "1-10:2,15,20-30"

        Negative frame numbers are supported, matching Unreal sequences whose
        playback range starts below zero (the submitter's own auto-population
        can produce e.g. "-10-49") and the adaptor's chunk parser.

        Note: Empty frames is not valid.

        :param frames: Frame range expression string
        :raises SubmitterInputValidationError: If frames format is invalid or empty
        """
        if not frames or not frames.strip():
            raise SubmitterInputValidationError(
                "Frames parameter is required. "
                "Specify a frame range (e.g., '1-100', '1,5,10-20:2')."
            )

        frames = frames.strip()

        # Regex pattern for validating Frames parameter format
        # Supports IntRangeList and IntRangeExpr formats per OpenJD specification:
        # - Single integer (possibly negative): "5", "0", "-10"
        # - Range: "1-100", "-10-49", "-100--76"
        # - Range with step: "1-100:2" (step only valid with range, always positive)
        # - Comma-separated list: "1,2,3", "1-10,15,20-30"
        # - Mixed: "1-10:2,15,20-30"
        #
        # This validates the job-level OpenJD integer range expression. With
        # rangeConstraint CONTIGUOUS, the scheduler canonicalizes each dispatched
        # chunk as "<start>-<end>", including singleton chunks such as "5-5".
        # The adaptor therefore intentionally accepts a narrower runtime shape.
        single_int = r"-?\d+"
        range_with_optional_step = r"-?\d+--?\d+(?::\d+)?"
        int_range_element_pattern = rf"(?:{range_with_optional_step}|{single_int})"
        frames_validation_pattern = re.compile(
            rf"^{int_range_element_pattern}(?:,{int_range_element_pattern})*$"
        )

        if not frames_validation_pattern.match(frames):
            raise SubmitterInputValidationError(
                f'Invalid Frames parameter value "{frames}". '
                f"Frames must conform to IntRangeList format (e.g., '1-10,15,20-30') "
                f"or IntRangeExpr format (e.g., '1-100:2'). "
                f"Valid formats include: integers ('5', '-10'), ranges ('1-100', '-10-49'), "
                f"ranges with step ('1-100:2'), or comma-separated combinations."
            )

        range_element_pattern = re.compile(r"^(-?\d+)-(-?\d+)(?::(\d+))?$")
        for element in frames.split(","):
            range_match = range_element_pattern.match(element)
            if not range_match:
                continue

            start_frame, end_frame, step = range_match.groups()
            if int(start_frame) > int(end_frame):
                raise SubmitterInputValidationError(
                    f'Invalid Frames parameter value "{frames}". '
                    f'Range start must not exceed range end in "{element}".'
                )
            if step is not None and int(step) < 1:
                raise SubmitterInputValidationError(
                    f'Invalid Frames parameter value "{frames}". '
                    f'Range step must be at least 1 in "{element}".'
                )
