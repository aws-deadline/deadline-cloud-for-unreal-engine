// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once

#include "DeadlineCloudJobSettings/DeadlineCloudJob.h"
#include "DeadlineCloudJobSettings/DeadlineCloudRenderJob.h"
#include "DeadlineCloudJobSettings/DeadlineCloudRenderStep.h"
#include "IDetailCustomization.h"
#include "MoviePipelineQueue.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJobPresetDetailsCustomization.h"
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

//struct like DeadlineCloudJobParametersArray with step and env overrides
USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FJobTemplateOverrides
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
    TArray<FParameterDefinition> Parameters;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
    TArray<FDeadlineCloudStepOverride> StepsOverrides;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
    TArray<FDeadlineCloudEnvironmentOverride> EnvironmentsOverrides;
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

    void PostInitProperties() override;

    /**
     * Returns the Deadline job info with overrides applied, if enabled.
     * Skips any property not
     */
    UFUNCTION(BlueprintCallable, Category = "DeadlineCloud")
    FDeadlineCloudJobPresetStruct GetDeadlineJobPresetStructWithOverrides() const;

    UFUNCTION(BlueprintCallable, Category = "DeadlineCloud")
    FDeadlineCloudJobParametersArray GetParameterDefinitionWithOverrides() const;

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
    UFUNCTION()
    UDeadlineCloudRenderJob* CreateDefaultJobPresetFromTemplates(UDeadlineCloudRenderJob* Preset);

    UFUNCTION()
    TArray<FDeadlineCloudStepOverride> GetStepsToOverride(const UDeadlineCloudJob* Preset);
    UFUNCTION()
    TArray<FDeadlineCloudEnvironmentOverride> GetEnvironmentsToOverride(const UDeadlineCloudJob* Preset);
    
    UFUNCTION()
    bool HasEditableParameters(const FDeadlineCloudStepOverride& StepOverride) const;

    /**
     * Reference to Deadline Cloud job preset DataAsset. Source for default job settings
     */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "DeadlineCloud")
    TObjectPtr<UDeadlineCloudRenderJob> JobPreset;

    /**
     * Reference to Deadline Cloud job preset DataAsset. Contains overriden job settings
     */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, config, Category = "DeadlineCloud")
    FDeadlineCloudJobPresetStruct PresetOverrides = FDeadlineCloudJobPresetStruct();

    /**
 * Reference to Deadline Cloud job parameters. Contains overriden job settings
 */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, config, Category = "DeadlineCloud")
    FJobTemplateOverrides JobTemplateOverrides = FJobTemplateOverrides();

    void JobPresetChanged();
    
    static bool IsAssetFileValid(const FString& FilePath);
	static bool IsAssetDirectoryValid(const FString& DirectoryPath);

protected:

#if WITH_EDITOR
    void CollectDependencies();
	void CollectPluginsDependencies();
    void UpdateInputFilesProperty();
    void UpdateInputDirectoriesProperty();
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
public:

    FSimpleDelegate OnRequestDetailsRefresh;


};

/**
 * Deadline MRQ job details view customization. Hides base MRQ job properties which are not used by Deadline Cloud Job
 */
class FMoviePipelineDeadlineCloudExecutorJobCustomization : public IDetailCustomization
{
public:

    static TSharedRef<IDetailCustomization> MakeInstance();
    TWeakObjectPtr<UMoviePipelineDeadlineCloudExecutorJob> MrqJob;

    /** Begin IDetailCustomization interface */
    virtual void CustomizeDetails(IDetailLayoutBuilder& DetailBuilder) override;
    /** End IDetailCustomization interface */
};
