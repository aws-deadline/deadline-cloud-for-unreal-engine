// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "DeadlineCloudJob.h"
#include "DeadlineCloudRenderJob.generated.h"

UCLASS(BlueprintType)
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudRenderJob : public UDeadlineCloudJob
{
    GENERATED_BODY()
public:

    UDeadlineCloudRenderJob() {};

};
UCLASS(Blueprintable)
class  ULevelSelector : public UObject
{
	GENERATED_BODY()

public:

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Level Selection", meta = (AllowedClasses = "/Script/Engine.World"))
	TSoftObjectPtr<UWorld> Map;
};