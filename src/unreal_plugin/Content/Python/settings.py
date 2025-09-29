# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
import unreal
from typing import Any, Tuple
import threading
from botocore.client import BaseClient
import boto3
import deadline.client.config as config

from deadline.client import api
from deadline.client.api import AwsCredentialsSource, AwsAuthenticationStatus, precache_clients
from deadline.client.config import config_file
from deadline.job_attachments.models import FileConflictResolution

from deadline.unreal_logger import get_logger


logger = get_logger()


def create_aws_entity(entity_descriptor: dict[str, Any], id_field: str) -> unreal.UnrealAwsEntity:
    """
    Create and return instance of UnrealAwsEntity

    :param entity_descriptor: Dictionary descriptor of the entity
    :type entity_descriptor: dict[str, Any]
    :param id_field: ID key name of the entity property to get from descriptor and store
                     in UnrealAwsEntity.id
    :type id_field: str
    :return: UnrealAwsEntity object
    :rtype: unreal.UnrealAwsEntity
    """

    aws_entity = unreal.UnrealAwsEntity()
    aws_entity.id = entity_descriptor[id_field]
    aws_entity.name = entity_descriptor["displayName"]
    return aws_entity


# TODO handling config parameter in api calls
def _get_current_os() -> str:
    """
    Get a string specifying what the OS is, following the format the Deadline storage profile API expects.
    """
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform.startswith("darwin"):
        return "macos"
    if sys.platform.startswith("win"):
        return "windows"
    return "Unknown"


def background_init_s3_client():
    """
    Initialize cache an S3 client based on the current deadline configuration
    within the deadline cloud library
    """
    logger.info("INIT DEADLINE CLOUD")
    try:
        deadline = api.get_boto3_client("deadline")
        logger.info("Got deadline client successfully")
    except Exception as e:
        logger.error(f"Failed to get deadline client: {e}")
        return None

    result_container: dict[str, Tuple[BaseClient, BaseClient]] = {}

    def init_s3_client():
        try:
            logger.info("INITIALIZING S3 CLIENT")
            result = precache_clients(deadline=deadline)
            result_container["result"] = result
            logger.info("DONE INITIALIZING S3 CLIENT")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")

    thread = threading.Thread(target=init_s3_client, daemon=True, name="S3ClientInit")
    thread.start()
    thread.result_container = result_container  # type: ignore[attr-defined]
    return thread


def on_farm_queue_update():
    """
    Perform updates based on a change in farm or queue
    """
    background_init_s3_client()


@unreal.uclass()
class DeadlineCloudSettingsLibraryImplementation(unreal.DeadlineCloudSettingsLibrary):

    def _post_init(self):
        self.init_from_python()

    @unreal.ufunction(override=True)
    def get_aws_string_config_setting(self, setting_name: str) -> str:
        try:
            result = config.get_setting(setting_name)
            logger.info(f"try get aws string config setting {setting_name} type: {type(result)}")
            logger.info(f"try get aws string config setting {setting_name} value: {result}")

            if isinstance(result, list):
                logger.warning(f"{setting_name} is a list: {result}")
                result = result[0]

            return str(result)

        except Exception as e:
            logger.error(f"Error in get_aws_string_config_setting: {str(e)}")
            return ""

    @unreal.ufunction(override=True)
    def set_aws_string_config_setting(self, setting_name: str, setting_value: str) -> None:
        try:
            current_setting = config.get_setting(setting_name)
            if setting_value != current_setting:
                logger.info(f"set aws string config setting {setting_name} value: {setting_value}")
                config.set_setting(setting_name, setting_value)
            else:
                logger.info(f"{setting_name} unchanged (already {setting_value}), skipping update")
        except Exception as e:
            logger.error(f"Error in set_aws_string_config_setting: {str(e)}")

    @unreal.ufunction(override=True)
    def get_farms(self) -> list:
        try:
            response = api.list_farms()
            farms_list = [create_aws_entity(item, "farmId") for item in response["farms"]]
        # TODO: do proper exception handling
        except Exception:
            return []
        return farms_list

    @unreal.ufunction(override=True)
    def get_queues(self) -> list:
        default_farm_id = config_file.get_setting("defaults.farm_id")
        if default_farm_id:
            try:
                response = api.list_queues(farmId=default_farm_id)
                queues_list = [create_aws_entity(item, "queueId") for item in response["queues"]]
            # TODO: do proper exception handling
            except Exception:
                queues_list = []
        else:
            queues_list = []
        return queues_list

    @unreal.ufunction(override=True)
    def get_storage_profiles(self) -> list:
        default_farm_id = config_file.get_setting("defaults.farm_id")
        default_queue_id = config_file.get_setting("defaults.queue_id")
        if default_farm_id and default_queue_id:
            try:
                response = api.list_storage_profiles_for_queue(
                    farmId=default_farm_id, queueId=default_queue_id
                )
                items = response.get("storageProfiles", [])
                items.append(
                    {
                        "storageProfileId": "",
                        "displayName": "<none selected>",
                        # TODO remove _get_current_os from here
                        "osFamily": _get_current_os(),
                    }
                )
                storage_profile_list = [
                    create_aws_entity(item, "storageProfileId") for item in items
                ]
            # TODO: do proper exception handling
            except Exception:
                storage_profile_list = []
            return storage_profile_list
        else:
            storage_profile_list = []
        return storage_profile_list

    @unreal.ufunction(override=True)
    def get_api_status(self) -> unreal.DeadlineCloudStatus:
        config_parser = config_file.read_config()
        state = unreal.DeadlineCloudStatus()
        state.creds_type = api.get_credentials_source(config=config_parser).name

        creds_status = api.check_authentication_status(config=config_parser)
        state.creds_status = creds_status.name

        if creds_status == AwsAuthenticationStatus.AUTHENTICATED:
            state.api_availability = (
                "AUTHORIZED"
                if api.check_deadline_api_available(config=config_parser)
                else "NOT AUTHORIZED"
            )
        else:
            state.api_availability = "NOT AUTHORIZED"

        return state

    @unreal.ufunction(override=True)
    def login(self) -> bool:
        logger.info("login")

        def on_pending_authorization(**kwargs):
            if kwargs["credentials_source"] == AwsCredentialsSource.DEADLINE_CLOUD_MONITOR_LOGIN:
                unreal.EditorDialog.show_message(
                    "Deadline Cloud",
                    "Opening Deadline Cloud Monitor. Please login before returning here.",
                    unreal.AppMsgType.OK,
                    unreal.AppReturnType.OK,
                )

        def on_cancellation_check():
            return False

        success_message = api.login(
            on_pending_authorization,
            on_cancellation_check,
            config=None,
        )
        if success_message:
            on_farm_queue_update()

            unreal.EditorDialog.show_message(
                "Deadline Cloud", success_message, unreal.AppMsgType.OK, unreal.AppReturnType.OK
            )
            return True

        return False

    @unreal.ufunction(override=True)
    def logout(self) -> None:
        logger.info("Deadline Cloud logout")
        api.logout()

    @unreal.ufunction(override=True)
    def get_aws_profiles(self) -> list:
        session = boto3.Session()
        aws_profile_names = list(session._session.full_config["profiles"].keys())
        for i in range(len(aws_profile_names)):
            if aws_profile_names[i] in ["default", "(defaults)", ""]:
                aws_profile_names[i] = "(default)"
        return aws_profile_names

    @unreal.ufunction(override=True)
    def get_conflict_resolution_options(self) -> list:
        return [option.name for option in FileConflictResolution]

    @unreal.ufunction(override=True)
    def get_job_attachment_modes(self) -> list:
        return ["COPIED", "VIRTUAL"]

    @unreal.ufunction(override=True)
    def get_logging_levels(self) -> list:
        return ["ERROR", "WARNING", "INFO", "DEBUG"]

    @staticmethod
    def find_entity_by_name(name, objects_list: unreal.UnrealAwsEntity):
        result_object = next(
            (result_object for result_object in objects_list if result_object.name == name), None
        )
        return result_object

    @unreal.ufunction(override=True)
    def save_to_aws_config(
        self,
        settings: unreal.DeadlineCloudPluginSettings,
        cache: unreal.DeadlineCloudPluginSettingsCache,
    ) -> None:
        config_parser = config_file.read_config()
        config.set_setting(
            "defaults.aws_profile_name",
            settings.global_settings.aws_profile,
            config=config_parser,
        )

        config.set_setting(
            "settings.job_history_dir",
            settings.profile.job_history_dir.path,
            config=config_parser,
        )

        farm_queue_update = False

        farm_id = config.get_setting("defaults.farm_id")
        farm = self.find_entity_by_name(settings.profile.default_farm, cache.farms_cache_list)
        if farm is not None:
            logger.info(f"Update default farm: {farm.id} -- {farm.name}")
            config.set_setting("defaults.farm_id", farm.id, config=config_parser)
            if farm.id != farm_id:
                farm_queue_update = True

        queue_id = config.get_setting("defaults.queue_id")
        queue = self.find_entity_by_name(settings.farm.default_queue, cache.queues_cache_list)
        if queue is not None:
            logger.info(f"Update default queue: {queue.id} -- {queue.name}")
            config.set_setting("defaults.queue_id", queue.id, config=config_parser)
            if queue.id != queue_id:
                farm_queue_update = True

        storage_profile = self.find_entity_by_name(
            settings.farm.default_storage_profile, cache.storage_profiles_cache_list
        )

        if storage_profile is not None:
            logger.info(
                f"Update default storage profile: {storage_profile.id} "
                f"-- {storage_profile.name}"
            )
            config.set_setting(
                "settings.storage_profile_id", storage_profile.id, config=config_parser
            )

        # farm.job_attachment_filesystem_options (defaults.job_attachments_file_system)
        config.set_setting(
            "defaults.job_attachments_file_system",
            settings.farm.job_attachment_filesystem_options,
            config=config_parser,
        )

        if settings.general.auto_accept_confirmation_prompts:
            config.set_setting("settings.auto_accept", "true", config=config_parser)
        else:
            config.set_setting("settings.auto_accept", "false", config=config_parser)

        # general.conflict_resolution_option (settings.conflict_resolution)
        config.set_setting(
            "settings.conflict_resolution",
            settings.general.conflict_resolution_option,
            config=config_parser,
        )

        # general.current_logging_level
        config.set_setting(
            "settings.log_level",
            settings.general.current_logging_level,
            config=config_parser,
        )

        config_file.write_config(config_parser)

        if farm_queue_update:
            on_farm_queue_update()
