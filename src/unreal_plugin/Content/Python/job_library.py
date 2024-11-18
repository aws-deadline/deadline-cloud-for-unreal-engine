# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import unreal

from deadline.unreal_submitter import common
from deadline.unreal_logger import get_logger
from deadline.unreal_submitter.unreal_dependency_collector import (
    DependencyCollector,
    DependencyFilters,
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
    def get_cpu_architectures(self):
        return ["x86_64", "arm64"]

    @unreal.ufunction(override=True)
    def get_operating_systems(self):
        return ["linux", "macos", "windows"]

    @unreal.ufunction(override=True)
    def get_job_initial_state_options(self):
        return ["READY", "SUSPENDED"]
