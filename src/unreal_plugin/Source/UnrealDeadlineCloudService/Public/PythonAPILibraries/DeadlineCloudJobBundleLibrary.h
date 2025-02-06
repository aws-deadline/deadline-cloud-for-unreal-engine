// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "PythonAPILibrary.h"
#include "MovieRenderPipeline/MoviePipelineDeadlineCloudExecutorJob.h"
#include "UObject/Object.h"
#include "DeadlineCloudJobBundleLibrary.generated.h"

/**
 * Deadline Cloud "Job Bundle" function library. Intended to be implemented in Python: Content/Python/job_library.py
 * see: DeadlineCloudJobBundleLibraryImplementation
 */
UCLASS()
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudJobBundleLibrary : public UObject, public TPythonAPILibraryBase<UDeadlineCloudJobBundleLibrary>
{
    GENERATED_BODY()

public:
    /**
     * Collect list of rendered Level and Level Sequence assets
     * @param MrqJob Unreal MRQ job
     * @return List of the Level and LevelSequence job dependencies
     */
    UFUNCTION(BlueprintImplementableEvent)
    TArray<FString> GetJobDependencies(const UMoviePipelineDeadlineCloudExecutorJob *MrqJob);

	/** @return list of CPU architectures */
	UFUNCTION(BlueprintImplementableEvent)
	TArray<FString> GetCpuArchitectures();

	/** @return list of Operating Systems */
	UFUNCTION(BlueprintImplementableEvent)
	TArray<FString> GetOperatingSystems();

	/** @return list of Possible job initial states */
	UFUNCTION(BlueprintImplementableEvent)
	TArray<FString> GetJobInitialStateOptions();
};
