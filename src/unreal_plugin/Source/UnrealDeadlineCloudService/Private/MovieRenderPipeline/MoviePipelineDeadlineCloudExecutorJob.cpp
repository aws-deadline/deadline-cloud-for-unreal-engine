// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "MovieRenderPipeline/MoviePipelineDeadlineCloudExecutorJob.h"
#include "DetailCategoryBuilder.h"
#include "DetailLayoutBuilder.h"
#include "Async/Async.h"
#include "PythonAPILibraries/DeadlineCloudJobBundleLibrary.h"
#include "Misc/Paths.h"
#include "Interfaces/IPluginManager.h"
#include "PropertyEditorModule.h"
#include "IDetailChildrenBuilder.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "DeadlineCloudJobSettings/DeadlineCloudDetailsWidgetsHelper.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJobPresetDetailsCustomization.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"

UMoviePipelineDeadlineCloudExecutorJob::UMoviePipelineDeadlineCloudExecutorJob()
{
	UE_LOG(LogTemp, Display, TEXT("DeadlineCloud: UMoviePipelineDeadlineCloudExecutorJob constructor called"));
	if (GEngine)
	{
		// If a Job Preset is not already defined, assign the default preset
		if (!JobPreset) {
			UE_LOG(LogTemp, Display, TEXT("DeadlineCloud: Assigning the default JobPreset"));
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

void UMoviePipelineDeadlineCloudExecutorJob::PostInitProperties()
{
	UE_LOG(LogTemp, Display, TEXT("DeadlineCloud: PostInitProperties called"));
	Super::PostInitProperties();

#if WITH_EDITOR
	if (!HasAnyFlags(RF_ClassDefaultObject)){
		JobPresetChanged();
	}
#endif // WITH_EDITOR
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
		&JobTemplateOverrides.Parameters,
		&ReturnValue.Parameters
	);

	return ReturnValue;

}


void UMoviePipelineDeadlineCloudExecutorJob::UpdateAttachmentFields()
{
	UpdateInputFilesProperty();
	UpdateInputDirectoriesProperty();
}

void UMoviePipelineDeadlineCloudExecutorJob::JobPresetChanged()
{
	UE_LOG(LogTemp, Display, TEXT("DeadlineCloud: JobPresetChanged called"));
	const UDeadlineCloudJob* SelectedJobPreset = this->JobPreset;

	if (!SelectedJobPreset)
	{
		UE_LOG(LogTemp, Display, TEXT("DeadlineCloud: JobPreset is null, creating default in JobPresetChanged"));
		this->JobPreset = CreateDefaultJobPresetFromTemplates(JobPreset);
		SelectedJobPreset = this->JobPreset;
	} else {
		UE_LOG(LogTemp, Display, TEXT("DeadlineCloud: JobPreset exists in JobPresetChanged"));
	}

	this->PresetOverrides.HostRequirements = SelectedJobPreset->JobPresetStruct.HostRequirements;
	this->PresetOverrides.JobSharedSettings = SelectedJobPreset->JobPresetStruct.JobSharedSettings;

	this->PresetOverrides.JobAttachments.InputFiles.Files =
		SelectedJobPreset->JobPresetStruct.JobAttachments.InputFiles.Files;

	this->PresetOverrides.JobAttachments.InputDirectories.Directories =
		SelectedJobPreset->JobPresetStruct.JobAttachments.InputDirectories.Directories;

	this->PresetOverrides.JobAttachments.OutputDirectories.Directories =
		SelectedJobPreset->JobPresetStruct.JobAttachments.OutputDirectories.Directories;

	this->JobTemplateOverrides.Parameters = SelectedJobPreset->ParameterDefinition.Parameters;

	this->JobTemplateOverrides.StepsOverrides = GetStepsToOverride(SelectedJobPreset);
	this->JobTemplateOverrides.EnvironmentsOverrides = GetEnvironmentsToOverride(SelectedJobPreset);
}

void UMoviePipelineDeadlineCloudExecutorJob::PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent)
{
	
	if (PropertyChangedEvent.Property)
	{
	// Check if we changed the job Preset an update the override details
	if (const FName PropertyName = PropertyChangedEvent.GetPropertyName(); PropertyName == "JobPreset")
	{
		JobPresetChanged();

		// Update MRQ widget request
		if (OnRequestDetailsRefresh.IsBound())
		{
			OnRequestDetailsRefresh.Execute();
		}
	}

	UE_LOG(LogTemp, Display, TEXT("Deadline Cloud job changed: %s"),
		*PropertyChangedEvent.Property->GetPathName());
	}
}

 bool UMoviePipelineDeadlineCloudExecutorJob::IsAssetFileValid(const FString& FilePath)
{
	// Check file on disk
	if (!FPaths::FileExists(FilePath))
	{
		UE_LOG(LogTemp, Warning, TEXT("Dependency file missing: %s"), *FilePath);
		return false;
	}

	// Check convert to asset path
	FString LongPackagePath;
	if (!FPackageName::TryConvertFilenameToLongPackageName(FilePath, LongPackagePath))
	{
		UE_LOG(LogTemp, Warning, TEXT("Could not convert to package path: %s"), *FilePath);
		return false;
	}

	// Check AssetRegistry
	FAssetRegistryModule& AssetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	FAssetData AssetData = AssetRegistryModule.Get().GetAssetByObjectPath(*LongPackagePath);

	if (!AssetData.IsValid())
	{
		UE_LOG(LogTemp, Warning, TEXT("AssetRegistry has no info about: %s (from file %s)"), *LongPackagePath, *FilePath);
		return false;
	}

	return true;
}

 bool UMoviePipelineDeadlineCloudExecutorJob::IsAssetDirectoryValid(const FString& DirectoryPath)
 {
	 // Check directory on disk
	 if (!FPaths::DirectoryExists(DirectoryPath))
	 {
		 UE_LOG(LogTemp, Warning, TEXT("Dependency directory missing: %s"), *DirectoryPath);
		 return false;
	 }
	 return true;
 }

void UMoviePipelineDeadlineCloudExecutorJob::CollectDependencies()
{

	if (GEngine)
	{
		UE_LOG(LogTemp, Display, TEXT("Running Garbage Collection before dependency update..."));
		GEngine->ForceGarbageCollection();
		
	}
	UE_LOG(LogTemp, Display, TEXT("MoviePipelineDeadlineCloudExecutorJob :: Collecting dependencies"));
	PresetOverrides.JobAttachments.InputFiles.AutoDetected.Paths.Empty();
	AsyncTask(ENamedThreads::GameThread, [this]()
		{
			auto& DependencyFiles = PresetOverrides.JobAttachments.InputFiles.AutoDetected.Paths;
			TArray<FString> FilePaths;
			if (auto Library = UDeadlineCloudJobBundleLibrary::Get())
			{
				FilePaths = Library->GetJobDependencies(this);
				for (auto FilePath : FilePaths)
				{
					if (!IsAssetFileValid(FilePath))
					{
						continue;
					}
					FFilePath Item;
					Item.FilePath = FilePath;
					DependencyFiles.Add(Item);
				}
				
				UE_LOG(LogTemp, Display, TEXT("Added %d dependency files:"), DependencyFiles.Num());
			}
			else
			{
				UE_LOG(LogTemp, Error, TEXT("Error get DeadlineCloudJobBundleLibrary"));
			}

		});
}

void UMoviePipelineDeadlineCloudExecutorJob::CollectPluginsDependencies()
{
	PresetOverrides.JobAttachments.InputDirectories.AutoDetectedDirectories.Paths.Empty();
	AsyncTask(ENamedThreads::GameThread, [this]()
		{
			auto& Plugins = PresetOverrides.JobAttachments.InputFiles.AutoDetected.Paths;
			TArray<FString> Paths;
			if (auto Library = UDeadlineCloudJobBundleLibrary::Get())
			{
				Paths = Library->GetPluginsDependencies();
				for (const auto& Path : Paths)
				{
					if (!IsAssetDirectoryValid(Path))
					{
						continue;
					}
					FDirectoryPath Item;
					Item.Path = Path;
					PresetOverrides.JobAttachments.InputDirectories.AutoDetectedDirectories.Paths.Add(Item);
				}

				UE_LOG(LogTemp, Display, TEXT("Added %d dependency directories:"), Plugins.Num());
			}
			else
			{
				UE_LOG(LogTemp, Error, TEXT("Error get DeadlineCloudJobBundleLibrary"));
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

void UMoviePipelineDeadlineCloudExecutorJob::UpdateInputDirectoriesProperty()
{
	if (PresetOverrides.JobAttachments.InputDirectories.bShowAutoDetected)
	{
		CollectPluginsDependencies();
	}
	else
	{
		PresetOverrides.JobAttachments.InputDirectories.AutoDetectedDirectories.Paths.Empty();
	}
}

void UMoviePipelineDeadlineCloudExecutorJob::PostEditChangeChainProperty(FPropertyChangedChainEvent& PropertyChangedEvent)
{
	Super::PostEditChangeChainProperty(PropertyChangedEvent);
	UE_LOG(LogTemp, Display, TEXT("Show auto detected: %s"), *GET_MEMBER_NAME_CHECKED(FDeadlineCloudFileAttachmentsStruct, bShowAutoDetected).ToString());
	if (PropertyChangedEvent.GetPropertyName() == "bShowAutoDetected")
	{
		static const FName InputFilesName = GET_MEMBER_NAME_CHECKED(FDeadlineCloudAttachmentsStruct, InputFiles);
		static const FName InputDirectoriesName = GET_MEMBER_NAME_CHECKED(FDeadlineCloudAttachmentsStruct, InputDirectories);
		// static const FName OutputDirectoriesName = GET_MEMBER_NAME_CHECKED(FDeadlineCloudAttachmentsStruct, OutputDirectories);

		const FProperty* Property = PropertyChangedEvent.PropertyChain.GetActiveNode()->GetPrevNode()->GetValue();
		if (Property->GetFName() == InputFilesName)
		{
			UpdateInputFilesProperty();
		}
		if (Property->GetFName() == InputDirectoriesName)
		{
			UpdateInputDirectoriesProperty();
		}
		return;
	}

	static const FName MapName = GET_MEMBER_NAME_CHECKED(UMoviePipelineDeadlineCloudExecutorJob, Map);
	static const FName SequenceName = GET_MEMBER_NAME_CHECKED(UMoviePipelineDeadlineCloudExecutorJob, Sequence);
	if (PropertyChangedEvent.GetPropertyName() == MapName || PropertyChangedEvent.GetPropertyName() == SequenceName)
	{
		UpdateInputFilesProperty();
	}
	UE_LOG(LogTemp, Display, TEXT("Changed property name: %s"), *PropertyChangedEvent.GetPropertyName().ToString());
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
	UE_LOG(LogTemp, Display, TEXT("DeadlineCloud: CreateDefaultJobPresetFromTemplates called"));

	if (Preset == nullptr)
	{
		UE_LOG(LogTemp, Display, TEXT("DeadlineCloud: Creating new UDeadlineCloudRenderJob"));

		Preset = NewObject<UDeadlineCloudRenderJob>();

		FString DefaultTemplate = "/Content/Python/openjd_templates/render_job.yml";
		FString StepTemplate = "/Content/Python/openjd_templates/render_step.yml";
		FString EnvTemplate = "/Content/Python/openjd_templates/launch_ue_environment.yml";

		FString PluginContentDir = IPluginManager::Get().FindPlugin(TEXT("UnrealDeadlineCloudService"))->GetBaseDir();

		FString PathToJobTemplate = FPaths::Combine(FPaths::ConvertRelativePathToFull(PluginContentDir), DefaultTemplate);
		FPaths::NormalizeDirectoryName(PathToJobTemplate);
		UE_LOG(LogTemp, Display, TEXT("DeadlineCloud: Looking for job template at: %s"), *PathToJobTemplate);

		UE_LOG(LogTemp, Display, TEXT("DeadlineCloud: Job template found, opening file"));
		Preset->PathToTemplate.FilePath = PathToJobTemplate;
		Preset->OpenJobFile(PathToJobTemplate);

		TObjectPtr <UDeadlineCloudRenderStep> PresetStep;
		PresetStep = NewObject<UDeadlineCloudRenderStep>();
		FString PathToStepTemplate = FPaths::Combine(FPaths::ConvertRelativePathToFull(PluginContentDir), StepTemplate);
		FPaths::NormalizeDirectoryName(PathToStepTemplate);
		UE_LOG(LogTemp, Display, TEXT("DeadlineCloud: Looking for step template at: %s"), *PathToStepTemplate);

		PresetStep->PathToTemplate.FilePath = PathToStepTemplate;
		PresetStep->OpenStepFile(PathToStepTemplate);
		Preset->Steps.Add(PresetStep);

		UDeadlineCloudEnvironment* PresetEnv;
		PresetEnv = NewObject<UDeadlineCloudEnvironment>();
		FString PathToEnvTemplate = FPaths::Combine(FPaths::ConvertRelativePathToFull(PluginContentDir), EnvTemplate);
		FPaths::NormalizeDirectoryName(PathToEnvTemplate);
		UE_LOG(LogTemp, Display, TEXT("DeadlineCloud: Looking for env template at: %s"), *PathToEnvTemplate);

		PresetEnv->PathToTemplate.FilePath = PathToEnvTemplate;
		PresetEnv->OpenEnvFile(PathToEnvTemplate);
		Preset->Environments.Add(PresetEnv);
		UE_LOG(LogTemp, Display, TEXT("DeadlineCloud: CreateDefaultJobPresetFromTemplates completed successfully"));
	}
	return Preset;
}

TArray<FDeadlineCloudStepOverride> UMoviePipelineDeadlineCloudExecutorJob::GetStepsToOverride(const UDeadlineCloudJob* Preset)
{
	TArray<FDeadlineCloudStepOverride> DeadlineStepsOverrides;
	if (Preset)
	{
		const TArray<UDeadlineCloudStep*> SelectedJobSteps = Preset->Steps;
		for (auto Step : SelectedJobSteps)
		{
			if (Step)
			{
				auto StepData = Step->GetStepDataToOverride();

				if (StepData.TaskParameterDefinitions.Parameters.IsEmpty() && StepData.EnvironmentsOverrides.IsEmpty())
				{
					continue;
				}

				DeadlineStepsOverrides.Add(StepData);
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
		for (auto Env : SelectedJobEnvs)
		{
			if (Env)
			{
				auto EnvData = Env->GetEnvironmentData();
				if (EnvData.Variables.Variables.IsEmpty())
				{
					continue;
				}

				EnvOverrides.Add(EnvData);
			}
		}
	}
	return EnvOverrides;
}

bool UMoviePipelineDeadlineCloudExecutorJob::HasEditableParameters(const FDeadlineCloudStepOverride& StepOverride) const
{
	// Check if the step has any parameters in TaskParameterDefinitions
	return StepOverride.TaskParameterDefinitions.Parameters.Num() > 0;
}


TSharedRef<IDetailCustomization> FMoviePipelineDeadlineCloudExecutorJobCustomization::MakeInstance()
{
	return MakeShared<FMoviePipelineDeadlineCloudExecutorJobCustomization>();
}

void FMoviePipelineDeadlineCloudExecutorJobCustomization::CustomizeDetails(IDetailLayoutBuilder& DetailBuilder)
{
	IDetailCategoryBuilder& DeadlineCategory = DetailBuilder.EditCategory("DeadlineCloud");

	TArray<TSharedRef<IPropertyHandle>> OutMrpCategoryProperties;
	DeadlineCategory.GetDefaultProperties(OutMrpCategoryProperties);

	TArray<TWeakObjectPtr<UObject>> ObjectsBeingCustomized;
	DetailBuilder.GetObjectsBeingCustomized(ObjectsBeingCustomized);

	MrqJob = Cast<UMoviePipelineDeadlineCloudExecutorJob>(ObjectsBeingCustomized[0].Get());
	MrqJob->OnRequestDetailsRefresh.BindLambda([&DetailBuilder]()
		{
			DetailBuilder.ForceRefreshDetails();
		});

	for (auto& Property : OutMrpCategoryProperties)
	{
		const FName PropertyName = Property->GetProperty()->GetFName();

		if (PropertyName == GET_MEMBER_NAME_CHECKED(UMoviePipelineDeadlineCloudExecutorJob, JobName))
		{
			DeadlineCategory.AddProperty(Property)
				.CustomWidget()
				.NameContent()
				[
					Property->CreatePropertyNameWidget()
				]
				.ValueContent()
				[
					FDeadlineCloudDetailsWidgetsHelper::CreatePropertyWidgetByType(
						Property, EValueType::STRING, EValueValidationType::JobName
					)
				];
		}
		

		else
		{
			DeadlineCategory.AddProperty(Property);
		}
	}
}