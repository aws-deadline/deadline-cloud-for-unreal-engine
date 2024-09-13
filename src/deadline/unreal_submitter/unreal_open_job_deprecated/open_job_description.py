import os
import yaml
import unreal
from copy import deepcopy
from typing import Dict, Any, List

from deadline.client.job_bundle import deadline_yaml_dump, create_job_history_bundle_dir
from deadline.client.job_bundle.submission import AssetReferences
from deadline.unreal_submitter.settings import DEFAULT_JOB_TEMPLATE_FILE_PATH
from deadline.unreal_submitter.common import (
    get_project_directory,
    get_project_file_path,
    soft_obj_path_to_str,
)
from deadline.unreal_submitter.unreal_dependency_collector.common import (
    DependencyFilters,
    os_path_from_unreal_path,
)
from deadline.unreal_submitter.unreal_dependency_collector.common import os_abs_from_relative
from deadline.unreal_submitter.unreal_dependency_collector.collector import DependencyCollector

from deadline.unreal_submitter.unreal_open_job.job_step import JobStep, JobStepFactory


class JobSharedSettings:
    """
    OpenJob shared settings representation.
    Contains SharedSettings model as dictionary built from template and allows to fill its values
    """

    def __init__(self, job_shared_settings):
        self.source_shared_settings = job_shared_settings
        self.parameter_values: List[Dict[Any, Any]] = [
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
                "description": "Maximum number of Tasks that can fail before the Job will be marked as failed.",
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
                "description": "Maximum number of times that a Task will retry before it's marked as failed.",
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
        # TODO Add priority to the settings
        return 1


class OpenJobDescription:
    """
    Represents a OpenJob description object
    """

    def __init__(self, mrq_job: unreal.MoviePipelineExecutorJob):
        """
        Build OpenJob with the given MovieP ipeline Executor Job and Queue Manifest path

        :param mrq_job: unreal.MoviePipelineExecutorJob object with the Job context
        :type mrq_job: unreal.MoviePipelineExecutorJob
        :param manifest_path: Path to the QueueManifest file with the Job parameters
        :type manifest_path: str
        """
        with open(DEFAULT_JOB_TEMPLATE_FILE_PATH) as f:
            self.default_job_template = yaml.safe_load(f)

        self._dependency_collector = DependencyCollector()

        self._open_job: Dict
        self._manifest_path: str

        self._steps: list[JobStep] = []
        self._parameter_values_dict: Dict[Any, Any] = {}
        self._asset_references = AssetReferences()
        self._job_bundle_path: str

        self._create_open_job_from_mrq_job(mrq_job)

    @property
    def name(self):
        """
        Returns the OpenJob name
        """
        return self._open_job.get("name")

    @property
    def job_bundle_path(self):
        """
        Returns the OpenJob job bundle path
        """
        return self._job_bundle_path

    def _create_open_job_from_mrq_job(self, mrq_job: unreal.MoviePipelineExecutorJob) -> None:
        """
        Creates an OpenJob representation from the unreal.MoviePipelineExecutorJob.

        Set the name, build steps, fill parameter values, attachments and build final job bundle.

        :param mrq_job: unreal.MoviePipelineExecutorJob instance
        :type mrq_job: unreal.MoviePipelineExecutorJob
        """

        self._open_job = deepcopy(self.default_job_template)
        shared_settings = mrq_job.preset_overrides.job_shared_settings

        self._open_job["name"] = (
            mrq_job.job_name
            if shared_settings.name == "" or shared_settings.name == "Untitled"
            else shared_settings.name
        )

        self._open_job["description"] = shared_settings.description

        self._save_manifest_file(mrq_job)

        self._build_steps(mrq_job)
        self._open_job["steps"] = [step.as_dict() for step in self._steps]

        self._build_parameter_values_dict(mrq_job)
        self._build_asset_references(mrq_job)

        self._build_job_bundle()

    def _collect_mrq_job_dependencies(self, mrq_job) -> list[str]:
        """
        Collects the dependencies of the Level and LevelSequence that used in MRQ Job.

        Use :class:`deadline.unreal_submitter.unreal_dependency_collector.collector.DependencyCollector` for collecting

        :param mrq_job: unreal.MoviePipelineExecutorJob instance
        :type mrq_job: unreal.MoviePipelineExecutorJob

        :return: List of the dependencies
        :rtype: list[str]
        """
        level_sequence_path = soft_obj_path_to_str(mrq_job.sequence)
        level_sequence_path = os.path.splitext(level_sequence_path)[0]

        level_path = soft_obj_path_to_str(mrq_job.map)
        level_path = os.path.splitext(level_path)[0]

        level_sequence_dependencies = self._dependency_collector.collect(
            level_sequence_path, filter_method=DependencyFilters.dependency_in_game_folder
        )

        level_dependencies = self._dependency_collector.collect(
            level_path, filter_method=DependencyFilters.dependency_in_game_folder
        )

        return level_sequence_dependencies + level_dependencies + [level_sequence_path, level_path]

    def _build_parameter_values_dict(self, mrq_job: unreal.MoviePipelineExecutorJob) -> dict:
        """
        Build parameter values of the OpenJob with the given MRQ Job.
        Extend the built parameter values with OpenJob SharedSettings instance
        (:class:`deadline.unreal_submitter.unreal_open_job.open_job_description.JobSharedSettings`)

        :param mrq_job: unreal.MoviePipelineExecutorJob instance
        :type mrq_job: unreal.MoviePipelineExecutorJob

        :return: Parameter values dictionary
        :rtype: dict
        """

        project_file_path = get_project_file_path()
        project_directory = get_project_directory()

        # Output path
        output_setting = mrq_job.get_configuration().find_setting_by_class(
            unreal.MoviePipelineOutputSetting
        )
        output_path = output_setting.output_directory.path
        # TODO handling unreal substitution templates
        output_path = output_path.replace("{project_dir}", project_directory)

        parameter_values = [
            {
                "name": "LevelPath",
                "value": soft_obj_path_to_str(mrq_job.map),
            },
            {
                "name": "LevelSequencePath",
                "value": soft_obj_path_to_str(mrq_job.sequence),
            },
            {
                "name": "ProjectFilePath",
                "value": project_file_path,
            },
            {
                "name": "ProjectDirectory",
                "value": project_directory,
            },
            {"name": "OutputPath", "value": output_path},
        ]

        shared_parameter_values = JobSharedSettings(
            mrq_job.preset_overrides.job_shared_settings
        ).to_dict()
        parameter_values += shared_parameter_values

        self._parameter_values_dict = dict(parameterValues=parameter_values)

        return self._parameter_values_dict

    def _build_asset_references(self, mrq_job) -> AssetReferences:
        """
        Build asset references of the OpenJob with the given MRQ Job.

        Return :class:`deadline.client.job_bundle.submission.AssetReferences` instance

        :param mrq_job: unreal.MoviePipelineExecutorJob instance
        :type mrq_job: unreal.MoviePipelineExecutorJob

        :return: AssetReferences dataclass instance
        :rtype: :class:`deadline.client.job_bundle.submission.AssetReferences`
        """

        # add dependencies to attachments
        os_dependencies = []
        job_dependencies = self._collect_mrq_job_dependencies(mrq_job)
        for dependency in job_dependencies:
            os_dependency = os_path_from_unreal_path(dependency, with_ext=True)
            if os.path.exists(os_dependency):
                os_dependencies.append(os_dependency)

        self._asset_references.input_filenames.update(os_dependencies)

        step_input_files = []
        for step in self._steps:
            step_input_files.extend(step.get_step_input_files())
        self._asset_references.input_filenames.update(step_input_files)

        project_directory = get_project_directory()

        # add manifest to attachments
        self._asset_references.input_filenames.add(self._manifest_path)

        # add other input files to attachments
        job_input_files = [
            os_abs_from_relative(input_file.file_path)
            for input_file in mrq_job.preset_overrides.job_attachments.input_files.files.paths
        ]
        for input_file in job_input_files:
            if os.path.exists(input_file):
                self._asset_references.input_filenames.add(input_file)

        # required input directories
        for sub_dir in ["Config", "Binaries"]:
            input_directory = os_abs_from_relative(sub_dir)
            if os.path.exists(input_directory):
                self._asset_references.input_directories.add(input_directory)

        # input directories
        job_input_directories = [
            os_abs_from_relative(input_directory.path)
            for input_directory in mrq_job.preset_overrides.job_attachments.input_directories.directories.paths
        ]
        for input_dir in job_input_directories:
            if os.path.exists(input_dir):
                self._asset_references.input_directories.add(input_dir)

        # output directories
        job_output_directories = [
            os_abs_from_relative(output_directory.path)
            for output_directory in mrq_job.preset_overrides.job_attachments.output_directories.directories.paths
        ]
        for output_dir in job_output_directories:
            self._asset_references.input_directories.add(output_dir)

        # TODO handling unreal substitution templates (output directory)
        # TODO Think about it. Maybe we need to move files from Unreal output to Deadline cloud output on worker side
        # or we should override output directory with the output defined in DataAsset
        output_setting = mrq_job.get_configuration().find_setting_by_class(
            unreal.MoviePipelineOutputSetting
        )
        output_path = output_setting.output_directory.path
        output_path = output_path.replace("{project_dir}", project_directory).rstrip("/")
        self._asset_references.output_directories.update([output_path])

        return self._asset_references

    def _build_steps(self, mrq_job) -> list[JobStep]:
        """
        Build OpenJob steps with the given MRQ Job.

        :param mrq_job: unreal.MoviePipelineExecutorJob instance
        :type mrq_job: unreal.MoviePipelineExecutorJob

        :return: List of the :class:`deadline.unreal_submitter.unreal_open_job.job_step.JobStep`
        :rtype: :class:`deadline.unreal_submitter.unreal_open_job.job_step.JobStep`
        """

        preset_overrides: unreal.DeadlineCloudJobPresetStruct = mrq_job.preset_overrides
        unreal.log(f"Preset overrides: {preset_overrides}")

        try:
            self._steps = JobStepFactory.create_steps(
                job_settings=mrq_job.get_configuration().get_all_settings(),
                host_requirements=preset_overrides.host_requirements,
                queue_manifest_path=self._manifest_path,
            )
            return self._steps

        except Exception as e:
            unreal.EditorDialog.show_message(
                "Custom step validate failed", str(e), unreal.AppMsgType.OK
            )
            raise e

    def _build_job_bundle(self) -> str:
        """
        Convert OpenJob to the bundle and write it on the disk.

        :return: OpenJob bundle path
        :rtype: str
        """

        job_bundle_path = create_job_history_bundle_dir("Unreal", self._open_job["name"])
        unreal.log(f"Job bundle path: {job_bundle_path}")

        with open(job_bundle_path + "/template.yaml", "w", encoding="utf8") as f:
            deadline_yaml_dump(self._open_job, f, indent=1)

        with open(job_bundle_path + "/parameter_values.yaml", "w", encoding="utf8") as f:
            deadline_yaml_dump(self._parameter_values_dict, f, indent=1)

        with open(job_bundle_path + "/asset_references.yaml", "w", encoding="utf8") as f:
            deadline_yaml_dump(self._asset_references.to_dict(), f, indent=1)

        self._job_bundle_path = job_bundle_path

        return self._job_bundle_path

    def _save_manifest_file(self, mrq_job):
        new_queue = unreal.MoviePipelineQueue()
        new_job = new_queue.duplicate_job(mrq_job)

        # In duplicated job remove empty auto-detected files since we don't want them to be saved in manifest
        # List of the files is moved to OpenJob attachments
        new_job.preset_overrides.job_attachments.input_files.auto_detected = (
            unreal.DeadlineCloudFileAttachmentsArray()
        )

        (
            duplicated_queue,
            manifest_path,
        ) = unreal.MoviePipelineEditorLibrary.save_queue_to_manifest_file(new_queue)
        manifest_path = unreal.Paths.convert_relative_path_to_full(manifest_path)
        self._manifest_path = manifest_path
