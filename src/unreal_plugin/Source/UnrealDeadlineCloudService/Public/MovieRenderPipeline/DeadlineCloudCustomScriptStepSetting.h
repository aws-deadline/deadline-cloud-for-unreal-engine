// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "MovieRenderPipeline/DeadlineCloudStepBaseSetting.h"
#include "DeadlineCloudCustomScriptStepSetting.generated.h"

/**
 * Custom script step settings parameters
 */
USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudCustomScriptStepParameters : public FDeadlineCloudCompositeStepParameters
{
	GENERATED_BODY()

	/** Path to custom python script to execute */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(RelativeToGameDir))
	FFilePath Script;
};

/**
 * UDeadlineCloudCompositeStepBaseSetting -- should always include property DeadlineCloudSteps,
 * which should be array of structs inherited from FDeadlineCloudCompositeStepParameters 
 * UDeadlineCloudCompositeStepBaseSetting
 */
UCLASS(Blueprintable)
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudCustomScriptStepSetting : public UDeadlineCloudCompositeStepBaseSetting
{
	GENERATED_BODY()

public:
	/** List of custom script steps */
	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	TArray<FDeadlineCloudCustomScriptStepParameters> DeadlineCloudSteps;

#if WITH_EDITOR
	virtual FText GetDisplayText() const override { return NSLOCTEXT("MovieRenderPipeline", "BeaLineRenderStepSettingDisplayName", "Custom Scripts"); }
#endif

};
