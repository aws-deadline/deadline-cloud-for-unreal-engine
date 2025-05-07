// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "PythonAPILibrary.h"
#include "UObject/Object.h"
#include "DeadlineCloudSettingsLibrary.generated.h"

/**
 * Structure representing an AWS entity with an ID and Name.
 */
USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FUnrealAwsEntity
{
    GENERATED_BODY()

    /** Unique identifier for the AWS entity. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AWS")
    FString Id;

    /** Name of the AWS entity. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AWS")
    FString Name;

    /** 
     * Validates the AWS entity by checking if both Id and Name are not empty.
     * @return True if valid, otherwise false.
     */
    bool IsValid()
    {
        return !Id.IsEmpty() && !Name.IsEmpty();
    }
};

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
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(GetOptions="GetAWSProfilesList", DisplayPriority=0, Category="Global Settings"))
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
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(GetOptions="GetFarmsList", DisplayPriority=2, Category="Profile Settings"))
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
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(GetOptions="GetQueuesList", DisplayPriority=3, Category="Farm Settings"))
	FString DefaultQueue;

	/**
	 * Selected Deadline cloud storage profiles. List of the available storage profiles is returned by "get_storage_profiles"
	 * method of DeadlineCloudDeveloperSettingsImplementation
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(GetOptions="GetStorageProfilesList", DisplayPriority=4, Category="Farm Settings"))
	FString DefaultStorageProfile; 

	/**
	 * Selected Deadline cloud job attachment mode. List of the available job attachment modes is returned by "get_job_attachment_modes"
	 * method of DeadlineCloudDeveloperSettingsImplementation
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(GetOptions="GetJobAttachmentModes", DisplayPriority=5, Category="Farm Settings"))
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
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(GetOptions="GetConflictResolutionOptions", DisplayPriority=7, Category="General Settings"))
	FString ConflictResolutionOption;

	/**
	 * Selected Deadline cloud logging level. List of the available strategies is returned by "get_conflict_resolution_options"
	 * method of DeadlineCloudDeveloperSettingsImplementation
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(GetOptions="GetLoggingLevels", DisplayPriority=8, Category="General Settings"))
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

/*
* 
*/
USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudPluginSettingsCache
{
	GENERATED_BODY()

    /** Cache list of farms. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(Category="cache"))
	TArray<FUnrealAwsEntity> FarmsCacheList;

	/** Cache list of queues. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(Category="cache"))
	TArray<FUnrealAwsEntity> QueuesCacheList;

	/** Cache list of storage profiles. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(Category="cache"))
	TArray<FUnrealAwsEntity> StorageProfilesCacheList;
};

/**
 * Library class for managing Deadline Cloud settings.
 */
UCLASS()
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudSettingsLibrary: public UObject, public TPythonAPILibraryBase<UDeadlineCloudSettingsLibrary>
{
    GENERATED_BODY()

public:

    bool bInitialized = false;

    /**
	* Called after python initialization to set up the library and update settings.
    */
    UFUNCTION(BlueprintCallable, Category = "DeadlineCloudSettingsLibrary")
    void InitFromPython();

    /** 
     * Retrieves a specific AWS configuration setting by name.
     * @param SettingName The name of the setting to retrieve.
     * @return The value of the specified setting.
     */
    UFUNCTION(BlueprintImplementableEvent)
    FString GetAWSStringConfigSetting(const FString& SettingName);

    /** 
     * Sets a specific AWS configuration setting by name.
     * @param SettingName The name of the setting to set.
     * @param SettingValue The value to set for the specified setting.
     */
    UFUNCTION(BlueprintImplementableEvent)
    void SetAWSStringConfigSetting(const FString& SettingName, const FString& SettingValue);

    /** 
     * Retrieves a list of available AWS profiles.
     * @return An array of AWS profile names.
     */
    UFUNCTION(BlueprintImplementableEvent)
    TArray<FString> GetAWSProfiles();

    /** 
     * Retrieves a list of available conflict resolution options.
     * @return An array of conflict resolution option names.
     */
    UFUNCTION(BlueprintImplementableEvent)
    TArray<FString> GetConflictResolutionOptions();

    /** 
     * Retrieves a list of available job attachment modes.
     * @return An array of job attachment mode names.
     */
    UFUNCTION(BlueprintImplementableEvent)
    TArray<FString> GetJobAttachmentModes();

    /** 
     * Retrieves a list of available logging levels.
     * @return An array of logging level names.
     */
    UFUNCTION(BlueprintImplementableEvent)
    TArray<FString> GetLoggingLevels();

    /** 
     * Retrieves a list of available farms.
     * @return An array of UnrealAwsEntity representing the farms.
     */
    UFUNCTION(BlueprintImplementableEvent)
    TArray<FUnrealAwsEntity> GetFarms();

    /** 
     * Retrieves a list of available queues.
     * @return An array of UnrealAwsEntity representing the queues.
     */
    UFUNCTION(BlueprintImplementableEvent)
    TArray<FUnrealAwsEntity> GetQueues();

    /** 
     * Retrieves a list of available storage profiles.
     * @return An array of UnrealAwsEntity representing the storage profiles.
     */
    UFUNCTION(BlueprintImplementableEvent)
    TArray<FUnrealAwsEntity> GetStorageProfiles();

	/**
	* Retrieves the current status of the API.
	* @return The current API status as a FDeadlineCloudStatus structure.
	*/
    UFUNCTION(BlueprintImplementableEvent)
	FDeadlineCloudStatus GetApiStatus();

    /** 
     * Initiates a login process for AWS.
     */
    UFUNCTION(BlueprintImplementableEvent)
    bool Login();

    /** 
     * Initiates a logout process for AWS.
     */
    UFUNCTION(BlueprintImplementableEvent)
    void Logout();

    /** 
     * Saves the provided settings to the AWS configuration.
     * @param Settings The settings to save.
     */
    UFUNCTION(BlueprintImplementableEvent)
    void SaveToAWSConfig(FDeadlineCloudPluginSettings Settings, FDeadlineCloudPluginSettingsCache Cache);
};
	
