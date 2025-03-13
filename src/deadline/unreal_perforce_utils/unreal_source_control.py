#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import unreal
import configparser

from deadline.unreal_logger import get_logger
from deadline.unreal_perforce_utils import exceptions


logger = get_logger()


_SOURCE_CONTROL_INI_RELATIVE_PATH = "Saved/Config/WindowsEditor/SourceControlSettings.ini"
_CONFIGURE_PERFORCE_MESSAGE = (
    "Please, configure Source Control plugin to use Perforce during the submission"
)


def validate_source_control_file(sc_file: str) -> str:
    """
    Check if SourceControlSettings.ini file exists

    :param sc_file: Path to the SourceControlSettings.ini file
    :return: Path to the SourceControlSettings.ini file
    :raises FileNotFoundError: If SourceControlSettings.ini file does not exist
    """

    if not os.path.exists(sc_file):
        raise FileNotFoundError(
            f"SourceControlSettings.ini not found: {sc_file}. "
            f"Check if Unreal Source Control is enabled, relaunch the project and try again."
        )

    return sc_file


def validate_has_section(
    sc_settings: configparser.ConfigParser,
    section_name: str,
) -> configparser.ConfigParser:
    """
    Validate that the given configparser object has the specified section.

    :param sc_settings: A configparser object containing the source control settings.
    :param section_name: The name of the section to validate.
    :return: The configparser object if the section is found.
    :raises KeyError: If the section is not found in the configparser object.
    """

    if not sc_settings.has_section(section_name):
        raise KeyError(f"{section_name} section not found in {_SOURCE_CONTROL_INI_RELATIVE_PATH}")

    return sc_settings


def validate_has_option(
    sc_settings: configparser.ConfigParser,
    section_name: str,
    option_name: str,
) -> configparser.ConfigParser:
    """
    Validate that the given configparser object has the specified option in the specified section.

    :param sc_settings: A configparser object containing the source control settings.
    :param section_name: The name of the section to validate.
    :param option_name: The name of the option to check for within the section.
    :return: The configparser object if the option is found in the specified section.
    :raises KeyError: If the option is not found in the specified section of the configparser object.
    """

    try:
        sc_settings.get(section_name, option_name)
    except configparser.NoOptionError:
        raise KeyError(
            f"{section_name} section does not contain '{option_name}' setting "
            f"in {_SOURCE_CONTROL_INI_RELATIVE_PATH}"
        )

    return sc_settings


def validate_provider(sc_settings: configparser.ConfigParser) -> configparser.ConfigParser:
    """
    Check if SourceControlSettings.ini file Provider is "Perforce"

    :param sc_settings: A configparser object containing the source control settings.
    :return: The configparser object if the settings are valid.
    :raises ValueError: If the settings are not valid.
    """
    section_name = "SourceControl.SourceControlSettings"
    option_name = "Provider"
    validate_has_option(sc_settings, section_name, option_name)

    provider = sc_settings.get(section_name, option_name)
    if provider != "Perforce":
        raise ValueError(
            f"{section_name}.{option_name} = {provider}. "
            f"Can't get Perforce connection settings. {_CONFIGURE_PERFORCE_MESSAGE}"
            f""
        )

    return sc_settings


def validate_perforce_source_control_settings(
    sc_settings: configparser.ConfigParser,
) -> configparser.ConfigParser:
    """
    Check if SourceControlSettings.ini has the valid Perforce connection settings.
    Raises an errors if there are any missing keys or values for Port, User and Workspace

    :param sc_settings: A configparser object containing the source control settings.
    :return: The configparser object if the settings are valid.
    :raises KeyError: If the settings are not valid.
    """

    section_name = "PerforceSourceControl.PerforceSourceControlSettings"
    expected_keys = {"Port", "UserName", "Workspace"}

    missed_keys: set[str] = {
        k for k in expected_keys if not sc_settings.has_option(section_name, k)
    }
    if missed_keys:
        raise KeyError(
            "Some keys are missed in PerforceSourceControl.PerforceSourceControlSettings. "
            f"Expected: {expected_keys}. Actual: {expected_keys - missed_keys}. "
            f"{_CONFIGURE_PERFORCE_MESSAGE}"
        )

    missed_values: set[str] = {k for k in expected_keys if not sc_settings.get(section_name, k)}
    if missed_values:
        raise ValueError(
            f"Some parameters is unfilled in PerforceSourceControl.PerforceSourceControlSettings: "
            f"{missed_values}. "
            f"{_CONFIGURE_PERFORCE_MESSAGE}"
        )

    return sc_settings


def get_connection_settings_from_ue_source_control() -> dict[str, str]:
    """
    Parse /Saved/Config/WindowsEditor/SourceControlSettings.ini file inside project's directory
    and return dictionary with Port, User and Workspace

    :return: P4 connection settings as dictionary (port, user, workspace)
    :rtype: dict[str, str]
    """

    if not unreal.SourceControl.is_available():
        raise exceptions.UnrealSourceControlNotAvailableError(
            f"Unreal Source Control is not available. {_CONFIGURE_PERFORCE_MESSAGE}"
        )

    project_dir = os.path.dirname(
        unreal.Paths.convert_relative_path_to_full(unreal.Paths.get_project_file_path())
    ).replace("\\", "/")

    source_control_ini = f"{project_dir}/{_SOURCE_CONTROL_INI_RELATIVE_PATH}"
    validate_source_control_file(source_control_ini)

    config = configparser.ConfigParser()
    config.read(source_control_ini)

    validate_has_section(config, "SourceControl.SourceControlSettings")
    validate_provider(config)

    perforce_section_name = "PerforceSourceControl.PerforceSourceControlSettings"
    validate_has_section(config, perforce_section_name)
    validate_perforce_source_control_settings(config)

    connection_settings = {
        "port": config.get(perforce_section_name, "Port"),
        "user": config.get(perforce_section_name, "UserName"),
        "workspace": config.get(perforce_section_name, "Workspace"),
    }
    logger.info(f"UE Source Control connection settings for Perforce: {connection_settings}")
    return connection_settings
