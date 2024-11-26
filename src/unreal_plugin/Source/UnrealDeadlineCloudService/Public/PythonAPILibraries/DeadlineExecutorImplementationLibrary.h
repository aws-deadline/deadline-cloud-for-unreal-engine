// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "PythonAPILibrary.h"

// Movie Pipeline Includes



#include "MoviePipelineQueue.h"
#include "MoviePipelinePrimaryConfig.h"
#include "MovieRenderPipelineEditor/Public/MoviePipelineQueueSubsystem.h"
#include "MovieRenderPipelineEditor/Public/MovieRenderPipelineSettings.h"

// Misc
#include "Editor.h"
#include "UnrealEd.h"
#include "EditorSubsystem.h"
#include "Subsystems/ImportSubsystem.h"
#include "Subsystems/AssetEditorSubsystem.h" 



#include "MovieRenderPipelineCore/Public/MoviePipelineExecutor.h"
#include "MovieRenderPipelineCore/Public/MoviePipelineQueue.h"
#include "UObject/Object.h"
#include "DeadlineExecutorImplementationLibrary.generated.h"


UCLASS()
class UNREALDEADLINECLOUDSERVICE_API UDeadlineExecutorImplementationLibrary : public UObject, public TPythonAPILibraryBase<UDeadlineExecutorImplementationLibrary>
{
	GENERATED_BODY()

public:
	UFUNCTION(BlueprintCallable)
	static TSubclassOf<UMoviePipelineExecutorBase> GetDefaultDeadlineExecutor();
	
};
