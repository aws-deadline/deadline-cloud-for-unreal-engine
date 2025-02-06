// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"

#include "MoviePipelineQueue.h"
#include "MoviePipelinePrimaryConfig.h"
#include "MovieRenderPipelineEditor/Public/MoviePipelineQueueSubsystem.h"
#include "MovieRenderPipelineEditor/Public/MovieRenderPipelineSettings.h"
#include "MovieRenderPipelineCore/Public/MoviePipelineExecutor.h"
#include "MovieRenderPipelineCore/Public/MoviePipelineQueue.h"

#include "Editor.h"
#include "UnrealEd.h"
#include "EditorSubsystem.h"
#include "Subsystems/ImportSubsystem.h"
#include "Subsystems/AssetEditorSubsystem.h" 

#include "Misc/Paths.h"
#include "UObject/NoExportTypes.h"

#include "Kismet/BlueprintFunctionLibrary.h"
#include "UObject/Object.h"
#include "DeadlineExecutorImplementationLibrary.generated.h"


UCLASS()
class UNREALDEADLINECLOUDSERVICE_API UDeadlineExecutorImplementationLibrary : public UObject
{
    GENERATED_BODY()

public:
    UFUNCTION(BlueprintCallable, Category = "Deadline Executor")
    static TSubclassOf<UMoviePipelineExecutorBase> GetDefaultDeadlineExecutor();

};

UCLASS(Blueprintable)
class  ULevelSelector : public UObject
{
    GENERATED_BODY()

public:

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Level Selection", meta = (AllowedClasses = "/Script/Engine.World"))
    TSoftObjectPtr<UWorld> Map;
};

UCLASS(Blueprintable)
class  UPathSelector : public UObject
{
    GENERATED_BODY()

public:

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Path Selection")
	FFilePath FilePath;
};