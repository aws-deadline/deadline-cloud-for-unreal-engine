// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once
#include "CoreMinimal.h"
#include "Engine/DeveloperSettings.h"
#include "PythonAPILibraries/PythonAPILibrary.h"
#include "DeadlineCloudDeveloperSettings.generated.h"

/**
 * Container for Deadline Cloud global settings 
 */
USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudGlobalPluginSettings
{
	GENERATED_BODY()

	/**
	 * Selected AWS profile. List of the available profiles is returned by "get_aws_profiles"
	 * method of DeadlineCloudDeveloperSettingsImplementation
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(GetOptions="get_aws_profiles", DisplayPriority=0, Category="Global Settings"))
	FString AWS_Profile;
};

/**
 * Container for Deadline cloud profile settings 
 */
USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudProfilePluginSettings
{
	GENERATED_BODY()

	/**
	 * Path to directory where all generated Deadline Cloud job bundles will be places
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(DisplayPriority=1, Category="Profile Settings"))
	FDirectoryPath JobHistoryDir;

	/**
	 * Selected Deadline cloud farm. List of the available farms is returned by "get_farms"
	 * method of DeadlineCloudDeveloperSettingsImplementation
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(GetOptions="get_farms", DisplayPriority=2, Category="Profile Settings"))
	FString DefaultFarm;
};

/**
 * Container for Deadline cloud farm settings
 */
USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudFarmPluginSettings
{
	GENERATED_BODY()

	/**
	 * Selected Deadline cloud queue. List of the available queues is returned by "get_queues"
	 * method of DeadlineCloudDeveloperSettingsImplementation
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(GetOptions="get_queues", DisplayPriority=3, Category="Farm Settings"))
	FString DefaultQueue;

	/**
	 * Selected Deadline cloud storage profiles. List of the available storage profiles is returned by "get_storage_profiles"
	 * method of DeadlineCloudDeveloperSettingsImplementation
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(GetOptions="get_storage_profiles", DisplayPriority=4, Category="Farm Settings"))
	FString DefaultStorageProfile; 

	/**
	 * Selected Deadline cloud job attachment mode. List of the available job attachment modes is returned by "get_job_attachment_modes"
	 * method of DeadlineCloudDeveloperSettingsImplementation
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(GetOptions="get_job_attachment_modes", DisplayPriority=5, Category="Farm Settings"))
	FString JobAttachmentFilesystemOptions;
};

/**
 * Container for Deadline cloud general settings
 */
USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudGeneralPluginSettings
{
	GENERATED_BODY()

	/**
	 * Deadline Cloud auto accept confirmation prompts setting
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(DisplayPriority=6, Category="General Settings"))
	bool AutoAcceptConfirmationPrompts = false;

	/**
	 * Selected files conflict resolution strategy. List of the available strategies is returned by "get_conflict_resolution_options"
	 * method of DeadlineCloudDeveloperSettingsImplementation
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(GetOptions="get_conflict_resolution_options", DisplayPriority=7, Category="General Settings"))
	FString ConflictResolutionOption;

	/**
	 * Selected Deadline cloud logging level. List of the available strategies is returned by "get_conflict_resolution_options"
	 * method of DeadlineCloudDeveloperSettingsImplementation
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(GetOptions="get_logging_levels", DisplayPriority=8, Category="General Settings"))
	FString CurrentLoggingLevel;

};

/**
 * Deadline cloud status indicators (read-only)
 */
USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudStatus
{
	GENERATED_BODY()

	/** AwsCredentialsSource: NOT_VALID, HOST_PROVIDED, DEADLINE_CLOUD_MONITOR_LOGIN */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="cache")
	FString CredsType;

	/** AwsAuthenticationStatus: CONFIGURATION_ERROR, AUTHENTICATED, NEEDS_LOGIN */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="cache")
	FString CredsStatus;

	/** AWS API availability status: AUTHORIZED, NOT AUTHORIZED */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="cache")
	FString ApiAvailability;
};

/**
 * Container for Deadline Cloud Workstation Configuration settings
 */
USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudPluginSettings
{
	GENERATED_BODY()

	/** Global settings */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(Category="Global Settings", DisplayPriority=0))
	FDeadlineCloudGlobalPluginSettings GlobalSettings;

	/** Profile settings */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(Category="Profile Settings", DisplayPriority=1))
	FDeadlineCloudProfilePluginSettings Profile;

	/** Farm settings */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(Category="Farm Settings", DisplayPriority=2))
	FDeadlineCloudFarmPluginSettings Farm;

	/** General settings */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(Category="General Settings", DisplayPriority=3))
	FDeadlineCloudGeneralPluginSettings General;

	/** Status (read-only) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(Category="cache", DisplayPriority=3))
	FDeadlineCloudStatus State;
};

/**
 * Deadline Cloud Workstation Configuration settings located in Project -> Settings. The class is abstract and implemented in Python.
 * Python implementation DeadlineCloudDeveloperSettingsImplementation can be found in Plugin's Content/Python/settings.py
 */
UCLASS(BlueprintType, Abstract, HideCategories="cache")
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudDeveloperSettings : public UDeveloperSettings, public TPythonAPILibraryBase<UDeadlineCloudDeveloperSettings>
{
	GENERATED_BODY()

public:
	/** Deadline Cloud Workstation Configuration settings container */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(Category="Deadline Cloud Workstation Configuration", DisplayPriority=2))
	FDeadlineCloudPluginSettings WorkStationConfiguration;

	/** @return Plugin settings main menu option */
	virtual FName GetContainerName() const override { return FName("Project"); }
	
	/** @return Plugin settings category */
	virtual FName GetCategoryName() const override { return FName("Plugins"); }

	/**
	 * Override Settings Section name
	 */
#if WITH_EDITOR
	virtual FText GetSectionText() const override;
	virtual FName GetSectionName() const override;
#endif

	/** Registers OnSettingsModified method as delegate for setting values changes in the UI */
	UDeadlineCloudDeveloperSettings();

	/**
	 * Delegate method which is called on each property value change in UI.
	 * Method is implemented in Python, see "on_settings_modified" in DeadlineCloudDeveloperSettingsImplementation
	 * @param PropertyPath path to modified property in Unreal reflection system properties naming format.
	 */
	UFUNCTION(BlueprintImplementableEvent, Category = DeadlineCloud)
	void OnSettingsModified(const FString& PropertyPath);

	/**
	 * Delegate method which is called on each external Deadline Cloud settings directory update.
	 * Settings directory update is handled by FDeadlineCloudStatusHandler
	 */
	UFUNCTION(BlueprintImplementableEvent, Category = DeadlineCloud)
	void RefreshState();

	/** Deadline cloud login */
	UFUNCTION(BlueprintImplementableEvent, Category = DeadlineCloud)
	void Login();

	/** Deadline cloud logout */
	UFUNCTION(BlueprintImplementableEvent, Category = DeadlineCloud)
	void Logout();


};
