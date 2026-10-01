# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import unreal
from typing import Any


class JobSharedSettings:
    """
    OpenJob shared settings representation.
    Contains SharedSettings model as dictionary built from template and allows to fill its values.

    The serialized ``parameter_values`` list is the single source of truth: the typed getters
    read from it, and :meth:`update_parameter_value` writes to it. This keeps the values a
    caller mutates (e.g. a pre-GUI submission hook setting ``deadline:priority``) and the
    values the getters report from ever diverging.
    """

    _INITIAL_STATE_NAME = "deadline:targetTaskRunStatus"
    _MAX_FAILED_TASKS_COUNT_NAME = "deadline:maxFailedTasksCount"
    _MAX_RETRIES_PER_TASK_NAME = "deadline:maxRetriesPerTask"
    _PRIORITY_NAME = "deadline:priority"

    def __init__(
        self,
        initial_state: str = "READY",
        max_failed_tasks_count: int = 1,
        max_retries_per_task: int = 2,
        priority: int = 50,
    ):
        self.parameter_values: list[dict[str, Any]] = [
            {
                "name": JobSharedSettings._INITIAL_STATE_NAME,
                "type": "STRING",
                "userInterface": {
                    "control": "DROPDOWN_LIST",
                    "label": "Initial State",
                },
                "allowedValues": ["READY", "SUSPENDED"],
                "value": initial_state,
            },
            {
                "name": JobSharedSettings._MAX_FAILED_TASKS_COUNT_NAME,
                "description": "Maximum number of Tasks that can fail "
                "before the Job will be marked as failed.",
                "type": "INT",
                "userInterface": {
                    "control": "SPIN_BOX",
                    "label": "Maximum Failed Tasks Count",
                },
                "minValue": 0,
                "value": max_failed_tasks_count,
            },
            {
                "name": JobSharedSettings._MAX_RETRIES_PER_TASK_NAME,
                "description": "Maximum number of times that a Task will retry "
                "before it's marked as failed.",
                "type": "INT",
                "userInterface": {
                    "control": "SPIN_BOX",
                    "label": "Maximum Retries Per Task",
                },
                "minValue": 0,
                "value": max_retries_per_task,
            },
            {
                "name": JobSharedSettings._PRIORITY_NAME,
                "type": "INT",
                "value": priority,
            },
        ]

    @classmethod
    def from_u_deadline_cloud_job_shared_settings(
        cls, job_shared_settings: unreal.DeadlineCloudJobSharedSettingsStruct
    ):
        """
        Create JobSharedSettings instance from unreal.DeadlineCloudJobSharedSettingsStruct object

        :return: JobSharedSettings instance
        :rtype: JobSharedSettings
        """
        return cls(
            initial_state=job_shared_settings.initial_state,
            max_failed_tasks_count=job_shared_settings.maximum_failed_tasks_count,
            max_retries_per_task=job_shared_settings.maximum_retries_per_task,
            priority=job_shared_settings.priority,
        )

    def serialize(self) -> list[dict[str, Any]]:
        """
        Returns the OpenJob SharedSettings object as list of dictionaries

        :return: OpenJob SharedSettings as list of dictionaries
        :rtype: list
        """
        return self.parameter_values

    def _get_parameter_value(self, name: str) -> Any:
        """
        Return the current value of the shared setting with the given parameter name.

        :param name: Shared setting parameter name, e.g. ``deadline:priority``
        :type name: str

        :return: The setting's current value
        :rtype: Any
        """
        return next(p["value"] for p in self.parameter_values if p["name"] == name)

    def get_initial_state(self) -> str:
        """
        Returns the OpenJob Initial State value

        :return: OpenJob Initial State
        :rtype: str
        """
        return self._get_parameter_value(JobSharedSettings._INITIAL_STATE_NAME)

    def get_max_failed_tasks_count(self) -> int:
        """
        Returns the OpenJob Max Failed Task Count value

        :return: OpenJob Max Failed Task Count
        :rtype: int
        """
        return self._get_parameter_value(JobSharedSettings._MAX_FAILED_TASKS_COUNT_NAME)

    def get_max_retries_per_task(self) -> int:
        """
        Returns the OpenJob Max Retries Per Task value

        :return: OpenJob Max Retries Per Task
        :rtype: int
        """
        return self._get_parameter_value(JobSharedSettings._MAX_RETRIES_PER_TASK_NAME)

    def get_priority(self) -> int:
        """
        Return the OpenJob Priority value

        :return: OpenJob Priority
        :rtype: int
        """

        return self._get_parameter_value(JobSharedSettings._PRIORITY_NAME)
