// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "UnrealDeadlineCloudServiceModule.h"
#include "DeadlineCloudJobSettings/DeadlineCloudDeveloperSettings.h"
#include "DeadlineCloudJobSettings/DeadlineCloudSettingsDetails.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJobPresetDetailsCustomization.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJobDetails.h"
#include "DeadlineCloudJobSettings/DeadlineCloudStepDetails.h"
#include "DeadlineCloudJobSettings/DeadlineCloudEnvironmentDetails.h"
#include "DeadlineCloudJobSettings/DeadlineCloudEnvironmentOverrideCustomization.h"
#include "MovieRenderPipeline/MoviePipelineDeadlineCloudExecutorJob.h"

#define LOCTEXT_NAMESPACE "UnrealDeadlineCloudServiceModule"

void FUnrealDeadlineCloudServiceModule::StartupModule()
{
	UE_LOG(LogTemp, Display, TEXT("DeadlineCloud: UE Install Path: %s"), *FPaths::EngineDir());

	// Verify the executor class is available
    UClass* ExecutorClass = UMoviePipelineDeadlineCloudExecutorJob::StaticClass();
    if (ExecutorClass)
	{
        UE_LOG(LogTemp, Display, TEXT("DeadlineCloud: UMoviePipelineDeadlineCloudExecutorJob class found: %s"), *ExecutorClass->GetName());
    } else {
        UE_LOG(LogTemp, Error, TEXT("DeadlineCloud: UMoviePipelineDeadlineCloudExecutorJob class NOT found"));
    }

    FPropertyEditorModule& PropertyModule = FModuleManager::GetModuleChecked<FPropertyEditorModule>("PropertyEditor");
    UE_LOG(LogTemp, Display, TEXT("DeadlineCloud: PropertyEditor module loaded"));
    
	PropertyModule.RegisterCustomClassLayout(
        UDeadlineCloudDeveloperSettings::StaticClass()->GetFName(),
        FOnGetDetailCustomizationInstance::CreateStatic(&FDeadlineCloudSettingsDetails::MakeInstance)
    );

    //job step, environment object details
    PropertyModule.RegisterCustomClassLayout(
        UDeadlineCloudJob::StaticClass()->GetFName(),
        FOnGetDetailCustomizationInstance::CreateStatic(&FDeadlineCloudJobDetails::MakeInstance));

	PropertyModule.RegisterCustomClassLayout(
		UDeadlineCloudStep::StaticClass()->GetFName(),
		FOnGetDetailCustomizationInstance::CreateStatic(&FDeadlineCloudStepDetails::MakeInstance));
    UE_LOG(LogTemp, Display, TEXT("DeadlineCloud: UDeadlineCloudStep registered"));

	PropertyModule.RegisterCustomClassLayout(
		UDeadlineCloudEnvironment::StaticClass()->GetFName(),
		FOnGetDetailCustomizationInstance::CreateStatic(&FDeadlineCloudEnvironmentDetails::MakeInstance));
    UE_LOG(LogTemp, Display, TEXT("DeadlineCloud: UDeadlineCloudEnvironment registered"));


	PropertyModule.RegisterCustomClassLayout(
		UMoviePipelineDeadlineCloudExecutorJob::StaticClass()->GetFName(),
		FOnGetDetailCustomizationInstance::CreateStatic(&FMoviePipelineDeadlineCloudExecutorJobCustomization::MakeInstance)
	);
	UE_LOG(LogTemp, Display, TEXT("DeadlineCloud: Registered UMoviePipelineDeadlineCloudExecutorJob customization"));

	// Job details properties customization
	PropertyModule.RegisterCustomPropertyTypeLayout(
		FDeadlineCloudJobSharedSettingsStruct::StaticStruct()->GetFName(),
		FOnGetPropertyTypeCustomizationInstance::CreateStatic(&FDeadlineCloudJobPresetDetailsCustomization::MakeInstance));

	PropertyModule.RegisterCustomPropertyTypeLayout(
		FDeadlineCloudHostRequirementsStruct::StaticStruct()->GetFName(),
		FOnGetPropertyTypeCustomizationInstance::CreateStatic(&FDeadlineCloudJobPresetDetailsCustomization::MakeInstance));

	PropertyModule.RegisterCustomPropertyTypeLayout(
		FDeadlineCloudJobParametersArray::StaticStruct()->GetFName(),
		FOnGetPropertyTypeCustomizationInstance::CreateStatic(&FDeadlineCloudJobParametersArrayCustomization::MakeInstance));
	
		PropertyModule.RegisterCustomPropertyTypeLayout(
			FJobTemplateOverrides::StaticStruct()->GetFName(),
			FOnGetPropertyTypeCustomizationInstance::CreateStatic(&FJobTemplateOverridesCustomization::MakeInstance));
	//Step details arrays 
	PropertyModule.RegisterCustomPropertyTypeLayout(
		FDeadlineCloudStepParametersArray::StaticStruct()->GetFName(),
		FOnGetPropertyTypeCustomizationInstance::CreateStatic(&FDeadlineCloudStepParametersArrayCustomization::MakeInstance));

	PropertyModule.RegisterCustomPropertyTypeLayout(
		FStepTaskParameterDefinition::StaticStruct()->GetFName(),
		FOnGetPropertyTypeCustomizationInstance::CreateStatic(&FDeadlineCloudStepParameterListCustomization::MakeInstance));

	// Environment details customization
	PropertyModule.RegisterCustomPropertyTypeLayout(
		FDeadlineCloudEnvironmentVariablesMap::StaticStruct()->GetFName(),
		FOnGetPropertyTypeCustomizationInstance::CreateStatic(&FDeadlineCloudEnvironmentParametersMapCustomization::MakeInstance));

	// Paths details
	PropertyModule.RegisterCustomPropertyTypeLayout(
		FDeadlineCloudFileAttachmentsArray::StaticStruct()->GetFName(),
		FOnGetPropertyTypeCustomizationInstance::CreateStatic(&FDeadlineCloudAttachmentArrayCustomization::MakeInstance));

	PropertyModule.RegisterCustomPropertyTypeLayout(
		FDeadlineCloudDirectoryAttachmentsArray::StaticStruct()->GetFName(),
		FOnGetPropertyTypeCustomizationInstance::CreateStatic(&FDeadlineCloudAttachmentArrayCustomization::MakeInstance));

	
	PropertyModule.RegisterCustomPropertyTypeLayout(
		FDeadlineCloudFileAttachmentsStruct::StaticStruct()->GetFName(),
		FOnGetPropertyTypeCustomizationInstance::CreateStatic(&FDeadlineCloudAttachmentDetailsCustomization::MakeInstance));

	PropertyModule.RegisterCustomPropertyTypeLayout(
		FDeadlineCloudDirectoryAttachmentsStruct::StaticStruct()->GetFName(),
		FOnGetPropertyTypeCustomizationInstance::CreateStatic(&FDeadlineCloudAttachmentDetailsCustomization::MakeInstance));

	PropertyModule.RegisterCustomPropertyTypeLayout(
		FDeadlineCloudOutputDirectoryAttachmentsStruct::StaticStruct()->GetFName(),
		FOnGetPropertyTypeCustomizationInstance::CreateStatic(&FDeadlineCloudAttachmentDetailsCustomization::MakeInstance));

	PropertyModule.RegisterCustomPropertyTypeLayout(
		FDeadlineCloudEnvironmentOverride::StaticStruct()->GetFName(),
		FOnGetPropertyTypeCustomizationInstance::CreateStatic(&FDeadlineCloudEnvironmentOverrideCustomization::MakeInstance)
	);

	// Step override customization
	PropertyModule.RegisterCustomPropertyTypeLayout(
		FDeadlineCloudStepOverride::StaticStruct()->GetFName(),
		FOnGetPropertyTypeCustomizationInstance::CreateStatic(&FDeadlineCloudStepOverrideCustomization::MakeInstance)
	);

	PropertyModule.NotifyCustomizationModuleChanged();
	UE_LOG(LogTemp, Display, TEXT("DeadlineCloud: All customizations registered, module startup complete"));
}

void FUnrealDeadlineCloudServiceModule::ShutdownModule()
{
	// This function may be called during shutdown to clean up your module.  For modules that support dynamic reloading,
	// we call this function before unloading the module.
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FUnrealDeadlineCloudServiceModule, UnrealDeadlineCloudService)