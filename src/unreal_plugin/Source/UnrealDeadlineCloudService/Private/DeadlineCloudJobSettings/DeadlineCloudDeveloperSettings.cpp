// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.


#include "DeadlineCloudJobSettings/DeadlineCloudDeveloperSettings.h"
#include "DeadlineCloudJobSettings/DeadlineCloudRenderJob.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJob.h"


namespace DeadlineSettingsKeys
{
    const FString AwsProfileName = TEXT("defaults.aws_profile_name");
    const FString FarmId = TEXT("defaults.farm_id");
    const FString QueueId = TEXT("defaults.queue_id");
    const FString StorageProfileId = TEXT("settings.storage_profile_id");
    const FString JobHistoryDir = TEXT("settings.job_history_dir");
    const FString JobAttachmentsFileSystem = TEXT("defaults.job_attachments_file_system");
    const FString AutoAccept = TEXT("settings.auto_accept");
    const FString ConflictResolution = TEXT("settings.conflict_resolution");
    const FString LogLevel = TEXT("settings.log_level");
}

UDeadlineCloudDeveloperSettings::UDeadlineCloudDeveloperSettings()
{
}

UDeadlineCloudRenderJob* UDeadlineCloudDeveloperSettings::GetDefaultJobPreset()
{
	if (auto Settings = UDeadlineCloudDeveloperSettings::Get())
	{
		return Settings->DefaultJobPreset.LoadSynchronous();
	}

	return nullptr;
}

void UDeadlineCloudDeveloperSettings::SetDefaultJobPreset(UDeadlineCloudRenderJob* NewJobPreset)
{
	if (auto Settings = UDeadlineCloudDeveloperSettings::GetMutable())
	{
		Settings->DefaultJobPreset = NewJobPreset;
		Settings->SaveConfig();
	}
}

void UDeadlineCloudDeveloperSettings::LoadMRQJobPresetCache(UMoviePipelineDeadlineCloudExecutorJob* MRQJob)
{
	if (auto Settings = UDeadlineCloudDeveloperSettings::GetMutable())
	{
		// If the user changed the default preset, we don't have anything to load
		if (Settings->JobPresetCache.LastJobPreset != Settings->DefaultJobPreset)
		{
			Settings->JobPresetCache.LastJobPreset = Settings->DefaultJobPreset;
			return;
		}

		// If the MRQ job is not using the default preset, we don't load anything
		if (MRQJob->JobPreset != Settings->DefaultJobPreset)
		{
			return;
		}

		MRQJob->PresetOverrides = Settings->JobPresetCache.LastPresetOverrides;
		// copy overrides if parameter exists in current preset, maybe some parameters were removed from previous cache save
		for (const auto& CachedParam : Settings->JobPresetCache.LastJobTemplateOverrides.Parameters)
		{
			for (auto& CurrentParam : MRQJob->JobTemplateOverrides.Parameters)
			{
				if (CachedParam.Name == CurrentParam.Name)
				{
					CurrentParam.Value = CachedParam.Value;
					break;
				}
			}
		}

		for (const auto& CachedStepParam : Settings->JobPresetCache.LastJobTemplateOverrides.StepsOverrides)
		{
			for (auto& CurrentStepParam : MRQJob->JobTemplateOverrides.StepsOverrides)
			{
				if (CachedStepParam.Name == CurrentStepParam.Name)
				{
					CurrentStepParam.CopyParametersValuesFrom(CachedStepParam);
					break;
				}
			}
		}

		for (const auto& CachedEnvParam : Settings->JobPresetCache.LastJobTemplateOverrides.EnvironmentsOverrides)
		{
			for (auto& CurrentEnvParam : MRQJob->JobTemplateOverrides.EnvironmentsOverrides)
			{
				if (CachedEnvParam.Name == CurrentEnvParam.Name)
				{
					CurrentEnvParam.CopyParametersValuesFrom(CachedEnvParam);
					break;
				}
			}
		}
	}
}

void UDeadlineCloudDeveloperSettings::SaveMRQJobPresetCache(const UMoviePipelineDeadlineCloudExecutorJob* MRQJob)
{
	if (auto Settings = UDeadlineCloudDeveloperSettings::GetMutable())
	{
		if (Settings->JobPresetCache.LastJobPreset != Settings->DefaultJobPreset)
		{
			Settings->JobPresetCache.LastJobPreset = Settings->DefaultJobPreset;
		}

		// If the MRQ job is not using the default preset, we don't save anything
		if (MRQJob->JobPreset != Settings->DefaultJobPreset)
		{
			return;
		}

		Settings->JobPresetCache.LastPresetOverrides = MRQJob->PresetOverrides;
		Settings->JobPresetCache.LastJobTemplateOverrides = MRQJob->JobTemplateOverrides;
		Settings->SaveConfig();
	}
}

TArray<FString> UDeadlineCloudDeveloperSettings::GetFarmsList()
{
	UpdateFarmsCacheList();

	TArray<FString> Farms;
	for (const auto& Farm : WorkStationConfigurationCache.FarmsCacheList)
	{
		Farms.Add(Farm.Name);
	}

	return Farms;
}

TArray<FString> UDeadlineCloudDeveloperSettings::GetAWSProfilesList()
{
	TArray<FString> AWSProfiles;
	if (auto Library = UDeadlineCloudSettingsLibrary::Get())
	{
		AWSProfiles = Library->GetAWSProfiles();
	}

	return AWSProfiles;
}

TArray<FString> UDeadlineCloudDeveloperSettings::GetLoggingLevels()
{
	TArray<FString> LoggingLevels;
	if (auto Library = UDeadlineCloudSettingsLibrary::Get())
	{
		LoggingLevels = Library->GetLoggingLevels();
	}

	return LoggingLevels;
}

TArray<FString> UDeadlineCloudDeveloperSettings::GetConflictResolutionOptions()
{
	TArray<FString> ConflictResolutionOptions;
	if (auto Library = UDeadlineCloudSettingsLibrary::Get())
	{
		ConflictResolutionOptions = Library->GetConflictResolutionOptions();
	}

	return ConflictResolutionOptions;
}

TArray<FString> UDeadlineCloudDeveloperSettings::GetStorageProfilesList()
{
	UpdateStorageProfilesCacheList();

	TArray<FString> StorageProfiles;
	for (const auto& StorageProfile : WorkStationConfigurationCache.StorageProfilesCacheList)
	{
		StorageProfiles.Add(StorageProfile.Name);
	}

	return StorageProfiles;
}

TArray<FString> UDeadlineCloudDeveloperSettings::GetJobAttachmentModes()
{
	TArray<FString> JobAttachmentModes;
	if (auto Library = UDeadlineCloudSettingsLibrary::Get())
	{
		JobAttachmentModes = Library->GetJobAttachmentModes();
	}

	return JobAttachmentModes;
}

TArray<FString> UDeadlineCloudDeveloperSettings::GetQueuesList()
{
	UpdateQueuesCacheList();

	TArray<FString> Queues;
	for (const auto& Queue : WorkStationConfigurationCache.QueuesCacheList)
	{
		Queues.Add(Queue.Name);
	}
	return Queues;
}

FText UDeadlineCloudDeveloperSettings::GetSectionText() const
{
    return NSLOCTEXT("DeadlineCloudDeveloperSettings", "DeadlineCloudDeveloperSettingsSection", "Deadline Cloud");
}

FName UDeadlineCloudDeveloperSettings::GetSectionName() const
{
    return TEXT("DeadlineCloud");
}

void UDeadlineCloudDeveloperSettings::PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent)
{
	Super::PostEditChangeProperty(PropertyChangedEvent);

	if (PropertyChangedEvent.Property)
	{
		if (PropertyChangedEvent.Property->GetFName() == GET_MEMBER_NAME_CHECKED(FDeadlineCloudGlobalPluginSettings, AWS_Profile))
		{
			if (auto Library = UDeadlineCloudSettingsLibrary::Get())
			{
				Library->SetAWSStringConfigSetting(DeadlineSettingsKeys::AwsProfileName, WorkStationConfiguration.GlobalSettings.AWS_Profile);
			}

			RefreshFromDefaultProfile();
		}
		else if (PropertyChangedEvent.Property->GetFName() == GET_MEMBER_NAME_CHECKED(FDeadlineCloudProfilePluginSettings, DefaultFarm))
		{
			FUnrealAwsEntity Farm = FindFarmByName(WorkStationConfiguration.Profile.DefaultFarm, true);
			if (auto Library = UDeadlineCloudSettingsLibrary::Get())
			{
				Library->SetAWSStringConfigSetting(DeadlineSettingsKeys::FarmId, Farm.Id);
			}

			RefreshFromDefaultProfile();
		}
		else
		{
			SaveToFile();
		}
	}
}

void UDeadlineCloudDeveloperSettings::PostInitProperties()
{
	Super::PostInitProperties();
}

void UDeadlineCloudDeveloperSettings::Refresh()
{
    RefreshFromDefaultProfile();
    RefreshState();
}

void UDeadlineCloudDeveloperSettings::RefreshState()
{
	Async(EAsyncExecution::Thread, [this]()
		{
			RefreshStateInternal();
		});
}

void UDeadlineCloudDeveloperSettings::RefreshStateInternal()
{
	if (auto Library = UDeadlineCloudSettingsLibrary::Get())
	{
		WorkStationConfiguration.State = Library->GetApiStatus();
	}
}

void UDeadlineCloudDeveloperSettings::RefreshFromDefaultProfile()
{
	Async(EAsyncExecution::Thread, [this]()
		{
			RefreshFromDefaultProfileInternal();
		});
}

void UDeadlineCloudDeveloperSettings::RefreshFromDefaultProfileInternal()
{
    if (auto Library = UDeadlineCloudSettingsLibrary::Get())
    {
		FString AWSProfileName = Library->GetAWSStringConfigSetting(DeadlineSettingsKeys::AwsProfileName);
        if (AWSProfileName.IsEmpty() || AWSProfileName == TEXT("default") || AWSProfileName == TEXT("(default)"))
        {
            AWSProfileName = TEXT("(default)");
        }

		WorkStationConfiguration.GlobalSettings.AWS_Profile = AWSProfileName;

		FString JobHistoryDir = Library->GetAWSStringConfigSetting(DeadlineSettingsKeys::JobHistoryDir);
        JobHistoryDir.ReplaceInline(TEXT("\\"), TEXT("/"));

		WorkStationConfiguration.Profile.JobHistoryDir.Path = JobHistoryDir;

        FString FarmId = Library->GetAWSStringConfigSetting(DeadlineSettingsKeys::FarmId);

		FUnrealAwsEntity Farm = FindFarmById(FarmId, true);
		if (Farm.IsValid())
		{
			WorkStationConfiguration.Profile.DefaultFarm = Farm.Name;
		}

		FString QueueId = Library->GetAWSStringConfigSetting(DeadlineSettingsKeys::QueueId);
		FUnrealAwsEntity Queue = FindQueueById(QueueId, true);
		if (Queue.IsValid())
		{
			WorkStationConfiguration.Farm.DefaultQueue = Queue.Name;
		}

		FString StorageProfileId = Library->GetAWSStringConfigSetting(DeadlineSettingsKeys::StorageProfileId);
		FUnrealAwsEntity StorageProfile = FindStorageProfileById(StorageProfileId, true);
		if (StorageProfile.IsValid())
		{
			WorkStationConfiguration.Farm.DefaultStorageProfile = StorageProfile.Name;
		}

		FString JobAttachmentFilesystemOptions = Library->GetAWSStringConfigSetting(DeadlineSettingsKeys::JobAttachmentsFileSystem);
		WorkStationConfiguration.Farm.JobAttachmentFilesystemOptions = JobAttachmentFilesystemOptions;

		FString AutoAcceptConfirmationPrompts = Library->GetAWSStringConfigSetting(DeadlineSettingsKeys::AutoAccept);
		WorkStationConfiguration.General.AutoAcceptConfirmationPrompts = AutoAcceptConfirmationPrompts == TEXT("true");

		FString ConflictResolutionOption = Library->GetAWSStringConfigSetting(DeadlineSettingsKeys::ConflictResolution);
		WorkStationConfiguration.General.ConflictResolutionOption = ConflictResolutionOption;

		FString CurrentLoggingLevel = Library->GetAWSStringConfigSetting(DeadlineSettingsKeys::LogLevel);
		WorkStationConfiguration.General.CurrentLoggingLevel = CurrentLoggingLevel;
    }
}

void UDeadlineCloudDeveloperSettings::Login()
{
	if (auto Library = UDeadlineCloudSettingsLibrary::Get())
	{
		if (Library->Login())
		{
			Refresh();
		}
	}
}

void UDeadlineCloudDeveloperSettings::Logout()
{
	if (auto Library = UDeadlineCloudSettingsLibrary::Get())
	{
		Library->Logout();
		Refresh();
	}
}

void UDeadlineCloudDeveloperSettings::SaveToFile()
{
	if (auto Library = UDeadlineCloudSettingsLibrary::Get())
	{
		Library->SaveToAWSConfig(WorkStationConfiguration, WorkStationConfigurationCache);
	}
}

void UDeadlineCloudDeveloperSettings::UpdateFarmsCacheList()
{
	WorkStationConfigurationCache.FarmsCacheList.Reset();
	if (auto Library = UDeadlineCloudSettingsLibrary::Get())
	{
		WorkStationConfigurationCache.FarmsCacheList = Library->GetFarms();
	}
}

FUnrealAwsEntity UDeadlineCloudDeveloperSettings::FindFarmById(const FString& FarmId, bool bUpdateFarmsList)
{
	if (bUpdateFarmsList)
	{
		UpdateFarmsCacheList();
	}

	return FindAwsEntityById(FarmId, WorkStationConfigurationCache.FarmsCacheList);
}

FUnrealAwsEntity UDeadlineCloudDeveloperSettings::FindFarmByName(const FString& FarmName, bool bUpdateFarmsList)
{
	if (bUpdateFarmsList)
	{
		UpdateFarmsCacheList();
	}

	return FindAwsEntityByName(FarmName, WorkStationConfigurationCache.FarmsCacheList);
}

void UDeadlineCloudDeveloperSettings::UpdateStorageProfilesCacheList()
{
	WorkStationConfigurationCache.StorageProfilesCacheList.Reset();
	if (auto Library = UDeadlineCloudSettingsLibrary::Get())
	{
		WorkStationConfigurationCache.StorageProfilesCacheList = Library->GetStorageProfiles();
	}
}

FUnrealAwsEntity UDeadlineCloudDeveloperSettings::FindStorageProfileById(const FString& StorageProfileId, bool bUpdateStorageProfilesList)
{
	if (bUpdateStorageProfilesList)
	{
		UpdateStorageProfilesCacheList();
	}

	return FindAwsEntityById(StorageProfileId, WorkStationConfigurationCache.StorageProfilesCacheList);

}

FUnrealAwsEntity UDeadlineCloudDeveloperSettings::FindStorageProfileByName(const FString& StorageProfileName, bool bUpdateStorageProfilesList)
{
	if (bUpdateStorageProfilesList)
	{
		UpdateStorageProfilesCacheList();
	}

	return FindAwsEntityByName(StorageProfileName, WorkStationConfigurationCache.StorageProfilesCacheList);
}

void UDeadlineCloudDeveloperSettings::UpdateQueuesCacheList()
{
	WorkStationConfigurationCache.QueuesCacheList.Reset();
	if (auto Library = UDeadlineCloudSettingsLibrary::Get())
	{
		WorkStationConfigurationCache.QueuesCacheList = Library->GetQueues();
	}
}

FUnrealAwsEntity UDeadlineCloudDeveloperSettings::FindQueueById(const FString& QueueId, bool bUpdateQueuesList)
{
	if (bUpdateQueuesList)
	{
		UpdateQueuesCacheList();
	}

	return FindAwsEntityById(QueueId, WorkStationConfigurationCache.QueuesCacheList);
}

FUnrealAwsEntity UDeadlineCloudDeveloperSettings::FindQueueByName(const FString& QueueName, bool bUpdateQueuesList)
{
	if (bUpdateQueuesList)
	{
		UpdateQueuesCacheList();
	}

	return FindAwsEntityByName(QueueName, WorkStationConfigurationCache.QueuesCacheList);
}

FUnrealAwsEntity UDeadlineCloudDeveloperSettings::FindAwsEntityById(const FString& Id, const TArray<FUnrealAwsEntity>& EntityList)
{
	for (const auto& Entity : EntityList)
	{
		if (Entity.Id == Id)
		{
			return Entity;
		}
	}

	return FUnrealAwsEntity();
}

FUnrealAwsEntity UDeadlineCloudDeveloperSettings::FindAwsEntityByName(const FString& Name, const TArray<FUnrealAwsEntity>& EntityList)
{
	for (const auto& Entity : EntityList)
	{
		if (Entity.Name == Name)
		{
			return Entity;
		}
	}

	return FUnrealAwsEntity();
}
