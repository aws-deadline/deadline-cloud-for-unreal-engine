# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity import (
    OpenJobStepParameterNames,
)


class TestOpenJobStepParameterNamesFramesPerTask:
    """Test that the new FRAMES_PER_TASK parameter is properly defined."""

    def test_frames_per_task_parameter_exists(self):
        # GIVEN/WHEN/THEN
        assert hasattr(OpenJobStepParameterNames, "FRAMES_PER_TASK")
        assert OpenJobStepParameterNames.FRAMES_PER_TASK == "FramesPerTask"

    def test_all_parameter_names_are_strings(self):
        # GIVEN
        parameter_names = [
            OpenJobStepParameterNames.QUEUE_MANIFEST_PATH,
            OpenJobStepParameterNames.MOVIE_PIPELINE_QUEUE_PATH,
            OpenJobStepParameterNames.LEVEL_SEQUENCE_PATH,
            OpenJobStepParameterNames.LEVEL_PATH,
            OpenJobStepParameterNames.MRQ_JOB_CONFIGURATION_PATH,
            OpenJobStepParameterNames.OUTPUT_PATH,
            OpenJobStepParameterNames.ADAPTOR_HANDLER,
            OpenJobStepParameterNames.FRAMES_PER_TASK,
            OpenJobStepParameterNames.SHOTS_PER_TASK,
            OpenJobStepParameterNames.TASK_INDEX,
        ]

        # WHEN/THEN
        for param_name in parameter_names:
            assert isinstance(param_name, str)
            assert len(param_name) > 0

    def test_frames_per_task_unique_value(self):
        # GIVEN
        all_parameter_values = [
            OpenJobStepParameterNames.QUEUE_MANIFEST_PATH,
            OpenJobStepParameterNames.MOVIE_PIPELINE_QUEUE_PATH,
            OpenJobStepParameterNames.LEVEL_SEQUENCE_PATH,
            OpenJobStepParameterNames.LEVEL_PATH,
            OpenJobStepParameterNames.MRQ_JOB_CONFIGURATION_PATH,
            OpenJobStepParameterNames.OUTPUT_PATH,
            OpenJobStepParameterNames.ADAPTOR_HANDLER,
            OpenJobStepParameterNames.FRAMES_PER_TASK,
            OpenJobStepParameterNames.SHOTS_PER_TASK,
            OpenJobStepParameterNames.TASK_INDEX,
        ]

        # WHEN/THEN - All parameter values should be unique
        assert len(all_parameter_values) == len(set(all_parameter_values))
        assert OpenJobStepParameterNames.FRAMES_PER_TASK in all_parameter_values
