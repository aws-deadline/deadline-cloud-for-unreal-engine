// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "MovieRenderPipeline/DeadlineCloudStepBaseSetting.h"
#include "MoviePipelineUtils.h"

#if UE_VERSION_NEWER_THAN(5, 2, -1)
#define MOVIE_PIPELINE_CONFIG_CLASS UMoviePipelinePrimaryConfig
#else
#define MOVIE_PIPELINE_CONFIG_CLASS UMoviePipelineMasterConfig
#endif

TArray<FString> GetStepOptionsImplementation(UObject* Object)
{
	TArray<FString> DeadlineCloudStepOptions;
	if (const auto Config = Cast<MOVIE_PIPELINE_CONFIG_CLASS>(Object->GetOuter()))
	{
		for (const auto Setting : Config->GetAllSettings())
		{
			const auto SettingClass = Setting->GetClass();
			if (const auto DeadlineCloudSetting = Cast<UDeadlineCloudStepBaseSetting>(SettingClass->ClassDefaultObject))
			{
				DeadlineCloudStepOptions.Add(DeadlineCloudSetting->GetDisplayText().ToString());
			}
			else if (const auto _ = Cast<UDeadlineCloudCompositeStepBaseSetting>(SettingClass->ClassDefaultObject))
			{
				// Iterate through containers to find struct properties
				for (TFieldIterator<FArrayProperty> ItProp(SettingClass, EFieldIterationFlags::IncludeAll); ItProp; ++ItProp)
				{
					const FArrayProperty* ArrayProperty = CastField<FArrayProperty>(*ItProp);
					if (const FStructProperty* StructProperty = CastField<FStructProperty>(ArrayProperty->Inner))
					{
						if (StructProperty->Struct->IsChildOf(FDeadlineCloudCompositeStepParameters::StaticStruct()))
						{
							FScriptArrayHelper ArrayHelper(ArrayProperty, ArrayProperty->ContainerPtrToValuePtr<void>(Setting));
							for (int32 ValueIdx = 0; ValueIdx < ArrayHelper.Num(); ++ValueIdx)
							{
								const auto StepParameter = reinterpret_cast<FDeadlineCloudCompositeStepParameters*>(ArrayHelper.GetRawPtr(ValueIdx));
								if (StepParameter && !StepParameter->Name.IsEmpty())
								{
									DeadlineCloudStepOptions.Add(StepParameter->Name);
								}
							}
						}
					}
				}
			}
		}
	}
	return DeadlineCloudStepOptions;
}

TArray<FString> UDeadlineCloudStepBaseSetting::GetStepOptions()
{
	return GetStepOptionsImplementation(this);
}

TArray<FString> UDeadlineCloudCompositeStepBaseSetting::GetStepOptions()
{
	return GetStepOptionsImplementation(this);
}
