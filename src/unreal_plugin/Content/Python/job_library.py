# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import re

import unreal

from deadline.unreal_submitter import common
from deadline.unreal_logger import get_logger
from deadline.unreal_submitter.unreal_dependency_collector import (
    DependencyCollector,
    DependencyFilters,
)

from deadline.unreal_submitter.unreal_open_job.unreal_open_job import UnrealOpenJob
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity import OpenJobParameterNames
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step_host_requirements import (
    HostRequirementsHelper,
)

logger = get_logger()


@unreal.uclass()
class DeadlineCloudJobBundleLibraryImplementation(unreal.DeadlineCloudJobBundleLibrary):
    @unreal.ufunction(override=True)
    def get_job_dependencies(self, mrq_job):
        level_sequence_path = common.soft_obj_path_to_str(mrq_job.sequence)
        level_path = common.soft_obj_path_to_str(mrq_job.map)

        level_sequence_path, _ = os.path.splitext(level_sequence_path)
        level_path, _ = os.path.splitext(level_path)

        dependency_collector = DependencyCollector()
        logger.info("Level sequence: " + level_sequence_path)
        logger.info("Level: " + level_path)

        unreal_dependencies = dependency_collector.collect(
            asset_path=level_sequence_path,
            filter_method=DependencyFilters.dependency_in_game_folder,
        )

        unreal_dependencies += dependency_collector.collect(
            asset_path=level_path, filter_method=DependencyFilters.dependency_in_game_folder
        )

        unreal_dependencies += [level_sequence_path, level_path]

        logger.info(
            f"Converted level path: "
            f"{common.os_path_from_unreal_path(level_sequence_path, with_ext=True)}"
        )

        unreal_dependencies = list(set(unreal_dependencies))

        return [common.os_path_from_unreal_path(d, with_ext=True) for d in unreal_dependencies]

    @unreal.ufunction(override=True)
    def validate_mrq_job_parameters(
        self, parameters: list[unreal.ParameterDefinition]
    ) -> list[unreal.ParameterDefinition]:
        conda_packages_param = None
        conda_packages_param_index = 0
        for i, p in enumerate(parameters):
            if p.get_editor_property("Name") == OpenJobParameterNames.CONDA_PACKAGES:
                conda_packages_param = p
                conda_packages_param_index = i
                break

        if not conda_packages_param:
            return parameters

        current_version = UnrealOpenJob.get_current_ue_version()

        conda_packages_value = conda_packages_param.value
        if not conda_packages_value:
            conda_packages_param.value = UnrealOpenJob.normalize_openjd_version_param(
                f"unrealengine={current_version}"
            )
            parameters[conda_packages_param_index] = conda_packages_param
            return parameters

        # Check for unrealengine=x.x pattern
        ue_version_match = re.search(r"unrealengine=(\d+\.\d+)", conda_packages_value)
        if not ue_version_match:
            conda_packages_param.value = UnrealOpenJob.normalize_openjd_version_param(
                f"unrealengine={current_version} " + conda_packages_value
            )

            parameters[conda_packages_param_index] = conda_packages_param
            return parameters

        template_ue_version = ue_version_match.group(1)
        logger.info(f"Template specifies Unreal Engine version: {template_ue_version}")

        # Compare versions
        if not template_ue_version == current_version:
            # replace with current version
            conda_packages_param.value = UnrealOpenJob.normalize_openjd_version_param(
                re.sub(
                    r"unrealengine=\d+\.\d+",
                    f"unrealengine={current_version}",
                    conda_packages_value,
                )
            )
            logger.info(f"Updated Unreal Engine version in conda packages to: {current_version}")
            parameters[conda_packages_param_index] = conda_packages_param

        return parameters

    @unreal.ufunction(override=True)
    def is_amount_requirement_default(self, amount_name) -> bool:
        return HostRequirementsHelper.is_predefined_requirement_by_name("amounts", amount_name)

    @unreal.ufunction(override=True)
    def is_attribute_requirement_default(self, attribute_name) -> bool:
        return HostRequirementsHelper.is_predefined_requirement_by_name(
            "attributes", attribute_name
        )

    @unreal.ufunction(override=True)
    def get_requirement_friendly_name(self, name) -> str:
        return HostRequirementsHelper.get_friendly_name(name)

    @unreal.ufunction(override=True)
    def get_plugins_dependencies(self):
        return [d for d in UnrealOpenJob.get_plugins_references().input_directories]

    @unreal.ufunction(override=True)
    def get_job_initial_state_options(self):
        return ["READY", "SUSPENDED"]

    @unreal.ufunction(override=True)
    def validate_amount_name(self, name) -> str:
        return HostRequirementsHelper.validate_name("amounts", name)

    @unreal.ufunction(override=True)
    def validate_attribute_name(self, name) -> str:
        return HostRequirementsHelper.validate_name("attributes", name)
