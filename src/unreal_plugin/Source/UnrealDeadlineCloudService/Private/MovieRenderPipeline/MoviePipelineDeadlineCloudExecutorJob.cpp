// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "MovieRenderPipeline/MoviePipelineDeadlineCloudExecutorJob.h"
#include "DetailCategoryBuilder.h"
#include "DetailLayoutBuilder.h"
#include "Async/Async.h"
#include "PythonAPILibraries/DeadlineCloudJobBundleLibrary.h"
#include "Misc/Paths.h"
#include "Interfaces/IPluginManager.h"
#include "PropertyEditorModule.h"

UMoviePipelineDeadlineCloudExecutorJob::UMoviePipelineDeadlineCloudExecutorJob()
{
	if (GEngine)
	{
		// // If a Job Preset is not already defined, assign the default preset
		if (!JobPreset) {
			JobPreset = CreateDefaultJobPresetFromTemplates(JobPreset);
		}
	}
}

bool UMoviePipelineDeadlineCloudExecutorJob::IsPropertyRowEnabledInMovieRenderJob(const FName& InPropertyPath) const
{
	if (const FPropertyRowEnabledInfo* Match = Algo::FindByPredicate(EnabledPropertyOverrides,
		[&InPropertyPath](const FPropertyRowEnabledInfo& Info)
		{
			return Info.PropertyPath == InPropertyPath;
		}))
	{
		return Match->bIsEnabled;
	}

	return false;
}

void UMoviePipelineDeadlineCloudExecutorJob::SetPropertyRowEnabledInMovieRenderJob(const FName& InPropertyPath, bool bInEnabled)
{
	if (FPropertyRowEnabledInfo* Match = Algo::FindByPredicate(EnabledPropertyOverrides,
		[&InPropertyPath](const FPropertyRowEnabledInfo& Info)
		{
			return Info.PropertyPath == InPropertyPath;
		}))
	{
		Match->bIsEnabled = bInEnabled;
	}
	else
	{
		EnabledPropertyOverrides.Add({ InPropertyPath, bInEnabled });
	}
}

void UMoviePipelineDeadlineCloudExecutorJob::GetPresetStructWithOverrides(UStruct* InStruct, const void* InContainer, void* OutContainer) const
{
	for (TFieldIterator<FProperty> PropIt(InStruct, EFieldIteratorFlags::IncludeSuper); PropIt; ++PropIt)
	{
		const FProperty* Property = *PropIt;
		if (!Property)
		{
			continue;
		}

		const FName PropertyPath = *Property->GetPathName();

		if (!IsPropertyRowEnabledInMovieRenderJob(PropertyPath))
		{
			continue;
		}

		// Get Override Property Value
		const void* OverridePropertyValuePtr = Property->ContainerPtrToValuePtr<void>(InContainer);

		void* ReturnPropertyValuePtr = Property->ContainerPtrToValuePtr<void>(OutContainer);
		Property->CopyCompleteValue(ReturnPropertyValuePtr, OverridePropertyValuePtr);

	}
}

FDeadlineCloudJobPresetStruct UMoviePipelineDeadlineCloudExecutorJob::GetDeadlineJobPresetStructWithOverrides() const
{
	// Start with preset properties
	FDeadlineCloudJobPresetStruct ReturnValue = JobPreset->JobPresetStruct;

	GetPresetStructWithOverrides(
		FDeadlineCloudJobSharedSettingsStruct::StaticStruct(),
		&PresetOverrides.JobSharedSettings,
		&ReturnValue.JobSharedSettings
	);

	GetPresetStructWithOverrides(
		FDeadlineCloudHostRequirementsStruct::StaticStruct(),
		&PresetOverrides.HostRequirements,
		&ReturnValue.HostRequirements
	);

	GetPresetStructWithOverrides(
		FDeadlineCloudFileAttachmentsStruct::StaticStruct(),
		&PresetOverrides.JobAttachments.InputFiles,
		&ReturnValue.JobAttachments.InputFiles
	);

	GetPresetStructWithOverrides(
		FDeadlineCloudDirectoryAttachmentsStruct::StaticStruct(),
		&PresetOverrides.JobAttachments.InputDirectories,
		&ReturnValue.JobAttachments.InputDirectories
	);

	GetPresetStructWithOverrides(
		FDeadlineCloudDirectoryAttachmentsStruct::StaticStruct(),
		&PresetOverrides.JobAttachments.OutputDirectories,
		&ReturnValue.JobAttachments.OutputDirectories
	);
	return ReturnValue;
}


FDeadlineCloudJobParametersArray UMoviePipelineDeadlineCloudExecutorJob::GetParameterDefinitionWithOverrides() const
{
	// Start with preset properties
	FDeadlineCloudJobParametersArray ReturnValue = JobPreset->ParameterDefinition;
	GetPresetStructWithOverrides(
		FDeadlineCloudJobParametersArray::StaticStruct(),
		&ParameterDefinitionOverrides.Parameters,
		&ReturnValue.Parameters
	);

	return ReturnValue;

}


void UMoviePipelineDeadlineCloudExecutorJob::UpdateAttachmentFields()
{
	if (PresetOverrides.JobAttachments.InputFiles.bShowAutoDetected)
	{
		this->CollectDependencies();
	}
	else
	{
		PresetOverrides.JobAttachments.InputFiles.AutoDetected.Paths.Empty();
	}
}

void UMoviePipelineDeadlineCloudExecutorJob::PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent)
{
	// Check if we changed the job Preset an update the override details
	if (const FName PropertyName = PropertyChangedEvent.GetPropertyName(); PropertyName == "JobPreset")
	{
		const UDeadlineCloudJob* SelectedJobPreset = this->JobPreset;

		if (!SelectedJobPreset)
		{
			this->JobPreset = CreateDefaultJobPresetFromTemplates(JobPreset);
			SelectedJobPreset = this->JobPreset;
		}

		this->PresetOverrides.HostRequirements = SelectedJobPreset->JobPresetStruct.HostRequirements;
		this->PresetOverrides.JobSharedSettings = SelectedJobPreset->JobPresetStruct.JobSharedSettings;

		this->PresetOverrides.JobAttachments.InputFiles.Files =
			SelectedJobPreset->JobPresetStruct.JobAttachments.InputFiles.Files;

		this->PresetOverrides.JobAttachments.InputDirectories.Directories =
			SelectedJobPreset->JobPresetStruct.JobAttachments.InputDirectories.Directories;

		this->PresetOverrides.JobAttachments.OutputDirectories.Directories =
			SelectedJobPreset->JobPresetStruct.JobAttachments.OutputDirectories.Directories;

		this->ParameterDefinitionOverrides.Parameters =
			SelectedJobPreset->ParameterDefinition.Parameters;

		this->StepsOverrides = GetStepsToOverride(SelectedJobPreset);
		this->EnvironmentsOverrides = GetEnvironmentsToOverride(SelectedJobPreset);
		// Update MRQ widget request
		if (OnRequestDetailsRefresh.IsBound())
		{
			OnRequestDetailsRefresh.Execute();
		}
	}

	UE_LOG(LogTemp, Log, TEXT("Deadline Cloud job changed: %s"),
		*PropertyChangedEvent.Property->GetPathName());
}

void UMoviePipelineDeadlineCloudExecutorJob::CollectDependencies()
{
	UE_LOG(LogTemp, Log, TEXT("MoviePipelineDeadlineCloudExecutorJob :: Collecting dependencies"));
	PresetOverrides.JobAttachments.InputFiles.AutoDetected.Paths.Empty();
	AsyncTask(ENamedThreads::GameThread, [this]()
		{
			auto& DependencyFiles = PresetOverrides.JobAttachments.InputFiles.AutoDetected.Paths;
			TArray<FString> FilePaths;
			if (auto Library = UDeadlineCloudJobBundleLibrary::Get())
			{
				FilePaths = Library->GetJobDependencies(this);
			}
			else
			{
				UE_LOG(LogTemp, Error, TEXT("Error get DeadlineCloudJobBundleLibrary"));
			}
			for (auto FilePath : FilePaths)
			{
				FFilePath Item;
				Item.FilePath = FilePath;
				DependencyFiles.Add(Item);
			}
		});
	UE_LOG(LogTemp, Log, TEXT("MoviePipelineDeadlineCloudExecutorJob :: Collecting dependencies"));
	PresetOverrides.JobAttachments.InputFiles.AutoDetected.Paths.Empty();
	AsyncTask(ENamedThreads::GameThread, [this]()
		{
			auto& DependencyFiles = PresetOverrides.JobAttachments.InputFiles.AutoDetected.Paths;
			TArray<FString> FilePaths = UDeadlineCloudJobBundleLibrary::Get()->GetJobDependencies(this);
			for (auto FilePath : FilePaths)
			{
				FFilePath Item;
				Item.FilePath = FilePath;
				DependencyFiles.Add(Item);
			}
		});
}

void UMoviePipelineDeadlineCloudExecutorJob::UpdateInputFilesProperty()
{
	if (PresetOverrides.JobAttachments.InputFiles.bShowAutoDetected)
	{
		this->CollectDependencies();
	}
	else
	{
		PresetOverrides.JobAttachments.InputFiles.AutoDetected.Paths.Empty();
	}
}

void UMoviePipelineDeadlineCloudExecutorJob::PostEditChangeChainProperty(FPropertyChangedChainEvent& PropertyChangedEvent)
{
	Super::PostEditChangeChainProperty(PropertyChangedEvent);
	UE_LOG(LogTemp, Log, TEXT("Show auto detected: %s"), *GET_MEMBER_NAME_CHECKED(FDeadlineCloudFileAttachmentsStruct, bShowAutoDetected).ToString());
	if (PropertyChangedEvent.GetPropertyName() == "bShowAutoDetected")
	{
		static const FName InputFilesName = GET_MEMBER_NAME_CHECKED(FDeadlineCloudAttachmentsStruct, InputFiles);
		// static const FName InputDirectoriesName = GET_MEMBER_NAME_CHECKED(FDeadlineCloudAttachmentsStruct, InputDirectories);
		// static const FName OutputDirectoriesName = GET_MEMBER_NAME_CHECKED(FDeadlineCloudAttachmentsStruct, OutputDirectories);

		const FProperty* Property = PropertyChangedEvent.PropertyChain.GetActiveNode()->GetPrevNode()->GetValue();
		if (Property->GetFName() == InputFilesName)
		{
			UpdateInputFilesProperty();
		}
		return;
	}

	static const FName MapName = GET_MEMBER_NAME_CHECKED(UMoviePipelineDeadlineCloudExecutorJob, Map);
	static const FName SequenceName = GET_MEMBER_NAME_CHECKED(UMoviePipelineDeadlineCloudExecutorJob, Sequence);
	if (PropertyChangedEvent.GetPropertyName() == MapName || PropertyChangedEvent.GetPropertyName() == SequenceName)
	{
		UpdateInputFilesProperty();
	}
	UE_LOG(LogTemp, Log, TEXT("Changed property name: %s"), *PropertyChangedEvent.GetPropertyName().ToString());
}

TArray<FString> UMoviePipelineDeadlineCloudExecutorJob::GetCpuArchitectures()
{
	if (auto Library = UDeadlineCloudJobBundleLibrary::Get())
	{
		return Library->GetCpuArchitectures();
	}
	else
	{
		UE_LOG(LogTemp, Error, TEXT("Error get DeadlineCloudJobBundleLibrary"));
	}
	return {};
}

TArray<FString> UMoviePipelineDeadlineCloudExecutorJob::GetOperatingSystems()
{
	if (auto Library = UDeadlineCloudJobBundleLibrary::Get())
	{
		return Library->GetOperatingSystems();
	}
	else
	{
		UE_LOG(LogTemp, Error, TEXT("Error get DeadlineCloudJobBundleLibrary"));
	}
	return {};
}

TArray<FString> UMoviePipelineDeadlineCloudExecutorJob::GetJobInitialStateOptions()
{
	if (auto Library = UDeadlineCloudJobBundleLibrary::Get())
	{
		return Library->GetJobInitialStateOptions();
	}
	else
	{
		UE_LOG(LogTemp, Error, TEXT("Error get DeadlineCloudJobBundleLibrary"));
	}
	return {};
}


UDeadlineCloudRenderJob* UMoviePipelineDeadlineCloudExecutorJob::CreateDefaultJobPresetFromTemplates(UDeadlineCloudRenderJob* Preset)
{
	if (Preset == nullptr)
	{
		Preset = NewObject<UDeadlineCloudRenderJob>();

		FString DefaultTemplate = "/Content/Python/openjd_templates/render_job.yml";
		FString StepTemplate = "/Content/Python/openjd_templates/render_step.yml";
		FString EnvTemplate = "/Content/Python/openjd_templates/launch_ue_environment.yml";

		FString  PluginContentDir = IPluginManager::Get().FindPlugin(TEXT("UnrealDeadlineCloudService"))->GetBaseDir();

		FString PathToJobTemplate = FPaths::Combine(FPaths::ConvertRelativePathToFull(PluginContentDir), DefaultTemplate);
		FPaths::NormalizeDirectoryName(PathToJobTemplate);
		Preset->PathToTemplate.FilePath = PathToJobTemplate;
		Preset->OpenJobFile(PathToJobTemplate);

		TObjectPtr <UDeadlineCloudRenderStep> PresetStep;
		PresetStep = NewObject<UDeadlineCloudRenderStep>();
		FString PathToStepTemplate = FPaths::Combine(FPaths::ConvertRelativePathToFull(PluginContentDir), StepTemplate);
		FPaths::NormalizeDirectoryName(PathToStepTemplate);
		PresetStep->PathToTemplate.FilePath = PathToStepTemplate;
		PresetStep->OpenStepFile(PathToStepTemplate);
		Preset->Steps.Add(PresetStep);

		UDeadlineCloudEnvironment* PresetEnv;
		PresetEnv = NewObject<UDeadlineCloudEnvironment>();
		FString PathToEnvTemplate = FPaths::Combine(FPaths::ConvertRelativePathToFull(PluginContentDir), EnvTemplate);
		FPaths::NormalizeDirectoryName(PathToEnvTemplate);
		PresetEnv->PathToTemplate.FilePath = PathToEnvTemplate;
		PresetEnv->OpenEnvFile(PathToEnvTemplate);
		Preset->Environments.Add(PresetEnv);

	}
	return Preset;
}

TArray<FDeadlineCloudStepOverride> UMoviePipelineDeadlineCloudExecutorJob::GetStepsToOverride(const UDeadlineCloudJob* Preset)
{
	TArray<FDeadlineCloudStepOverride> DeadlineStepsOverrides;
	if (Preset)
	{
		const TArray<UDeadlineCloudStep*> SelectedJobSteps = Preset->Steps;
		for (auto step : SelectedJobSteps)
		{
			if (step)
			{
				DeadlineStepsOverrides.Add(step->GetStepDataToOverride());
			}
		}
	}
	return DeadlineStepsOverrides;
}

TArray<FDeadlineCloudEnvironmentOverride> UMoviePipelineDeadlineCloudExecutorJob::GetEnvironmentsToOverride(const UDeadlineCloudJob* Preset)
{
	TArray<FDeadlineCloudEnvironmentOverride> EnvOverrides;
	if (Preset)
	{
		const TArray<UDeadlineCloudEnvironment*> SelectedJobEnvs = Preset->Environments;
		for (auto env : SelectedJobEnvs)
		{
			if (env)
			{
				EnvOverrides.Add(env->GetEnvironmentData());
			}
		}
	}
	return EnvOverrides;
}


TSharedRef<IDetailCustomization> FMoviePipelineDeadlineCloudExecutorJobCustomization::MakeInstance()
{
	return MakeShared<FMoviePipelineDeadlineCloudExecutorJobCustomization>();
}

void FMoviePipelineDeadlineCloudExecutorJobCustomization::CustomizeDetails(IDetailLayoutBuilder& DetailBuilder)
{
	IDetailCategoryBuilder& MrpCategory = DetailBuilder.EditCategory("Movie Render Pipeline");

	TArray<TSharedRef<IPropertyHandle>> OutMrpCategoryProperties;
	MrpCategory.GetDefaultProperties(OutMrpCategoryProperties);

	TArray<TWeakObjectPtr<UObject>> ObjectsBeingCustomized;
	DetailBuilder.GetObjectsBeingCustomized(ObjectsBeingCustomized);

	MrqJob = Cast<UMoviePipelineDeadlineCloudExecutorJob>(ObjectsBeingCustomized[0].Get());
	MrqJob->OnRequestDetailsRefresh.BindLambda([&DetailBuilder]()
		{
			DetailBuilder.ForceRefreshDetails();
		});

	TSharedPtr<IPropertyHandle> JobPropertyHandle = DetailBuilder.GetProperty(GET_MEMBER_NAME_CHECKED(UMoviePipelineDeadlineCloudExecutorJob, JobPreset));
	if (!JobPropertyHandle.IsValid()) return;

	if (ObjectsBeingCustomized.Num() > 0)
	{
		UObject* CustomizedObject = ObjectsBeingCustomized[0].Get();
		if (CustomizedObject) {
			if (UMoviePipelineDeadlineCloudExecutorJob* MyMrq = Cast<UMoviePipelineDeadlineCloudExecutorJob>(CustomizedObject))
			{
				FPropertyChangedEvent PropertyChangedEvent(JobPropertyHandle->GetProperty());
				CustomizedObject->PostEditChangeProperty(PropertyChangedEvent);
			}
		}
	}
}