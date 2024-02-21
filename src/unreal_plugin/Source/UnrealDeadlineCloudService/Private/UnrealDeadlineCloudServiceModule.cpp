// Copyright Epic Games, Inc. All Rights Reserved.

#include "UnrealDeadlineCloudServiceModule.h"
#include "DeadlineCloudJobSettings/DeadlineCloudDeveloperSettings.h"
#include "DeadlineCloudJobSettings/DeadlineCloudSettingsDetails.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJobPresetDetailsCustomization.h"

#include "MovieRenderPipeline/MoviePipelineDeadlineCloudExecutorJob.h"

#define LOCTEXT_NAMESPACE "UnrealDeadlineCloudServiceModule"

void FUnrealDeadlineCloudServiceModule::StartupModule()
{
	FPropertyEditorModule& PropertyModule = FModuleManager::GetModuleChecked<FPropertyEditorModule>("PropertyEditor");
	PropertyModule.RegisterCustomClassLayout(
		UDeadlineCloudDeveloperSettings::StaticClass()->GetFName(),
		FOnGetDetailCustomizationInstance::CreateStatic(&FDeadlineCloudSettingsDetails::MakeInstance)
	);

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