// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once

#include "Engine/DataAsset.h"
#include "DeadlineCloudJobDataAsset.generated.h"

/**
 * Deadline Cloud Job Shared Settings
 * Goes as part of FDeadlineCloudJobPresetStruct,
 * Exposes shared job settings to Unreal MRQ through Deadline DataAsset
 */
USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudJobSharedSettingsStruct
{
	GENERATED_BODY()

	/** Job Name */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Shared Settings", meta=(DisplayPriority=0))
	FString Name = "Untitled";

	/** Job description */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Shared Settings", meta=(DisplayPriority=1))
	FString Description = "No description";

	/** Job initial state */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Shared Settings", meta = (GetOptions = "GetJobInitialStateOptions", DisplayPriority=2))
	FString InitialState = "READY";

	/** Max number of failed tasks */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Shared Settings", meta=(DisplayPriority=3))
	int32 MaximumFailedTasksCount = 1;

	/** Maximum retries per task */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Shared Settings", meta=(DisplayPriority=4))
	int32 MaximumRetriesPerTask = 50;

	// TODO Some property is missing here
};

/**
 * Deadline Cloud Host Requirement Settings
 * Goes as part of FDeadlineCloudJobPresetStruct,
 * Exposes host requirement settings to Unreal MRQ through Deadline DataAsset
 */
// TODO Get min/max values from deadline-cloud core
USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudHostRequirementsStruct
{
	GENERATED_BODY()

	/** Indicates the job can be launched on all of the available worker nodes */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Host requirements")
	bool bRunOnAllWorkerNodes = true;

	/** Required OS */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Host requirements", meta=(EditCondition="!bRunOnAllWorkerNodes", GetOptions="GetOperatingSystems"))
	FString OperatingSystem;

	/** Required CPU architecture */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Host requirements", meta=(EditCondition="!bRunOnAllWorkerNodes", GetOptions="GetCpuArchitectures"))
	FString CPU_Architecture;

	/** Required number of CPU cores */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Host requirements", meta=(ClampMin=0, ClampMax=10000, DisplayName="vCPUs", EditCondition="!bRunOnAllWorkerNodes"))
	FInt32Interval CPUs = FInt32Interval(0, 0);

	/** Required amount of RAM */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Host requirements", meta=(ClampMin=0, ClampMax=10000, DisplayName="Memory (GiB)", EditCondition="!bRunOnAllWorkerNodes"))
	FInt32Interval Memory = FInt32Interval(0, 0);

	/** Required number of GPU */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Host requirements", meta=(ClampMin=0, ClampMax=10000, DisplayName="GPU Memory (GiB)", EditCondition="!bRunOnAllWorkerNodes"))
	FInt32Interval GPUs = FInt32Interval(0, 0);

	/** Required amount of scratch space */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Host requirements", meta=(ClampMin=0, ClampMax=10000, DisplayName="Scratch Space", EditCondition="!bRunOnAllWorkerNodes"))
	FInt32Interval ScratchSpace = FInt32Interval(0, 0);

};

/**
 * Attachments files array wrapper. @ref FDeadlineCloudAttachmentArrayBuilder
 */
USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudFileAttachmentsArray
{
	GENERATED_BODY()

	/** List of files paths */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Attachments", meta=(RelativeToGameDir))
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
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Attachments", meta=(RelativeToGameDir))
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
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Attachments", DisplayName="Show Auto-Detected")
	bool bShowAutoDetected = false;

	/** List of manually added files */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Attachments", meta=(RelativeToGameDir))
	FDeadlineCloudFileAttachmentsArray Files;

	/** List of auto-detected attachment files */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Attachments", DisplayName="Auto Detected Files")
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
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Attachments", DisplayName="Show Auto-Detected")
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
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Attachments", DisplayName="Show Auto-Detected")
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

	/** Host requirements */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Preset")
	FDeadlineCloudHostRequirementsStruct HostRequirements;

	/** Job attachments */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Preset")
	FDeadlineCloudAttachmentsStruct JobAttachments;

};

/**
 * Deadline Cloud DataAsset to persist predefined settings for the Deadline Cloud jobs within the project
 */
UCLASS(BlueprintType)
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudJobPreset : public UDataAsset
{
	GENERATED_BODY()
public:

	UDeadlineCloudJobPreset();

	/** Deadline cloud job settings container struct */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Preset")
	FDeadlineCloudJobPresetStruct JobPresetStruct;
	
	// Begin Job list options methods
	/** Returns list of Cpu architectures */
	UFUNCTION()
	TArray<FString> GetCpuArchitectures();

	/** Returns list of Operating systems */
	UFUNCTION()
	TArray<FString> GetOperatingSystems();

	/** Returns list of Job initial states */
	UFUNCTION()
	TArray<FString> GetJobInitialStateOptions();
	// End Job list options methods

};
