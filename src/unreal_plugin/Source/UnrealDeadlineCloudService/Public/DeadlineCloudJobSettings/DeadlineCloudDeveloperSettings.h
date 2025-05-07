// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once
#include "CoreMinimal.h"
#include "Engine/DeveloperSettings.h"
#include "PythonAPILibraries/DeadlineCloudSettingsLibrary.h"
#include "DeadlineCloudDeveloperSettings.generated.h"

/**
 * Deadline Cloud Workstation Configuration settings located in Project -> Settings.
 */
UCLASS(BlueprintType, HideCategories="cache")
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudDeveloperSettings : public UDeveloperSettings
{
	GENERATED_BODY()

public:

	/** 
	* Constructor for UDeadlineCloudDeveloperSettings.
	*/
	UDeadlineCloudDeveloperSettings();

	/** 
	* Gets the default instance of UDeadlineCloudDeveloperSettings.
	* @return The default settings instance.
	*/
	static const UDeadlineCloudDeveloperSettings* Get() { return GetDefault<UDeadlineCloudDeveloperSettings>(); }

	/** 
	* Gets a mutable instance of UDeadlineCloudDeveloperSettings.
	* @return A mutable settings instance.
	*/
	static UDeadlineCloudDeveloperSettings* GetMutable() { return GetMutableDefault<UDeadlineCloudDeveloperSettings>(); }

	/** 
	* Deadline Cloud Workstation Configuration settings container.
	*/
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(Category="Deadline Cloud Workstation Configuration", DisplayPriority=2))
	FDeadlineCloudPluginSettings WorkStationConfiguration;

	/** 
	* @return Plugin settings main menu option.
	*/
	virtual FName GetContainerName() const override { return FName("Project"); }
	
	/** 
	* @return Plugin settings category.
	*/
	virtual FName GetCategoryName() const override { return FName("Plugins"); }

	/** 
	* Retrieves the list of farms.
	* @return An array of farm names.
	*/
	UFUNCTION(Category = DeadlineCloudSettings)
	TArray<FString> GetFarmsList();

	/** 
	* Retrieves the list of AWS profiles.
	* @return An array of AWS profile names.
	*/
	UFUNCTION(Category = DeadlineCloudSettings)
	TArray<FString> GetAWSProfilesList();

	/** 
	* Retrieves the available logging levels.
	* @return An array of logging level names.
	*/
	UFUNCTION(Category = DeadlineCloudSettings)
	TArray<FString> GetLoggingLevels();

	/** 
	* Retrieves the conflict resolution options.
	* @return An array of conflict resolution option names.
	*/
	UFUNCTION(Category = DeadlineCloudSettings)
	TArray<FString> GetConflictResolutionOptions();

	/** 
	* Retrieves the list of storage profiles.
	* @return An array of storage profile names.
	*/
	UFUNCTION(Category = DeadlineCloudSettings)
	TArray<FString> GetStorageProfilesList();

	/** 
	* Retrieves the job attachment modes.
	* @return An array of job attachment mode names.
	*/
	UFUNCTION(Category = DeadlineCloudSettings)
	TArray<FString> GetJobAttachmentModes();

	/** 
	* Retrieves the list of queues.
	* @return An array of queue names.
	*/
	UFUNCTION(Category = DeadlineCloudSettings)
	TArray<FString> GetQueuesList();

	/**
	* Override Settings Section name.
	*/
#if WITH_EDITOR
	/** 
	* @return The section text for the settings.
	*/
	virtual FText GetSectionText() const override;

	/** 
	* @return The section name for the settings.
	*/
	virtual FName GetSectionName() const override;

	/** 
	* Handles property changes in the editor.
	* @param PropertyChangedEvent The event that describes the property change.
	*/
	virtual void PostEditChangeProperty(struct FPropertyChangedEvent& PropertyChangedEvent) override;

	/** 
	* Initializes properties after construction.
	*/
	virtual void PostInitProperties() override;
#endif

	/** Refreshes the settings. */
	UFUNCTION(Category = DeadlineCloudSettings)
	void Refresh();

	/** 
	* Delegate method called on each external Deadline Cloud settings directory update.
	* Settings directory update is handled by FDeadlineCloudStatusHandler.
	*/
	UFUNCTION(Category = DeadlineCloudSettings)
	void RefreshState();

	/** Internal method to refresh state. */
	void RefreshStateInternal();

	/** 
	* Refreshes settings from the default profile.
	*/
	UFUNCTION(Category = DeadlineCloudSettings)
	void RefreshFromDefaultProfile();

	/** Internal method to refresh from the default profile. */
	void RefreshFromDefaultProfileInternal();

	/** 
	* Logs in to the Deadline Cloud.
	*/
	UFUNCTION(Category = DeadlineCloudSettings)
	void Login();

	/** 
	* Logs out of the Deadline Cloud.
	*/
	UFUNCTION(Category = DeadlineCloudSettings)
	void Logout();

	/** Saves settings to a file. */
	void SaveToFile();

	/** 
	* Finds a farm by its ID.
	* @param FarmId The ID of the farm to find.
	* @param bUpdateFarmsList Whether to update the farms list.
	* @return The found farm entity.
	*/
	FUnrealAwsEntity FindFarmById(const FString& FarmId, bool bUpdateFarmsList = false);
	FUnrealAwsEntity FindFarmByName(const FString& FarmName, bool bUpdateFarmsList = false);

	/** 
	* Finds a storage profile by its ID.
	* @param StorageProfileId The ID of the storage profile to find.
	* @param bUpdateStorageProfilesList Whether to update the storage profiles list.
	* @return The found storage profile entity.
	*/
	FUnrealAwsEntity FindStorageProfileById(const FString& StorageProfileId, bool bUpdateStorageProfilesList = false);
	FUnrealAwsEntity FindStorageProfileByName(const FString& StorageProfileName, bool bUpdateStorageProfilesList = false);

	/** 
	* Finds a queue by its ID.
	* @param QueueId The ID of the queue to find.
	* @param bUpdateQueuesList Whether to update the queues list.
	* @return The found queue entity.
	*/
	FUnrealAwsEntity FindQueueById(const FString& QueueId, bool bUpdateQueuesList = false);
	FUnrealAwsEntity FindQueueByName(const FString& QueueName, bool bUpdateQueuesList = false);
protected:
	FDeadlineCloudPluginSettingsCache WorkStationConfigurationCache;

	/** Updates the queues cache list. */
	void UpdateQueuesCacheList();

	/** Updates the storage profiles cache list. */
	void UpdateStorageProfilesCacheList();

	/** Updates the farms cache list. */
	void UpdateFarmsCacheList();

	/** 
	* Finds an AWS entity by its ID.
	* @param Id The ID of the entity to find.
	* @param EntityList The list of entities to search.
	* @return The found AWS entity.
	*/
	static FUnrealAwsEntity FindAwsEntityById(const FString& Id, const TArray<FUnrealAwsEntity>& EntityList);

	static FUnrealAwsEntity FindAwsEntityByName(const FString& Name, const TArray<FUnrealAwsEntity>& EntityList);
};
