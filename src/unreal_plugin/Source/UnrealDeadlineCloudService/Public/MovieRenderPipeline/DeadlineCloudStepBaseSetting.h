// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "MoviePipelineSetting.h"
#include "Misc/EngineVersionComparison.h"
#include "DeadlineCloudStepBaseSetting.generated.h"

/**
 * Base class for Deadline Cloud MRQ setting.
 * Unreal DeadlineCloud submitter creates an OpenJob step for each setting inherited from this class  
 */
UCLASS(Blueprintable, Abstract)
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudStepBaseSetting : public UMoviePipelineSetting
{
    GENERATED_BODY()

public:
    /** List of Deadline Cloud step names this step depends on */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Rendering", meta = (GetOptions = "GetStepOptions"))
    TArray<FString> DependsOn;

    virtual bool IsValidOnShots() const override { return true; }

#if UE_VERSION_NEWER_THAN(5, 2, -1)
    virtual bool IsValidOnPrimary() const override { return true; }
#else
    virtual bool IsValidOnMaster() const override { return true; }
#endif

#if WITH_EDITOR
	virtual FText GetCategoryText() const override { return NSLOCTEXT("MovieRenderPipeline", "DeadlineCloudCategoryName_Text", "DeadlineCloud"); }
#endif

	/** Returns a list of all currently available Deadline Cloud step names */
	UFUNCTION()
	TArray<FString> GetStepOptions();
};

/**
 * Base parameters structure for Deadline Cloud composite MRQ Setting
 */
USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudCompositeStepParameters
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category=Rendering)
	FString Name = "";

	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta = (GetOptions = "GetStepOptions", Category=Rendering))
	TArray<FString> DependsOn;
};

/**
 * Intended to be mapped to multiple steps of the OpenJob
 * Should always have property TArray<SomeType extending FDeadlineCloudCompositeStepParameters> DeadlineCloudSteps when inherited
 * An array of structs inherited from FDeadlineCloudCompositeStepParameters
 * Each array element of the property will be mapped to a step in OpenJob
 * We don't add this property to base class since in Unreal we can't define UPROPERTY of generic type
 */
UCLASS(Blueprintable, Abstract)
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudCompositeStepBaseSetting : public UMoviePipelineSetting
{
	GENERATED_BODY()

public:

	// When extended should include property:
	// UPROPERTY(EditAnywhere, BlueprintReadWrite)
	// TArray<SomeType extending FDeadlineCloudCompositeStepParameters> DeadlineCloudSteps;

	virtual bool IsValidOnShots() const override { return true; }

#if UE_VERSION_NEWER_THAN(5, 2, -1)
	virtual bool IsValidOnPrimary() const override { return true; }
#else
	virtual bool IsValidOnMaster() const override { return true; }
#endif
	
#if WITH_EDITOR
	virtual FText GetCategoryText() const override { return NSLOCTEXT("MovieRenderPipeline", "DeadlineCloudCategoryName_Text", "DeadlineCloud"); }
#endif

	/** Returns a list of all currently available Deadline Cloud step names */
	UFUNCTION()
	TArray<FString> GetStepOptions();
};

