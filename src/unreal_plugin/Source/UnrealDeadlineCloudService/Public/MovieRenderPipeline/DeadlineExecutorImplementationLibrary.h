// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"

#include "MoviePipelineQueue.h"
#include "MoviePipelinePrimaryConfig.h"
#include "MoviePipelineExecutor.h"
#include "MoviePipelineQueueSubsystem.h"
#include "MovieRenderPipelineSettings.h"


#include "Editor.h"
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

    UFUNCTION(BlueprintCallable, Category = "Deadline Executor")
    static void StopCsvCapture();

    UFUNCTION(BlueprintPure, Category = "Deadline Executor")
    static bool IsCsvCaptureComplete();

    UFUNCTION(BlueprintCallable, Category = "Deadline Executor")
    static void RequestMemReport();

    UFUNCTION(BlueprintPure, Category = "Deadline Executor")
    static bool IsMemReportComplete();
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
