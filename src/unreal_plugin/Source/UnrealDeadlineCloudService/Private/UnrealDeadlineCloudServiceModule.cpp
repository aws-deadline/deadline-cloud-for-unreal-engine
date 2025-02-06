// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "UnrealDeadlineCloudServiceModule.h"
#include "DeadlineCloudJobSettings/DeadlineCloudDeveloperSettings.h"
#include "DeadlineCloudJobSettings/DeadlineCloudSettingsDetails.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJobPresetDetailsCustomization.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJobDetails.h"
#include "DeadlineCloudJobSettings/DeadlineCloudStepDetails.h"
#include "DeadlineCloudJobSettings/DeadlineCloudEnvironmentDetails.h"

#include "MovieRenderPipeline/MoviePipelineDeadlineCloudExecutorJob.h"

#define LOCTEXT_NAMESPACE "UnrealDeadlineCloudServiceModule"

void FUnrealDeadlineCloudServiceModule::StartupModule()
{
    FPropertyEditorModule& PropertyModule = FModuleManager::GetModuleChecked<FPropertyEditorModule>("PropertyEditor");
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

	PropertyModule.RegisterCustomClassLayout(
		UDeadlineCloudEnvironment::StaticClass()->GetFName(),
		FOnGetDetailCustomizationInstance::CreateStatic(&FDeadlineCloudEnvironmentDetails::MakeInstance));



	PropertyModule.RegisterCustomClassLayout(
		UMoviePipelineDeadlineCloudExecutorJob::StaticClass()->GetFName(),
		FOnGetDetailCustomizationInstance::CreateStatic(&FMoviePipelineDeadlineCloudExecutorJobCustomization::MakeInstance)
	);

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

	PropertyModule.NotifyCustomizationModuleChanged();
}

void FUnrealDeadlineCloudServiceModule::ShutdownModule()
{
	// This function may be called during shutdown to clean up your module.  For modules that support dynamic reloading,
	// we call this function before unloading the module.
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FUnrealDeadlineCloudServiceModule, UnrealDeadlineCloudServiceEditorMode)