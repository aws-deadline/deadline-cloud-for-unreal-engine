// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once

#include "DeadlineCloudJobSettings/DeadlineCloudJobDataAsset.h"
#include "IDetailCustomization.h"
#include "MoviePipelineQueue.h"

#include "MoviePipelineDeadlineCloudExecutorJob.generated.h"

/**
 * Helper struct, contains property row checkbox state
 */
USTRUCT()
struct FPropertyRowEnabledInfo
{
	GENERATED_BODY()
	
	FName PropertyPath;
	bool bIsEnabled = false;
};

/**
 * Movie pipeline executor job
 */
UCLASS(BlueprintType, config = EditorPerProjectUserSettings)
class UNREALDEADLINECLOUDSERVICE_API UMoviePipelineDeadlineCloudExecutorJob : public UMoviePipelineExecutorJob
{
	GENERATED_BODY()
public:
	UMoviePipelineDeadlineCloudExecutorJob();

	bool IsPropertyRowEnabledInMovieRenderJob(const FName& InPropertyPath) const;

	void SetPropertyRowEnabledInMovieRenderJob(const FName& InPropertyPath, bool bInEnabled);

	/**
	 * Returns the Deadline job info with overrides applied, if enabled.
	 * Skips any property not 
	 */
	UFUNCTION(BlueprintCallable, Category = "DeadlineCloud")
	FDeadlineCloudJobPresetStruct GetDeadlineJobPresetStructWithOverrides() const;

#if WITH_EDITOR
	void UpdateAttachmentFields();
	virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override;
	virtual void PostEditChangeChainProperty(FPropertyChangedChainEvent& PropertyChangedEvent) override;
#endif

	// Begin Job list options methods
	/**
	 * Delegates call to Content/Python/job_library.py DeadlineCloudJobBundleLibraryImplementation
	 * @return list of CPU architectures
	 */
	UFUNCTION()
	TArray<FString> GetCpuArchitectures();

	/**
	 * Delegates call to Content/Python/job_library.py DeadlineCloudJobBundleLibraryImplementation
	 * @return list of Operating Systems
	 */
	UFUNCTION()
	TArray<FString> GetOperatingSystems();

	UFUNCTION()
	TArray<FString> GetJobInitialStateOptions();
	// End Job list options methods

	/**
	 * Reference to Deadline Cloud job preset DataAsset. Source for default job settings
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "DeadlineCloud")
	TObjectPtr<UDeadlineCloudJobPreset> JobPreset;

	/**
	 * Reference to Deadline Cloud job preset DataAsset. Contains overriden job settings
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, config, Category = "DeadlineCloud")
	FDeadlineCloudJobPresetStruct PresetOverrides = FDeadlineCloudJobPresetStruct();
	
protected:

#if WITH_EDITOR
	void CollectDependencies();
	void UpdateInputFilesProperty();
#endif

	/**
	 * Copy overriden property values
	 * @param InStruct structure type
	 * @param InContainer Pointer to source structure
	 * @param OutContainer Pointer to target structure
	 */
	void GetPresetStructWithOverrides(UStruct* InStruct, const void* InContainer, void* OutContainer) const;

	/**
	 * List of property "enabled" states in UI
	 */
	UPROPERTY(config)
	TArray<FPropertyRowEnabledInfo> EnabledPropertyOverrides;

};

/**
 * Deadline MRQ job details view customization. Hides base MRQ job properties which are not used by Deadline Cloud Job 
 */
class FMoviePipelineDeadlineCloudExecutorJobCustomization : public IDetailCustomization
{
public:

	static TSharedRef<IDetailCustomization> MakeInstance();

	/** Begin IDetailCustomization interface */
	virtual void CustomizeDetails(IDetailLayoutBuilder& DetailBuilder) override;
	/** End IDetailCustomization interface */
};
