// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once
#include "DeadlineCloudStep.h"
#include "DeadlineCloudRenderStep.h"
#include "CoreMinimal.h"
#include "DeadlineCloudEnvironment.h"
#include "DeadlineCloudHostRequirements.h"
#include "DeadlineCloudJob.generated.h"

/**
 * All Deadline Cloud job settings container struct
 */

 /**
  * Deadline Cloud Job Shared Settings
  * Goes as part of FDeadlineCloudJobPresetStruct,
  * Exposes shared job settings to Unreal MRQ through Deadline DataAsset
  */
USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudJobSharedSettingsStruct
{
    GENERATED_BODY()

public:
    /** Job Name */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Shared Settings", meta = (DisplayPriority = 0, CustomWidgetType = STRING, ValidationType = JobName))
    FString Name = "Untitled";

    /** Job description */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Shared Settings", meta = (DisplayPriority = 1, CustomWidgetType = STRING, ValidationType = JobDescription))
    FString Description = "No description";

    /** Job initial state */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Shared Settings", meta = (GetOptions = "GetJobInitialStateOptions", DisplayPriority = 2))
    FString InitialState = "READY";

    /** Max number of failed tasks */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Shared Settings", meta = (ClampMin = 0, DisplayPriority = 3))
    int32 MaximumFailedTasksCount = 0;

    /** Maximum retries per task */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Shared Settings", meta = (ClampMin = 0, DisplayPriority = 4))
    int32 MaximumRetriesPerTask = 2;

    /** Job priority */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Shared Settings", meta = (ClampMin = 0, ClampMax = 100, DisplayPriority = 5))
    int32 Priority = 50;
};

/**
 * Attachments files array wrapper. @ref FDeadlineCloudAttachmentArrayBuilder
 */
USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudFileAttachmentsArray
{
	GENERATED_BODY()

	/** List of files paths */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Attachments", meta = (RelativeToGameDir))
	TArray<FFilePath> Paths;
};
 /**
  * Attachments directories array wrapper. @ref FDeadlineCloudAttachmentArrayBuilder
  */
USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudDirectoryAttachmentsArray
{
	GENERATED_BODY()

	/** List of directories paths */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Attachments", meta = (RelativeToGameDir))
	TArray<FDirectoryPath> Paths;
};

/**
 * Files attachments container struct
 */
USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudFileAttachmentsStruct
{
	GENERATED_BODY()

	/** Switcher to show/hide auto-detected files in MRQ job details  */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Attachments", DisplayName = "Show Auto-Detected")
	bool bShowAutoDetected = false;

	/** List of manually added files */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Attachments", meta = (RelativeToGameDir))
	FDeadlineCloudFileAttachmentsArray Files;

	/** List of auto-detected attachment files */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Attachments", DisplayName = "Auto Detected Files")
	FDeadlineCloudFileAttachmentsArray AutoDetected;
};

/**
 * Input Directories attachments container struct
 */
USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudDirectoryAttachmentsStruct
{
	GENERATED_BODY()

	/** Switcher to show/hide auto-detected directories in MRQ job details  */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Attachments", DisplayName = "Show Auto-Detected")
	bool bShowAutoDetected = false;

	/** List of manually added directories */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Attachments")
	FDeadlineCloudDirectoryAttachmentsArray Directories;

	/** List of auto-detected attachment directories */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Attachments")
	FDeadlineCloudDirectoryAttachmentsArray AutoDetectedDirectories;
};

/**
 * Output Directories attachments container struct
 */
USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudOutputDirectoryAttachmentsStruct
{
	GENERATED_BODY()

	/** Switcher to show/hide auto-detected directories in MRQ job details  */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Attachments", DisplayName = "Show Auto-Detected")
	bool bShowAutoDetected = false;

	/** List of manually added directories */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Attachments")
	FDeadlineCloudDirectoryAttachmentsArray Directories;

	/** List of auto-detected attachment directories */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Attachments")
	FDeadlineCloudDirectoryAttachmentsArray AutoDetectedDirectories;
};

/**
 * All attachments container struct
 */
USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudAttachmentsStruct
{
	GENERATED_BODY()

	/** Input files attachments */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Attachments")
	FDeadlineCloudFileAttachmentsStruct InputFiles;

	/** Input directories attachments */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Attachments")
	FDeadlineCloudDirectoryAttachmentsStruct InputDirectories;

	/** Output directories attachments */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Attachments")
	FDeadlineCloudOutputDirectoryAttachmentsStruct OutputDirectories;
};

/**
 * All Deadline Cloud job settings container struct
 */
USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudJobPresetStruct
{
	GENERATED_BODY()

	/** Job shared settings */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Preset")
	FDeadlineCloudJobSharedSettingsStruct JobSharedSettings;

	/** Job attachments */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Preset")
	FDeadlineCloudAttachmentsStruct JobAttachments;

};

USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudJobParametersArray
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	TArray<FParameterDefinition> Parameters;
};


UCLASS(BlueprintType, Blueprintable, Config = Game)
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudJob : public UDataAsset
{
	GENERATED_BODY()
public:

	UDeadlineCloudJob();

	FSimpleDelegate OnPathChanged;

	void TriggerChange()
	{
		OnPathChanged.Execute();
	}

	UPROPERTY(Config, BlueprintReadWrite, Category = "Parameters", meta = (DisplayPriority = 1))
	FString Name;

	UPROPERTY(Config, EditAnywhere, BlueprintReadWrite, Category = "Parameters", meta = (DisplayPriority = 2))
	FFilePath PathToTemplate;

	/** Deadline cloud job settings container struct */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters", DisplayName = "Job Preset", meta = (DisplayPriority = 3))
	FDeadlineCloudJobPresetStruct JobPresetStruct;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters", meta = (DisplayPriority = 6))
    TArray<TObjectPtr<UDeadlineCloudStep>> Steps;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters", meta = (DisplayPriority = 5))
    TArray<TObjectPtr<UDeadlineCloudEnvironment>> Environments;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters", meta = (DisplayPriority = 4))
	FDeadlineCloudJobParametersArray ParameterDefinition;

public:
	/*Read path */
	UFUNCTION()
	void OpenJobFile(const FString& Path);

	UFUNCTION()
	void ReadName(const FString& Path);

	FString GetDefaultParameterValue(const FString& ParameterName);

	void FixConsistencyForHiddenParameters();

	UFUNCTION()
	FParametersConsistencyCheckResult CheckJobParametersConsistency(const UDeadlineCloudJob* Self);

	UFUNCTION(BlueprintCallable, Category = "Parameters")
	TArray <FParameterDefinition> GetJobParameters();

	UFUNCTION(BlueprintCallable, Category="Parameters")
	void SetJobParameters(TArray<FParameterDefinition> InJobParameters);

	UFUNCTION()
	TArray<FString> GetCpuArchitectures();

	/** Returns list of Operating systems */
	UFUNCTION()
	TArray<FString> GetOperatingSystems();

	/** Returns list of Job initial states */
	UFUNCTION()
	TArray<FString> GetJobInitialStateOptions();

	UFUNCTION(BlueprintCallable, Category = "Parameters")
	void FixJobParametersConsistency(UDeadlineCloudJob* Job);

	TArray<FStepTaskParameterDefinition> GetAllStepParameters() const;

	TArray<FParameterDefinition> GetParametersDataToOverride() const;
public:

	virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override;

    FSimpleDelegate OnParameterHidden;

	void ParameterHiddenEvent() {
		if (OnParameterHidden.IsBound())
		{
			OnParameterHidden.Execute();
		}
	};

	FHiddenItemsManager& GetHiddenManager() { return HiddenVarsManager; }
	const FHiddenItemsManager& GetHiddenManager() const { return HiddenVarsManager; }
private:

	UPROPERTY()
	FHiddenItemsManager HiddenVarsManager;

};
