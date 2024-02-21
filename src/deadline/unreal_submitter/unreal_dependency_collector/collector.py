#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import unreal
from typing import Callable, Optional

from .common import os_path_from_unreal_path
from .dependency_search_options import DependencySearchOptions

asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()


class DependencyCollector:
    """
    A helper class to collect all dependencies of the given unreal asset (Level, LevelSequence, etc.).
    Execute recursive collecting on the newly found dependency  until not found any other.

    For example, we want to collect dependencies of LevelSequence:
    1. LevelSequence depends on Level and Cube
    2. Level depends on StatueSet
    3. StatueSet depends on HorseAsset, RockAsset
    Output list will be: [Level, Cube, StatueSet, HorseAsset, RockAsset]
    """

    def __init__(self):
        self._collected_dependencies = list()

    def collect(
        self,
        asset_path: str,
        dependency_options=DependencySearchOptions(),
        filter_method: Optional[Callable] = None,
        on_found_dependency_callback: Optional[Callable] = None,
    ):
        """
        Collect all dependencies recursively of the given unreal asset.

        :param asset_path: Unreal path of the asset to find dependencies, e.g. /Game/Sequences/MyLevelSequence
        :type asset_path: str
        :param dependency_options: Dataclass containing options for search dependency
        :type dependency_options: DependencySearchOptions
        :param filter_method: Method used to filter the found dependencies, for example, dependencies only in Game(Content) folder
        :type filter_method: typing.Callable, optional
        :param on_found_dependency_callback: Method used to invoke some operations on found dependencies list, for example sync them from VCS
        :type on_found_dependency_callback: typing.Callable, optional

        :return: List of the collected dependencies
        :rtype: list
        """
        self._collected_dependencies.clear()

        udependency_options = unreal.AssetRegistryDependencyOptions(**dependency_options.as_dict())

        source_control_available = unreal.SourceControl.is_available()
        unreal.log(
            "DependencyCollector: Source control is available: {}".format(source_control_available)
        )

        if source_control_available:
            if not unreal.EditorAssetLibrary.does_asset_exist(asset_path):
                os_asset_path = os_path_from_unreal_path(asset_path) + ".*"
                unreal.SourceControl.sync_file(os_asset_path)
                unreal.AssetRegistryHelpers().get_asset_registry().scan_modified_asset_files(
                    [asset_path]
                )
                unreal.AssetRegistryHelpers().get_asset_registry().scan_paths_synchronous(
                    [asset_path], True, True
                )

        dependencies = self._get_dependencies(
            asset_path=asset_path,
            udependency_options=udependency_options,
            filter_method=filter_method,
            on_found_dependency_callback=on_found_dependency_callback,
        )

        return dependencies

    def _get_dependencies(
        self,
        asset_path: str,
        udependency_options: unreal.AssetRegistryDependencyOptions,
        filter_method: Optional[Callable] = None,
        on_found_dependency_callback: Optional[Callable] = None,
    ):
        """
        Inner method that gets called recursively and execute the main collecting process

        :param asset_path: Unreal path of the asset to find dependencies, e.g. /Game/Sequences/MyLevelSequence
        :type asset_path: str
        :param udependency_options: Asset Registry Dependency Options (https://docs.unrealengine.com/5.2/en-US/PythonAPI/class/AssetRegistryDependencyOptions.html)
        :type udependency_options: unreal.AssetRegistryDependencyOptions
        :param filter_method: Method used to filter the found dependencies, for example, dependencies only in Game(Content) folder
        :type filter_method: typing.Callable, optional
        :param on_found_dependency_callback: Method used to invoke some operations on found dependencies list, for example sync them from VCS
        :type on_found_dependency_callback: typing.Callable, optional

        :return: List of dependencies
        :rtype: list
        """

        dependencies_raw = asset_registry.get_dependencies(
            package_name=asset_path, dependency_options=udependency_options
        )

        dependencies = list()
        if dependencies_raw:
            for dependency_raw in dependencies_raw:
                does_confirm_filter = filter_method(dependency_raw) if filter_method else True
                is_not_collected = dependency_raw not in self._collected_dependencies

                if does_confirm_filter and is_not_collected:
                    dependencies.append(dependency_raw)

        if dependencies:
            self._collected_dependencies.extend(dependencies)

        if on_found_dependency_callback:
            unreal.log(
                f"Execute callable {on_found_dependency_callback.__name__} on the dependencies"
            )
            on_found_dependency_callback(dependencies)

        unreal.AssetRegistryHelpers().get_asset_registry().scan_modified_asset_files(dependencies)
        unreal.AssetRegistryHelpers().get_asset_registry().scan_paths_synchronous(
            dependencies, True, True
        )

        for dependency in dependencies:
            self._get_dependencies(
                dependency, udependency_options, filter_method, on_found_dependency_callback
            )

        return [str(d) for d in self._collected_dependencies]
