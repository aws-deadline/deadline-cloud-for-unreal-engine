#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import json
import pprint
import socket
from pathlib import Path

from deadline.unreal_logger import get_logger
from deadline.unreal_perforce_utils import perforce, exceptions


logger = get_logger()


def get_workspace_name(project_name: str) -> str:
    """
    Build and return the workspace name based on the given project name:
    <USERNAME>_<HOST>_<PROJECT_NAME>

    :param project_name: Name of the project

    :return: Workspace name
    :rtype: str
    """

    return f'{os.getlogin()}_{socket.gethostname()}_{project_name}'


def get_workspace_specification_template_from_file(workspace_specification_template_path: str) -> dict:
    """
    Read the given workspace specification template file path and return loaded content

    :param workspace_specification_template_path: Path to the workspace specification template file

    :return: Loaded workspace specification template dictionary
    :rtype: dict
    """

    if not os.path.exists(workspace_specification_template_path):
        raise FileNotFoundError(
            f'The workspace specification template does not exist: {workspace_specification_template_path}'
        )

    logger.info(f'Getting workspace specification template from file: {workspace_specification_template_path} ...')
    with open(workspace_specification_template_path, 'r') as f:
        return json.load(f)


def create_perforce_workspace_from_template(
        specification_template: dict,
        project_name: str,
        overridden_workspace_root: str = None,
) -> perforce.PerforceClient:
    """
    Creates Perforce workspace from the template

    :param specification_template: Workspace specification template dictionary
    :param project_name: Name of the project to build workspace name
    :param overridden_workspace_root: Workspace local path root (Optional, root from template is used by default)

    :return: :class:`p4utilsforunreal.perforce.PerforceClient` instance
    :rtype: :class:`p4utilsforunreal.perforce.PerforceClient`
    """

    logger.info(f'Creating perforce workspace from template: \n'
          f'Specification template: {specification_template}\n'
          f'Project: {project_name}\n'
          f'Overridden workspace root: {overridden_workspace_root}')

    workspace_name = get_workspace_name(project_name=project_name)

    specification_template_str = json.dumps(specification_template)
    specification_str = specification_template_str.replace('{workspace_name}', workspace_name)
    specification = json.loads(specification_str)

    if overridden_workspace_root:
        specification['Root'] = overridden_workspace_root
    else:
        specification['Root'] = f"{os.getenv('P4_CLIENTS_DIRECTORY', os.getcwd())}/{workspace_name}"

    logger.info(f'Specification: {specification}')

    perforce_client = perforce.PerforceClient(
        connection=perforce.PerforceConnection(),
        name=workspace_name,
        specification=specification
    )

    perforce_client.save()

    logger.info('Perforce workspace created!')
    logger.info(pprint.pformat(perforce_client.spec))

    return perforce_client


def initial_workspace_sync(
        workspace: perforce.PerforceClient,
        unreal_project_relative_path: str,
        changelist: int = None,
) -> None:
    """
    Do initial workspace synchronization:

    - .uproject file
    - Binaries folder
    - Config folder
    - Plugins folder

    :param workspace: p4utilsforunreal.perforce.PerforceClient instance
    :param unreal_project_relative_path: path to the .uproject file relative to the workspace root
    """

    logger.info('Workspace initial synchronizing ...')

    workspace_root = workspace.spec['Root'].replace('\\', '/')

    paths_to_sync = [f'{workspace_root}/{unreal_project_relative_path}']

    unreal_project_directory = os.path.dirname(unreal_project_relative_path)

    for folder in ['Binaries', 'Config', 'Plugins']:
        tokens = filter(
            lambda t: t not in [None, ''],
            [workspace_root, unreal_project_directory, folder, '...']
        )
        paths_to_sync.append('/'.join(tokens))

    logger.info(f'Paths to sync: {paths_to_sync}')

    for path in paths_to_sync:
        try:
            workspace.sync(path, changelist=changelist, force=True)
        except Exception as e:
            logger.info(f'Initial workspace sync exception: {str(e)}')


def configure_project_source_control_settings(workspace: perforce.PerforceClient, unreal_project_relative_path: str):
    """
    Configure SourceControl settings (Saved/Config/WindowsEditor/SourceControlSettings.ini)
    with the current P4 connection settings

    :param workspace: p4utilsforunreal.perforce.PerforceClient instance
    :param unreal_project_relative_path: path to the .uproject file relative to the workspace root
    """

    logger.info('Configuring Unreal project SourceControl settings ...')
    unreal_project_directory = os.path.dirname(unreal_project_relative_path)
    tokens = filter(
        lambda t: t not in [None, ''],
        [
            workspace.spec['Root'],
            unreal_project_directory,
            'Saved/Config/WindowsEditor/SourceControlSettings.ini'
        ]
    )
    source_control_settings_path = '/'.join(tokens)
    os.makedirs(os.path.dirname(source_control_settings_path), exist_ok=True)
    logger.info(f'Source Control settings file: {source_control_settings_path}')

    source_control_settings_lines = [
        '[PerforceSourceControl.PerforceSourceControlSettings]\n',
        'UseP4Config = False\n',
        f'Port = {workspace.p4.port}\n',
        f'UserName = {workspace.p4.user}\n',
        f'Workspace = {workspace.p4.client}\n\n',

        '[SourceControl.SourceControlSettings]\n',
        'Provider = Perforce\n'

    ]
    logger.info('source control settings:\n')
    for setting_line in source_control_settings_lines:
        logger.info(setting_line)

    with open(source_control_settings_path, 'w+') as f:
        for setting_line in source_control_settings_lines:
            f.write(setting_line)


def create_workspace(
        perforce_specification_template_path: str,
        unreal_project_relative_path: str,
        unreal_project_name: str = None,
        overridden_workspace_root: str = None,
        changelist: int = None
):
    """
    Create P4 workspace and execute next steps:

    - :meth:`deadline.unreal_perforce_utils.app.get_workspace_specification_template_from_file()`
    - :meth:`deadline.unreal_perforce_utils.app.initial_workspace_sync()`
    - :meth:`deadline.unreal_perforce_utils.app.configure_project_source_control_settings()`

    :param perforce_specification_template_path: Path to the perforce specification template file to read specification from
    :param unreal_project_relative_path: path to the .uproject file relative to the workspace root
    :param overridden_workspace_root: Workspace local path root (Optional, root from template is used by default)
    """

    logger.info('Creating workspace with the following settings:\n'
                f'Specification template: {perforce_specification_template_path}\n'
                f'Unreal project relative path: {unreal_project_relative_path}\n'
                f'Overridden workspace root: {overridden_workspace_root}\n'
                f'Changelist: {changelist}')

    workspace_specification_template = get_workspace_specification_template_from_file(
        workspace_specification_template_path=perforce_specification_template_path
    )

    workspace = create_perforce_workspace_from_template(
        specification_template=workspace_specification_template,
        project_name=unreal_project_name or Path(unreal_project_relative_path).stem,
        overridden_workspace_root=overridden_workspace_root
    )

    initial_workspace_sync(
        workspace=workspace,
        unreal_project_relative_path=unreal_project_relative_path,
        changelist=changelist
    )

    configure_project_source_control_settings(
        workspace=workspace,
        unreal_project_relative_path=unreal_project_relative_path
    )


def delete_workspace(workspace_name: str = None, project_name: str = None):
    """
    Clear workspace files that are in depot and delete the workspace

    :param workspace_name: Name of the workspace to delete
    :param project_name: Name of the Unreal Project to generate a workspace name if not provided
    """

    logger.info(f'Deleting workspace for the project: {project_name}')

    if workspace_name:
        workspace_name_to_delete = workspace_name
    elif project_name:
        workspace_name_to_delete = get_workspace_name(project_name)
    else:
        raise exceptions.PerforceWorkspaceNotFoundError(
            f"Can't get workspace name to delete "
            f"since no workspace name or Unreal project name is provided"
        )

    p4 = perforce.PerforceConnection().p4

    last_exception = None

    workspace_root = p4.fetch_client(workspace_name_to_delete).get('Root').replace('\\', '/')
    if workspace_root and os.path.exists(workspace_root):
        try:
            logger.info('Reverting changes in default changelist')
            p4.client = workspace_name_to_delete
            p4.run('revert', '-c', 'default', workspace_root + '/...')
        except Exception as e:
            if 'file(s) not opened on this client' in str(e):
                logger.info('Nothing to revert')
                pass
            else:
                logger.info(f'Error handled while reverting changes: {e}')
                last_exception = e
        try:
            logger.info(f'Clearing workspace root: {workspace_root}')
            p4.client = workspace_name_to_delete
            p4.run('sync', '-f', workspace_root + '/...#0')
        except Exception as e:
            if 'file(s) up-to-date' in str(e):
                logger.info('Nothing to clear')
            else:
                logger.info(f'Error handled while clearing workspace: {e}')
                last_exception = e

    try:
        logger.info(f'Deleting workspace: {workspace_name_to_delete}')
        p4.run('client', '-d', '-f', workspace_name_to_delete)
    except Exception as e:
        logger.info(f'Error handled while deleting workspace: {e}')
        last_exception = e

    if last_exception and isinstance(last_exception, Exception):
        raise last_exception
