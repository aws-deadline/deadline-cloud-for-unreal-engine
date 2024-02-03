#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import unreal


content_dir = unreal.Paths.project_content_dir()
content_dir = unreal.Paths.convert_relative_path_to_full(content_dir)
project_dir = unreal.Paths.project_dir()
project_dir = unreal.Paths.convert_relative_path_to_full(project_dir)


class DependencyFilters:
    """
    Common class for filtering the found dependencies
    """

    @staticmethod
    def dependency_in_game_folder(dependency_path):
        """
        Check if a given dependency is in the "Game" folder ("Content" in the OS file system)

        :param dependency_path: Unreal Path of the dependency asset, e.g. /Game/Assets/MyAsset
        :type dependency_path: str

        :return: True if the dependency is in the Game folder, False otherwise
        :rtype: bool
        """

        return '/Game/' in str(dependency_path)


def os_path_from_unreal_path(unreal_path, with_ext: bool = False):
    """
    Convert Unreal path to OS path, e.g. /Game/Assets/MyAsset to C:/UE_project/Content/Assets/MyAsset.uasset.

    if parameter with_ext is set to True, tries to get type of the asset by unreal.AssetData and set appropriate extension:

    - type World - .umap
    - other types - .uasset

    If for some reason it can't find asset data (e.g. temporary level's actors don't have asset data), it will set ".uasset"

    :param unreal_path: Unreal Path of the asset, e.g. /Game/Assets/MyAsset
    :param with_ext: if True, build the path with extension (.uasset or .umap), set asterisk "*" otherwise.
    :return: the OS path of the asset
    :rtype: str
    """
    os_path = str(unreal_path).replace('/Game/', content_dir)

    if with_ext:
        asset_data = unreal.EditorAssetLibrary.find_asset_data(unreal_path)
        asset_class_name = asset_data.asset_class_path.asset_name \
            if hasattr(asset_data, 'asset_class_path') \
            else asset_data.asset_class  # support older version of UE python API

        if not asset_class_name.is_none():  # AssetData not found - asset not in the project / on disk
            os_path += '.umap' if asset_class_name == 'World' else '.uasset'
        else:
            os_path += '.uasset'
    else:
        os_path += '.*'

    return os_path


def os_abs_from_relative(os_path):
    if os.path.isabs(os_path):
        return str(os_path)
    return project_dir + os_path


def sync_assets_with_ue_source_control(asset_paths: list[str], sync_description='Sync Assets'):
    """
    Sync the given assets with Unreal Source Control plugin, which handle all connection parameters.

    :param asset_paths: Asset paths to sync
    :type asset_paths: list[str]
    :param sync_description: Sync description for the UI progress bar
    :type sync_description: str
    :return: Sync success result (True/False)
    :rtype: bool
    """
    synced = True

    if not unreal.SourceControl.is_available():
        unreal.log('SourceControl is not available')
        return

    unreal.log('Sync assets: {}'.format(asset_paths))
    if 'IS_RENDER_MODE' not in os.environ:
        with unreal.ScopedSlowTask(len(asset_paths), sync_description) as slow_task:
            slow_task.make_dialog(True)
            for i in range(len(asset_paths)):
                unreal.log('Sync asset: {}'.format(asset_paths[i]))
                synced = unreal.SourceControl.sync_files([asset_paths[i]])
                slow_task.enter_progress_frame(1, asset_paths[i])
    else:
        synced = unreal.SourceControl.sync_files(asset_paths)

    unreal.log(f'Assets synced: {synced}')
    return synced
