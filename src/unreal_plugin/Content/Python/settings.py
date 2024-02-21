# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
import threading
import unreal

import boto3
import deadline.client.config as config

from deadline.client import api
from deadline.client.api import AwsCredentialsType, AwsCredentialsStatus
from deadline.client.config import config_file
from deadline.job_attachments.models import FileConflictResolution


@unreal.ustruct()
class UnrealAwsEntity(unreal.StructBase):
    id = unreal.uproperty(str)
    name = unreal.uproperty(str)

    @staticmethod
    def create(entity_dict, id_field):
        """
        Create a new AwsEntity instance.

        :param entity_dict: A dictionary containing the entity data.
        :type entity_dict: dict
        :param id_field: The name of the field that represents the entity's ID.
        :type id_field: str
        :return: The newly created AwsEntity instance.
        :rtype: AwsEntity
        """
        aws_entity = UnrealAwsEntity()
        aws_entity.id = entity_dict[id_field]
        aws_entity.name = entity_dict["displayName"]
        return aws_entity


# TODO Slava handling config parameter in api calls
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


@unreal.uclass()
class DeadlineCloudDeveloperSettingsImplementation(unreal.DeadlineCloudDeveloperSettings):
    farms_cache_list = unreal.uproperty(unreal.Array(UnrealAwsEntity), meta=dict(Category="Cache"))
    queues_cache_list = unreal.uproperty(unreal.Array(UnrealAwsEntity), meta=dict(Category="Cache"))
    storage_profile_cache_list = unreal.uproperty(
        unreal.Array(UnrealAwsEntity), meta=dict(Category="Cache")
    )

    def _post_init(self):
        self.refresh_from_default_profile()
        self.refresh_state()

    def refresh_from_default_profile(self):
        t = threading.Thread(target=self.__refresh_deadline_settings, daemon=True)
        t.start()

    def __refresh_deadline_settings(self):
        # TODO Slava handle case when user is not logged in
        aws_profile_name = config.get_setting("defaults.aws_profile_name")
        if aws_profile_name in ["(default)", "default", ""]:
            aws_profile_name = "(default)"

        self.work_station_configuration.global_settings.aws_profile = aws_profile_name

        self.work_station_configuration.profile.job_history_dir.path = config.get_setting(
            "settings.job_history_dir"
        ).replace("\\", "/")

        farm_id = config.get_setting("defaults.farm_id")
        farm_entity = self.find_farm_by_id(farm_id)

        if farm_entity is not None:
            self.work_station_configuration.profile.default_farm = farm_entity.name

        queue_id = config.get_setting("defaults.queue_id")
        queue_entity = self.find_queue_by_id(queue_id)
        if queue_entity is not None:
            self.work_station_configuration.farm.default_queue = queue_entity.name

        storage_profile_id = config.get_setting("settings.storage_profile_id")
        storage_profile_entity = self.find_storage_profile_by_id(storage_profile_id)
        if storage_profile_entity is not None:
            self.work_station_configuration.farm.default_storage_profile = (
                storage_profile_entity.name
            )

        self.work_station_configuration.farm.job_attachment_filesystem_options = config.get_setting(
            "defaults.job_attachments_file_system"
        )

        self.work_station_configuration.general.auto_accept_confirmation_prompts = (
            True if config.get_setting("settings.auto_accept") == "true" else False
        )

        self.work_station_configuration.general.conflict_resolution_option = config.get_setting(
            "settings.conflict_resolution"
        )

        self.work_station_configuration.general.current_logging_level = config.get_setting(
            "settings.log_level"
        )

    @unreal.ufunction(ret=unreal.Array(str))
    def get_aws_profiles(self):
        session = boto3.Session()
        aws_profile_names = list(session._session.full_config["profiles"].keys())
        for i in range(len(aws_profile_names)):
            if aws_profile_names[i] in ["default", "(defaults)", ""]:
                aws_profile_names[i] = "(default)"
        return aws_profile_names

    @unreal.ufunction(ret=unreal.Array(str))
    def get_farms(self):
        try:
            response = api.list_farms()
            self.farms_cache_list = [
                UnrealAwsEntity.create(item, "farmId") for item in response["farms"]
            ]
        # TODO Slava
        except Exception:
            return []
        return [farm.name for farm in self.farms_cache_list]

    @unreal.ufunction(ret=unreal.Array(str))
    def get_queues(self):
        default_farm_id = config_file.get_setting("defaults.farm_id")
        if default_farm_id:
            try:
                response = api.list_queues(farmId=default_farm_id)
                self.queues_cache_list = [
                    UnrealAwsEntity.create(item, "queueId") for item in response["queues"]
                ]
            # TODO Slava
            except Exception:
                self.queues_cache_list = []
        else:
            self.queues_cache_list = []
        return [queue.name for queue in self.queues_cache_list]

    @unreal.ufunction(ret=unreal.Array(str))
    def get_storage_profiles(self):
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
                        # TODO Slava remove _get_current_os from here
                        "osFamily": _get_current_os(),
                    }
                )
                self.storage_profile_cache_list = [
                    UnrealAwsEntity.create(item, "storageProfileId") for item in items
                ]
            # TODO Slava
            except Exception:
                self.storage_profile_cache_list = []
            return [storage_profile.name for storage_profile in self.storage_profile_cache_list]
        else:
            self.storage_profile_cache_list = []
        return self.storage_profile_cache_list

    @unreal.ufunction(ret=unreal.Array(str))
    def get_job_attachment_modes(self):
        return ["COPIED", "VIRTUAL"]

    @unreal.ufunction(ret=unreal.Array(str))
    def get_conflict_resolution_options(self):
        return [option.name for option in FileConflictResolution]

    @unreal.ufunction(ret=unreal.Array(str))
    def get_logging_levels(self):
        return ["ERROR", "WARNING", "INFO", "DEBUG"]

    @unreal.ufunction(override=True)
    def refresh_state(self):
        t = threading.Thread(target=self.__refresh_deadline_status, daemon=True)
        t.start()

    def __refresh_deadline_status(self):
        config_parser = config_file.read_config()
        self.work_station_configuration.state.creds_type = api.get_credentials_type(
            config=config_parser
        ).name

        creds_status = api.check_credentials_status(config=config_parser)
        self.work_station_configuration.state.creds_status = creds_status.name

        if creds_status == AwsCredentialsStatus.AUTHENTICATED:
            self.work_station_configuration.state.api_availability = (
                "AUTHORIZED"
                if api.check_deadline_api_available(config=config_parser)
                else "NOT AUTHORIZED"
            )
        else:
            self.work_station_configuration.state.api_availability = "NOT AUTHORIZED"

    @unreal.ufunction(override=True)
    def on_settings_modified(self, property_name):
        """
        TODO refresh config
        1. When we change an "aws profile" we need to pull Job history dir and default farm
        2. When we change "default farm" we need to pull default queue,
           default storage profile, and job attachment fs options
        """
        unreal.log(f"Changed property: {property_name}")

        # This means we need to change default profile
        # If the default profile is changed then we update it in the config first
        # after that we need to save this setting first and read settings for all other values
        if property_name == "AWS_Profile":
            config.set_setting(
                "defaults.aws_profile_name",
                self.work_station_configuration.global_settings.aws_profile,
            )
            self.refresh_from_default_profile()
            return

        if property_name == "DefaultFarm":
            farm = self.find_farm_by_name(self.work_station_configuration.profile.default_farm)
            if farm is not None:
                config.set_setting("defaults.farm_id", farm.id)
            self.refresh_from_default_profile()
            return

        self.save_to_file()

    def find_farm_by_id(self, farm_id):
        _ = self.get_farms()
        farm = next((farm for farm in self.farms_cache_list if farm.id == farm_id), None)
        return farm

    def find_queue_by_id(self, queue_id):
        _ = self.get_queues()
        queue = next((queue for queue in self.queues_cache_list if queue.id == queue_id), None)
        return queue

    def find_storage_profile_by_id(self, storage_profile_id):
        _ = self.get_storage_profiles()
        storage_profile = next(
            (
                storage_profile
                for storage_profile in self.storage_profile_cache_list
                if storage_profile.id == storage_profile_id
            ),
            None,
        )
        return storage_profile

    def find_farm_by_name(self, farm_name):
        # response = api.list_farms()
        farm = next((farm for farm in self.farms_cache_list if farm.name == farm_name), None)
        return farm

    def find_queue_by_name(self, queue_name):
        # default_farm_id = config_file.get_setting("defaults.farm_id")
        # response = api.list_queues(farmId=default_farm_id)
        queue = next((queue for queue in self.queues_cache_list if queue.name == queue_name), None)
        return queue

    def find_storage_by_name(self, storage_profile_name):
        storage_profile = next(
            (item for item in self.storage_profile_cache_list if item.name == storage_profile_name),
            None,
        )
        return storage_profile

    def save_to_file(self):
        config_parser = config_file.read_config()
        config.set_setting(
            "defaults.aws_profile_name",
            self.work_station_configuration.global_settings.aws_profile,
            config=config_parser,
        )

        config.set_setting(
            "settings.job_history_dir",
            self.work_station_configuration.profile.job_history_dir.path,
            config=config_parser,
        )

        farm = self.find_farm_by_name(self.work_station_configuration.profile.default_farm)
        if farm is not None:
            unreal.log(f"Update default farm: {farm.id} -- {farm.name}")
            config.set_setting("defaults.farm_id", farm.id, config=config_parser)

        queue = self.find_queue_by_name(self.work_station_configuration.farm.default_queue)
        if queue is not None:
            unreal.log(f"Update default queue: {queue.id} -- {queue.name}")
            config.set_setting("defaults.queue_id", queue.id, config=config_parser)

        storage_profile = self.find_storage_by_name(
            self.work_station_configuration.farm.default_storage_profile
        )
        if storage_profile is not None:
            unreal.log(
                f"Update default storage profile: {storage_profile.id} "
                f"-- {storage_profile.name}"
            )
            config.set_setting(
                "settings.storage_profile_id", storage_profile.id, config=config_parser
            )

        # farm.job_attachment_filesystem_options (defaults.job_attachments_file_system)
        config.set_setting(
            "defaults.job_attachments_file_system",
            self.work_station_configuration.farm.job_attachment_filesystem_options,
            config=config_parser,
        )

        if self.work_station_configuration.general.auto_accept_confirmation_prompts:
            config.set_setting("settings.auto_accept", "true", config=config_parser)
        else:
            config.set_setting("settings.auto_accept", "false", config=config_parser)

        # general.conflict_resolution_option (settings.conflict_resolution)
        config.set_setting(
            "settings.conflict_resolution",
            self.work_station_configuration.general.conflict_resolution_option,
            config=config_parser,
        )

        # general.current_logging_level
        config.set_setting(
            "settings.log_level",
            self.work_station_configuration.general.current_logging_level,
            config=config_parser,
        )

        config_file.write_config(config_parser)

    @unreal.ufunction(override=True)
    def login(self):
        unreal.log("login")

        def on_pending_authorization(**kwargs):
            if kwargs["credential_type"] == AwsCredentialsType.DEADLINE_CLOUD_MONITOR_LOGIN:
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
            unreal.EditorDialog.show_message(
                "Deadline Cloud", success_message, unreal.AppMsgType.OK, unreal.AppReturnType.OK
            )
            self.refresh_from_default_profile()
            self.refresh_state()

    @unreal.ufunction(override=True)
    def logout(self):
        unreal.log("Deadline Cloud logout")
        api.logout()
        self.refresh_from_default_profile()
        self.refresh_state()
