import unreal
from typing import Any


class JobSharedSettings:
    """
    OpenJob shared settings representation.
    Contains SharedSettings model as dictionary built from template and allows to fill its values
    """

    def __init__(self, job_shared_settings: unreal.DeadlineCloudJobSharedSettingsStruct):
        self.source_shared_settings = job_shared_settings
        self.parameter_values: list[dict[str, Any]] = [
            {
                "name": "deadline:targetTaskRunStatus",
                "type": "STRING",
                "userInterface": {
                    "control": "DROPDOWN_LIST",
                    "label": "Initial State",
                },
                "allowedValues": ["READY", "SUSPENDED"],
                "value": self.get_initial_state(),
            },
            {
                "name": "deadline:maxFailedTasksCount",
                "description": "Maximum number of Tasks that can fail "
                "before the Job will be marked as failed.",
                "type": "INT",
                "userInterface": {
                    "control": "SPIN_BOX",
                    "label": "Maximum Failed Tasks Count",
                },
                "minValue": 0,
                "value": self.get_max_failed_tasks_count(),
            },
            {
                "name": "deadline:maxRetriesPerTask",
                "description": "Maximum number of times that a Task will retry "
                "before it's marked as failed.",
                "type": "INT",
                "userInterface": {
                    "control": "SPIN_BOX",
                    "label": "Maximum Retries Per Task",
                },
                "minValue": 0,
                "value": self.get_max_retries_per_task(),
            },
            {"name": "deadline:priority", "type": "INT", "value": self.get_priority()},
        ]

    def to_dict(self) -> list[dict]:
        """
        Returns the OpenJob SharedSettings object as list of dictionaries

        :return: OpenJob SharedSettings as list of dictionaries
        :rtype: dict
        """
        return self.parameter_values

    def get_initial_state(self) -> str:
        """
        Returns the OpenJob Initial State value

        :return: OpenJob Initial State
        :rtype: str
        """
        return self.source_shared_settings.initial_state

    def get_max_failed_tasks_count(self) -> int:
        """
        Returns the OpenJob Max Failed Task Count value

        :return: OpenJob Max Failed Task Count
        :rtype: int
        """
        return self.source_shared_settings.maximum_failed_tasks_count

    def get_max_retries_per_task(self) -> int:
        """
        Returns the OpenJob Max Retries Per Task value

        :return: OpenJob Max Retries Per Task
        :rtype: int
        """
        return self.source_shared_settings.maximum_retries_per_task

    def get_priority(self) -> int:
        """
        Return the OpenJob Priority value

        :return: OpenJob Priority
        :rtype: int
        """

        return self.source_shared_settings.priority
