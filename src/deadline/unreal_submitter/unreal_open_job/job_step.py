import os
import yaml
import unreal
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Optional

from deadline.unreal_submitter.settings import DEFAULT_JOB_STEP_TEMPLATE_FILE_PATH
from deadline.unreal_submitter.unreal_dependency_collector.common import os_abs_from_relative


class HostRequirements:
    """OpenJob host requirements representation"""

    def __init__(self, host_requirements):
        self.source_host_requirements = host_requirements
        self.requirements: dict = {}

        os_requirements = self._get_os_requirements()
        if os_requirements:
            # OS requirements are currently all amount type capabilities
            self.requirements["attributes"] = os_requirements

        hardware_requirements = self._get_hardware_requirements()
        if hardware_requirements:
            # hardware requirements are currently all amount
            self.requirements["amounts"] = hardware_requirements

    def _get_os_requirements(self) -> list[dict]:
        """
        Get requirements for OS family and CPU architecture

        :return: list of the OS requirements
        :rtype: list[dict]
        """
        requirements: list[dict] = []
        if self.source_host_requirements.operating_system:
            requirements.append(
                {
                    "name": "attr.worker.os.family",
                    "anyOf": [self.source_host_requirements.operating_system],
                }
            )
        if self.source_host_requirements.cpu_architecture:
            requirements.append(
                {
                    "name": "attr.worker.cpu.arch",
                    "anyOf": [self.source_host_requirements.cpu_architecture],
                }
            )
        return requirements

    def _get_hardware_requirements(self) -> list[dict[str, Any]]:
        """
        Get requirements for cpu, gpu and memory limits

        :return: list of the OS requirements
        :rtype: list[dict]
        """
        cpus = self._get_amount_requirement(
            self.source_host_requirements.cp_us, "amount.worker.vcpu"
        )
        memory = self._get_amount_requirement(
            self.source_host_requirements.memory, "amount.worker.memory", 1024
        )
        # TODO gpu amount
        # gpus = self._get_amount_requirement(self.source_host_requirements.gpus, "amount.worker.gpu")
        gpu_memory = self._get_amount_requirement(
            self.source_host_requirements.gp_us, "amount.worker.gpu.memory", 1024
        )
        scratch_space = self._get_amount_requirement(
            self.source_host_requirements.scratch_space, "amount.worker.disk.scratch"
        )
        requirements: list[dict[str, Any]] = [
            item for item in [cpus, memory, gpu_memory, scratch_space] if item is not None
        ]
        return requirements

    @staticmethod
    def _get_amount_requirement(source_interval, name: str, scaling_factor: int = 1) -> dict:
        """
        Helper method to get the amount of Host Requirement setting interval

        :param source_interval: Interval unreal setting
        :param name: AWS HostRequirements setting name
        :param scaling_factor: Multiplier number by which to scale the source_interval values

        :return: Amount requirement as dictionary
        :rtype: dict
        """
        requirement = {}
        if source_interval.min > 0 or source_interval.max > 0:
            requirement = {"name": name}
            if source_interval.min > 0:
                requirement["min"] = source_interval.min * scaling_factor
            if source_interval.max > 0:
                requirement["max"] = source_interval.max * scaling_factor
        return requirement

    def as_dict(self) -> dict:
        """
        Returns the HostRequirements as dictionary

        :return: Host Requirements as dictionary
        :rtype: dict
        """
        return self.requirements


class JobStep:
    """
    Represents a OpenJob Step
    """

    def __init__(self, step_template, step_settings, host_requirements, queue_manifest_path):
        """
        Build JobStep, set its name and fill dependencies list

        :param step_template: Step default template to use for this step
        :type step_template: dict
        :param step_settings: Deadline Cloud Step Setting object
        """
        self._job_step = deepcopy(step_template)

        self._set_name(step_settings)
        self._fill_step_dependency_list(step_settings)
        self._fill_host_requirements(host_requirements)

    def _set_name(self, step_settings):
        """
        Set the name of this Step

        :param step_settings: Deadline Cloud Step Setting object with the name
        :raises Exception: When job name is empty or None
        """
        new_name = step_settings.name
        if not new_name:
            raise Exception("Job step name could not be empty")

        self._job_step["name"] = new_name

    def _set_step_path_parameter(self, parameter_name: str, path_value: str):
        """
        Fill the path parameter by name of this Step with the given value

        :param parameter_name: Name of the parameter
        :type parameter_name: str
        :param path_value: Value of the parameter
        :type path_value: str
        """
        parameter_space = self._job_step["parameterSpace"]
        parameter_definition = next(
            (
                parameter_definition
                for parameter_definition in parameter_space["taskParameterDefinitions"]
                if parameter_definition["name"] == parameter_name
            ),
            None,
        )
        if parameter_definition is not None:
            parameter_definition["range"] = [path_value]

    def _fill_step_dependency_list(self, step_settings):
        """
        Fill the dependsOn list of this Step with the given step settings' "depends_on" attribute

        :param step_settings: Deadline Cloud Step Setting object with the depends_on attribute
        """
        dependencies_list = [
            {"dependsOn": dependency} for dependency in step_settings.depends_on if dependency != ""
        ]
        if len(dependencies_list) > 0:
            self._job_step["dependencies"] = dependencies_list

    def _fill_host_requirements(self, host_requirements):
        if host_requirements.run_on_all_worker_nodes:
            return
        self._job_step["hostRequirements"] = HostRequirements(host_requirements).as_dict()

    def get_step_input_files(self) -> list[str]:
        return []

    def as_dict(self):
        """Returns a dictionary representation of this Step"""
        return self._job_step


class CustomScriptJobStep(JobStep):
    """
    Represents a OpenJob Step for Custom Script executing
    """

    def __init__(self, step_template, step_settings, host_requirements, queue_manifest_path):
        """
        Build JobStep, set its name, fill dependencies list and set script path parameter
        """
        super().__init__(step_template, step_settings, host_requirements, queue_manifest_path)

        self._set_script_path_parameter(os_abs_from_relative(step_settings.script.file_path))

    def _set_script_path_parameter(self, script_path):
        """
        Fill the necessary parameter "ScriptPath" with the given script path.

        Use :meth:`deadline.unreal_submitter.unreal_open_job.job_step.JobStep._set_step_path_parameter()`

        :param script_path: Path to the script
        :type script_path: str
        """
        if not os.path.exists(script_path):
            raise Exception(f"Script path does not exist on the disk: {script_path}")

        self._set_step_path_parameter(parameter_name="ScriptPath", path_value=script_path)

    def get_step_input_files(self) -> list[str]:
        """
        Return the script paths from ScriptPath range attribute

        :return: List of script paths
        :rtype: list[str]
        """
        script_attachments = []

        parameter_space = self._job_step["parameterSpace"]
        parameter_definition = next(
            (
                parameter_definition
                for parameter_definition in parameter_space["taskParameterDefinitions"]
                if parameter_definition["name"] == "ScriptPath"
            ),
            None,
        )
        if parameter_definition is not None:
            script_attachments = [attachment for attachment in parameter_definition["range"]]

        return script_attachments


class RenderJobStep(JobStep):
    """
    Represents a OpenJob Step for Render executing
    """

    def __init__(self, step_template, step_settings, host_requirements, queue_manifest_path):
        """
        Build JobStep, set its name, fill dependencies list and set queue manifest path parameter
        """
        super().__init__(step_template, step_settings, host_requirements, queue_manifest_path)

        self._set_queue_manifest_path_parameter(queue_manifest_path)

    def _set_name(self, step_settings):
        """
        Override the behavior of the JobStep._set_name() method and setup name as "Render"
        """
        self._job_step["name"] = "Render"

    def _set_queue_manifest_path_parameter(self, queue_manifest_path):
        """
        Fill the necessary parameter "QueueManifestPath" with the given script path.

        Use :meth:`deadline.unreal_submitter.unreal_open_job.job_step.JobStep._set_step_path_parameter`

        :param script_path: Path to the script
        :type script_path: str
        """
        self._set_step_path_parameter(
            parameter_name="QueueManifestPath", path_value=queue_manifest_path
        )


@dataclass
class JobStepDescriptor:
    """
    Common Job Step descriptor that contains information
    about the step type, its representation class and appropriate Unreal setting class
    """

    #: Step default type, for example "Render" or "CustomScript"
    step_type: str
    #: Representation class of the Step template, inherited from :class:``
    step_class: type[JobStep]
    setting_class: unreal.Class


class JobStepFactory:
    """Build JobStep with the given context"""

    with open(DEFAULT_JOB_STEP_TEMPLATE_FILE_PATH) as f:
        #: Job Step default template that contains unfilled description of the Job's steps
        DEFAULT_JOB_STEP_TEMPLATE = yaml.safe_load(f)

    #: Common Step mapping list of the :class:`deadline.unreal_submitter.unreal_open_job.job_step.JobStepDescriptor`
    #: instances for the Render and CustomScript steps
    JOB_STEP_MAPPING = [
        JobStepDescriptor(
            "Render", RenderJobStep, unreal.DeadlineCloudRenderStepSetting().static_class()
        ),
        JobStepDescriptor(
            "CustomScript",
            CustomScriptJobStep,
            unreal.DeadlineCloudCustomScriptStepSetting().static_class(),
        ),
    ]

    @staticmethod
    def get_step_descriptor_by_setting_class(
        setting_class: unreal.Class,
    ) -> Optional[JobStepDescriptor]:
        """
        Returns the :class:`deadline.unreal_submitter.unreal_open_job.job_step.JobStepDescriptor` instance that kept in
        :class:`deadline.unreal_submitter.unreal_open_job.job_step.JobStepFactory.JOB_STEP_MAPPING`
        by the given unreal setting class (Render or CustomScript)

        :param setting_class: Unreal Settings instance class
        :type setting_class: unreal.Class

        :return: :class:`deadline.unreal_submitter.unreal_open_job.job_step.JobStepDescriptor` instance for the Render/CustomScript
        :rtype: :class:`deadline.unreal_submitter.unreal_open_job.job_step.JobStepDescriptor`
        """
        return next(
            (
                step_descriptor
                for step_descriptor in JobStepFactory.JOB_STEP_MAPPING
                if step_descriptor.setting_class == setting_class
            ),
            None,
        )

    @staticmethod
    def get_step_template(step_descriptor: JobStepDescriptor):
        """
        Read the JobStep template file and get the appropriate JobStep

        :param step_descriptor: :class:`deadline.unreal_submitter.unreal_open_job.job_step.JobStepDescriptor` instance
        :type step_descriptor: :class:`deadline.unreal_submitter.unreal_open_job.job_step.JobStepDescriptor`

        :return: JobStep template
        :rtype: dict
        """

        step_template = next(
            (
                step_template
                for step_template in JobStepFactory.DEFAULT_JOB_STEP_TEMPLATE["steps"]
                if step_template["name"] == step_descriptor.step_type
            ),
            None,
        )
        return step_template

    @classmethod
    def create_steps(
        cls,
        job_settings: list[unreal.MoviePipelineSetting],
        queue_manifest_path: str,
        host_requirements,
    ) -> list[JobStep]:
        """
        Create the Job Steps list using the provided job settings and other parameters

        :param job_settings: list of unreal.MoviePipelineSetting settings
        :type job_settings: unreal.MoviePipelineSetting
        :param queue_manifest_path: OS path for the queue manifest file
        :type queue_manifest_path: str
        :param host_requirements: AWS Host requirements settings

        :return: list of the :class:`deadline.unreal_submitter.unreal_open_job.job_step.JobStep` instances
        :rtype: :class:`deadline.unreal_submitter.unreal_open_job.job_step.JobStep`
        """

        steps = []

        for setting in job_settings:
            step_descriptor = JobStepFactory.get_step_descriptor_by_setting_class(
                setting.get_class()
            )
            if not step_descriptor:
                continue

            if hasattr(setting, "deadline_cloud_steps"):
                for script_step_setting in setting.deadline_cloud_steps:
                    steps.append(
                        step_descriptor.step_class(
                            step_template=JobStepFactory.get_step_template(step_descriptor),
                            step_settings=script_step_setting,
                            host_requirements=host_requirements,
                            queue_manifest_path=queue_manifest_path,
                        )
                    )

            else:
                steps.append(
                    step_descriptor.step_class(
                        step_template=JobStepFactory.get_step_template(step_descriptor),
                        step_settings=setting,
                        host_requirements=host_requirements,
                        queue_manifest_path=queue_manifest_path,
                    )
                )

        return steps
