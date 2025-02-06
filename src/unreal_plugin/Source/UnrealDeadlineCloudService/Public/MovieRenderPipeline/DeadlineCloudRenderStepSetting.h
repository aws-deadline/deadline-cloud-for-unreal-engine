// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "MovieRenderPipeline/DeadlineCloudStepBaseSetting.h"
#include "DeadlineCloudRenderStepSetting.generated.h"

/**
 * Deadline Cloud Render step setting
 */
UCLASS()
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudRenderStepSetting : public UDeadlineCloudStepBaseSetting
{
    GENERATED_BODY()

public:
#if WITH_EDITOR
    virtual FText GetDisplayText() const override { return NSLOCTEXT("MovieRenderPipeline", "DeadlineCloudRenderStepSettingDisplayName", "Render"); }
#endif

};
