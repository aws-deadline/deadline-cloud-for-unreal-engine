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
#include "DeadlineCloudJobSettings/DeadlineCloudDeveloperSettings.h"
#include "DesktopPlatformModule.h"
#include "Framework/Application/SlateApplication.h"
#include "Factories/DataAssetFactory.h"
#include "AssetToolsModule.h"
#include "PackageTools.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "PythonAPILibraries/DeadlineCloudPreGuiHookLibrary.h"
#include "ObjectTools.h"
#include "UObject/SavePackage.h"
#include "Serialization/ArchiveReplaceObjectRef.h"
#include "Framework/MetaData/DriverMetaData.h"
#include "Framework/Notifications/NotificationManager.h"
#include "Widgets/Notifications/SNotificationList.h"

namespace
{
	inline bool MatchesSourcePath(const FSoftObjectPath& OverridePath, const UObject* SourceObj)
	{
		return OverridePath.IsValid() && OverridePath == FSoftObjectPath(SourceObj);
	}

}

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

	return true;
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
	if (!HasAnyFlags(RF_ClassDefaultObject))
	{
		JobPresetChanged();
	}
#endif // WITH_EDITOR
}

void UMoviePipelineDeadlineCloudExecutorJob::SaveAsJobPreset(FString& FolderPath, FString& BaseName, bool bSetAsDefault)
{
	TMap<UDataAsset*, FString> ObjectsNames;

	UMoviePipelineDeadlineCloudExecutorJob::GeneratePresetObjectsNames(this, FolderPath, BaseName, ObjectsNames);

	TArray<UDataAsset*> ResultAssets;
	UDeadlineCloudRenderJob* ResultJob = nullptr;
	for (const auto& Name : ObjectsNames)
	{
		FString PackageName = Name.Value;

		auto Asset = Name.Key;

		const FString AssetName  = FPackageName::GetLongPackageAssetName(PackageName);
		const FString ObjectPath = PackageName + TEXT(".") + AssetName;

		FAssetRegistryModule& AssetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
		FAssetData ExistingAsset = AssetRegistryModule.Get().GetAssetByObjectPath(FSoftObjectPath(ObjectPath));

		if (ExistingAsset.IsValid())
		{
			// Delete existing asset with the same path
			ObjectTools::DeleteAssets({ ExistingAsset }, false);
		}
		
		UPackage* Pkg = CreatePackage(*PackageName);

		UDataAsset* NewObj = DuplicateObject<UDataAsset>(Asset, Pkg, *FPaths::GetBaseFilename(PackageName));
		if (!NewObj)
		{
			UE_LOG(LogTemp, Error, TEXT("Could not duplicate asset: %s"), *PackageName);
			return;
		}

		NewObj->SetFlags(RF_Public | RF_Standalone);
		FAssetRegistryModule::AssetCreated(NewObj);

		if (auto Job = Cast<UDeadlineCloudRenderJob>(NewObj))
		{
			CopyJobOverrides(Job);
			ResultJob = Job;
		}
		else if (auto Step = Cast<UDeadlineCloudStep>(NewObj))
		{
			CopyStepOverrides(Step, Cast<UDeadlineCloudStep>(Asset));
		}
		else if (auto Env = Cast<UDeadlineCloudEnvironment>(NewObj))
		{
			CopyEnvironmentOverrides(Env, Cast<UDeadlineCloudEnvironment>(Asset));
		}
		else if (auto HostReq = Cast<UDeadlineCloudHostRequirements>(NewObj))
		{
			CopyHostRequirementsOverrides(HostReq, Cast<UDeadlineCloudHostRequirements>(Asset));
		}

		Pkg->MarkPackageDirty();
		FString FilePath = FPackageName::LongPackageNameToFilename(
					PackageName, FPackageName::GetAssetPackageExtension());

		FSavePackageArgs SaveArgs = FSavePackageArgs();
		SaveArgs.TopLevelFlags = EObjectFlags::RF_Public | EObjectFlags::RF_Standalone;
		SaveArgs.Error = GError;
		SaveArgs.bWarnOfLongFilename = true;

		UPackage::SavePackage(
			Pkg, NewObj, *FilePath, SaveArgs);

		ResultAssets.Add(NewObj);
	}

	// replace old references with new ones
	FixReferencesAfterDuplication(ObjectsNames, ResultAssets);

	if (bSetAsDefault)
	{
		// Set as default in settings
		UDeadlineCloudDeveloperSettings::GetMutable()->DefaultJobPreset = ResultJob;
	}

	// Update current job to use the new preset
	Modify();
	JobPreset = ResultJob;
	if (OnRequestDetailsRefresh.IsBound())
	{
		OnRequestDetailsRefresh.Execute();
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
	if (!IsValid(JobPreset))
	{
		UE_LOG(LogTemp, Display, TEXT("DeadlineCloud: JobPreset is null, creating default in JobPresetChanged"));
		JobPreset = CreateDefaultJobPresetFromTemplates(JobPreset);
	} else {
		UE_LOG(LogTemp, Display, TEXT("DeadlineCloud: JobPreset exists in JobPresetChanged"));
	}

	ReloadDataFromJobPreset();

	if (IsUsingDefaultPreset())
	{
		ApplyLastUsedTo(this);
	}
}

void UMoviePipelineDeadlineCloudExecutorJob::PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent)
{
	Super::PostEditChangeProperty(PropertyChangedEvent);

	if (!HasAnyFlags(RF_ClassDefaultObject))
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

			if (IsUsingDefaultPreset())
			{
				SaveLastUsedFrom(this);
			}

			UE_LOG(LogTemp, Display, TEXT("Deadline Cloud job changed: %s"),
				*PropertyChangedEvent.Property->GetPathName());
		}
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

	const FString AssetName  = FPackageName::GetLongPackageAssetName(LongPackagePath);
	const FString ObjectPath = LongPackagePath + TEXT(".") + AssetName;

	// Check AssetRegistry
	FAssetRegistryModule& AssetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	FAssetData AssetData = AssetRegistryModule.Get().GetAssetByObjectPath(FSoftObjectPath(ObjectPath));

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

void UMoviePipelineDeadlineCloudExecutorJob::ReloadDataFromJobPreset()
{
	PresetOverrides.JobSharedSettings = JobPreset->JobPresetStruct.JobSharedSettings;

	PresetOverrides.JobAttachments.InputFiles.Files =
		JobPreset->JobPresetStruct.JobAttachments.InputFiles.Files;

	PresetOverrides.JobAttachments.InputDirectories.Directories =
		JobPreset->JobPresetStruct.JobAttachments.InputDirectories.Directories;

	PresetOverrides.JobAttachments.OutputDirectories.Directories =
		JobPreset->JobPresetStruct.JobAttachments.OutputDirectories.Directories;

	JobTemplateOverrides.Parameters = JobPreset->GetParametersDataToOverride();
	JobTemplateOverrides.StepsOverrides = GetStepsToOverride(JobPreset);
	JobTemplateOverrides.EnvironmentsOverrides = GetEnvironmentsToOverride(JobPreset);

	// Pre-GUI hooks: inherit the source preset's applied-state alongside the values just copied above.
	// If a data-asset panel hook already applied to JobPreset (bPreGuiHooksApplied), the values now in
	// PresetOverrides / JobTemplateOverrides are already hooked, so the MRQ panel must NOT re-run the
	// hook — otherwise an "adjust" hook (e.g. +10 priority) applies twice for one submission. If the
	// preset is un-hooked (the common MRQ workflow, or a freshly-picked preset), this re-arms the latch
	// so the next panel build applies the hook onto the freshly-loaded values; without it, a preset
	// change would wipe the previously-applied hook values while the latch blocked re-application.
	bPreGuiHooksApplied = JobPreset->bPreGuiHooksApplied;


	UDeadlineCloudJobBundleLibrary* Library = UDeadlineCloudJobBundleLibrary::Get();
	if (Library)
	{
		JobTemplateOverrides.Parameters = Library->ValidateMrqJobParameters(JobTemplateOverrides.Parameters);
	}
	else
	{
		UE_LOG(LogTemp, Error, TEXT("Error get DeadlineCloudJobBundleLibrary"));
	}
}

void UMoviePipelineDeadlineCloudExecutorJob::GetPresetObjectsNames(const UMoviePipelineDeadlineCloudExecutorJob* MrqJob, TMap<UDataAsset*, FString>& OutPresetPackageNames)
{
	if (!MrqJob || !MrqJob->JobPreset)
	{
		return;
	}

	FString PackageName = FSoftObjectPath(MrqJob->JobPreset).GetLongPackageName();
	OutPresetPackageNames.Add(MrqJob->JobPreset, PackageName);
	for (auto Step : MrqJob->JobPreset->Steps)
	{
		if (IsValid(Step))
		{
			PackageName = FSoftObjectPath(Step).GetLongPackageName();
			OutPresetPackageNames.Add(Step, PackageName);

			for (auto Env : Step->Environments)
			{
				if (IsValid(Env))
				{
					PackageName = FSoftObjectPath(Env).GetLongPackageName();
					OutPresetPackageNames.Add(Env, PackageName);
				}
			}

			if (IsValid(Step->HostRequirements))
			{
				PackageName = FSoftObjectPath(Step->HostRequirements).GetLongPackageName();
				OutPresetPackageNames.Add(Step->HostRequirements, PackageName);
			}
		}
	}

	for (auto Env : MrqJob->JobPreset->Environments)
	{
		if (IsValid(Env))
		{
			PackageName = FSoftObjectPath(Env).GetLongPackageName();
			OutPresetPackageNames.Add(Env, PackageName);
		}
	}
}

void UMoviePipelineDeadlineCloudExecutorJob::GeneratePresetObjectsNames(
	const UMoviePipelineDeadlineCloudExecutorJob* MrqJob,
	const FString& FolderPath, const FString& BaseName,
	TMap<UDataAsset*, FString>& OutPresetPackageNames
)
{
	if (!MrqJob || !MrqJob->JobPreset)
	{
		return;
	}

	FString NewName = UPackageTools::SanitizePackageName(FolderPath + TEXT("/") + BaseName);

	OutPresetPackageNames.Add(MrqJob->JobPreset, NewName);

	uint32 StepIndex = 1;
	for (const auto& Step : MrqJob->JobPreset->Steps)
	{
		if (IsValid(Step))
		{
			if (OutPresetPackageNames.Contains(Step))
			{
				// Already added
				continue;
			}

			FString StepName = NewName + "_Step" + FString::FromInt(StepIndex);
			OutPresetPackageNames.Add(Step, StepName);
			StepIndex++;

			// Add step environments
			uint32 StepEnvIndex = 1;
			for (const auto& StepEnv : Step->Environments)
			{
				if (IsValid(StepEnv))
				{
					if (OutPresetPackageNames.Contains(StepEnv))
					{
						// Already added
						continue;
					}
					FString EnvName = StepName + "_Environment" + FString::FromInt(StepEnvIndex);
					OutPresetPackageNames.Add(StepEnv, EnvName);
					StepEnvIndex++;
				}
			}

			if (Step->HostRequirements)
			{
				if (!OutPresetPackageNames.Contains(Step->HostRequirements))
				{
					FString HostReqName = StepName + "_HostRequirements";
					OutPresetPackageNames.Add(Step->HostRequirements, HostReqName);
				}
			}
		}
	}

	// Add job environments
	uint32 EnvIndex = 1;
	for (const auto& Env : MrqJob->JobPreset->Environments)
	{
		if (IsValid(Env))
		{
			if (OutPresetPackageNames.Contains(Env))
			{
				// Already added
				continue;
			}

			FString EnvName = NewName + "_Environment" + FString::FromInt(EnvIndex);
			OutPresetPackageNames.Add(Env, EnvName);
		}
	}
}



void UMoviePipelineDeadlineCloudExecutorJob::CopyEnvironmentOverrides(UDeadlineCloudEnvironment* Environment, UDeadlineCloudEnvironment* Origin)
{
	for (auto& EnvOverride : JobTemplateOverrides.EnvironmentsOverrides)
	{
		if (MatchesSourcePath(EnvOverride.SourceObjectPath, Origin))
		{
			Environment->Variables = EnvOverride.Variables;
			return;
		}
	}

	for (auto& StepOverride : JobTemplateOverrides.StepsOverrides)
	{
		for (auto& EnvOverride : StepOverride.EnvironmentsOverrides)
		{
			if (MatchesSourcePath(EnvOverride.SourceObjectPath, Origin))
			{
				Environment->Variables = EnvOverride.Variables;
				return;
			}
		}
	}
}

void UMoviePipelineDeadlineCloudExecutorJob::CopyHostRequirementsOverrides(UDeadlineCloudHostRequirements* HostRequirements, UDeadlineCloudHostRequirements* Origin)
{
	for (auto& StepOverride : JobTemplateOverrides.StepsOverrides)
	{
		if (!StepOverride.HostRequirementsOverride.IsEmpty())
		{
			if (MatchesSourcePath(StepOverride.HostRequirementsOverride.SourceObjectPath, Origin))
			{
				HostRequirements->HostRequirements.Amounts = StepOverride.HostRequirementsOverride.HostRequirements.Amounts;
				HostRequirements->HostRequirements.Attributes = StepOverride.HostRequirementsOverride.HostRequirements.Attributes;

				return;
			}
		}
	}
}

void UMoviePipelineDeadlineCloudExecutorJob::CopyStepOverrides(UDeadlineCloudStep* Step, UDeadlineCloudStep* Origin)
{
	for (auto& StepOverride : JobTemplateOverrides.StepsOverrides)
	{
		if (MatchesSourcePath(StepOverride.SourceObjectPath, Origin))
		{
			Step->TaskParameterDefinitions.Parameters = StepOverride.TaskParameterDefinitions.Parameters;
			break;
		}
	}
}

void UMoviePipelineDeadlineCloudExecutorJob::CopyJobOverrides(UDeadlineCloudRenderJob* Job)
{
	Job->JobPresetStruct.JobSharedSettings = PresetOverrides.JobSharedSettings;
	Job->JobPresetStruct.JobAttachments.InputFiles = PresetOverrides.JobAttachments.InputFiles;
	Job->JobPresetStruct.JobAttachments.InputDirectories = PresetOverrides.JobAttachments.InputDirectories;
	Job->JobPresetStruct.JobAttachments.OutputDirectories = PresetOverrides.JobAttachments.OutputDirectories;
	Job->ParameterDefinition.Parameters = JobTemplateOverrides.Parameters;
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

bool UMoviePipelineDeadlineCloudExecutorJob::IsUsingDefaultPreset() const
{
	auto DefaultJobPreset = UDeadlineCloudDeveloperSettings::GetDefaultJobPreset();

    return JobPreset == DefaultJobPreset;
}

void UMoviePipelineDeadlineCloudExecutorJob::SaveLastUsedFrom(const UMoviePipelineDeadlineCloudExecutorJob* Source)
{
	UDeadlineCloudDeveloperSettings::SaveMRQJobPresetCache(Source);
}

void UMoviePipelineDeadlineCloudExecutorJob::ApplyLastUsedTo(UMoviePipelineDeadlineCloudExecutorJob* Target)
{
	UDeadlineCloudDeveloperSettings::LoadMRQJobPresetCache(Target);
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
		auto DefaultPreset = UDeadlineCloudDeveloperSettings::GetDefaultJobPreset();
		if (IsValid(DefaultPreset))
		{
			Preset = DefaultPreset;
		}
		else
		{
			UE_LOG(LogTemp, Display, TEXT("DeadlineCloud: Creating new UDeadlineCloudRenderJob"));
			Preset = NewObject<UDeadlineCloudRenderJob>();

			FString DefaultTemplate = "/Content/Python/openjd_templates/render_job.yml";
			FString StepTemplate = "/Content/Python/openjd_templates/render_step.yml";
			FString EnvTemplate = "/Content/Python/openjd_templates/launch_ue_environment.yml";
			FString HostReqTemplate = "/Content/Python/openjd_templates/host_requirements.yml";

			FString  PluginContentDir = IPluginManager::Get().FindPlugin(TEXT("UnrealDeadlineCloudService"))->GetBaseDir();

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

			UDeadlineCloudHostRequirements* PresetHostReq;
			PresetHostReq = NewObject<UDeadlineCloudHostRequirements>();
			
			FString PathToHostReqTemplate = FPaths::Combine(FPaths::ConvertRelativePathToFull(PluginContentDir), HostReqTemplate);
			FPaths::NormalizeDirectoryName(PathToHostReqTemplate);
			UE_LOG(LogTemp, Display, TEXT("DeadlineCloud: Looking for host requirements template at: %s"), *PathToHostReqTemplate);

			PresetHostReq->PathToTemplate.FilePath = PathToHostReqTemplate;
			PresetHostReq->OpenHostRequirementsFile(PathToHostReqTemplate);
			PresetStep->HostRequirements = PresetHostReq;
			UE_LOG(LogTemp, Display, TEXT("DeadlineCloud: Host requirements template loaded successfully"));
		}
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
				
				if (StepData.TaskParameterDefinitions.Parameters.IsEmpty() 
					&& StepData.EnvironmentsOverrides.IsEmpty()
					&& StepData.HostRequirementsOverride.IsEmpty())
				{
					continue;
				}

				DeadlineStepsOverrides.Add(StepData);
			}
		}
	}
	return DeadlineStepsOverrides;
}

void UMoviePipelineDeadlineCloudExecutorJob::FixReferencesAfterDuplication(TMap<UDataAsset*, FString>& SourceObjects, TArray<UDataAsset*> NewObjects)
{
    TArray<UDataAsset*> OldObjects;
    OldObjects.Reserve(SourceObjects.Num());
    for (const TPair<UDataAsset*, FString>& Pair : SourceObjects)
    {
        OldObjects.Add(Pair.Key);
    }

    if (OldObjects.Num() != NewObjects.Num())
    {
        UE_LOG(LogTemp, Warning, TEXT("FixReferencesAfterDuplication: size mismatch Old=%d New=%d"),
            OldObjects.Num(), NewObjects.Num());
    }

    const int32 Count = FMath::Min(OldObjects.Num(), NewObjects.Num());

    TMap<UObject*, UObject*> ReplacementMap;
    ReplacementMap.Reserve(Count);
    for (int32 i = 0; i < Count; ++i)
    {
        if (OldObjects[i] && NewObjects[i])
        {
            ReplacementMap.Add(OldObjects[i], NewObjects[i]);
        }
    }

    for (UDataAsset* NewAsset : NewObjects)
    {
        if (!NewAsset) { continue; }

        NewAsset->Modify(); 

        FArchiveReplaceObjectRef<UObject> ReplaceAr(
            NewAsset,
            ReplacementMap,
            EArchiveReplaceObjectFlags::None
        );

#if WITH_EDITOR
        FCoreUObjectDelegates::OnObjectModified.Broadcast(NewAsset);
        NewAsset->MarkPackageDirty();
#endif
	}
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

	/*
	 * Pre-GUI hooks (MRQ path). The MRQ render submission serializes PresetOverrides (a snapshot of the
	 * data asset taken at preset-assign time), NOT the live data asset, so the pre-GUI hook must apply
	 * here to reach an MRQ render — running it only on the data-asset editor panel
	 * (FDeadlineCloudJobDetails) misses this primary submission path. We run env-sourced hooks once per
	 * executor-job instance and pre-populate PresetOverrides.JobSharedSettings (+ JobTemplateOverrides
	 * parameters) before the field widgets below are built.
	 *
	 * Panel-tied by design: the hook fires when a job's Details panel is built (i.e. the job is opened in
	 * the MRQ), matching the cross-DCC "pre-GUI" contract that hooks pre-populate the fields the artist
	 * reviews before editing. A Render (Remote) submits every queue job (remote_executor iterates
	 * pipeline_queue.get_jobs()), so a job that is never opened is submitted with its un-hooked
	 * PresetOverrides. This is intentional — there is deliberately no submit-time hook entry point, as a
	 * submit-time hook could not pre-populate what the artist reviews. The common single-job workflow
	 * (open the job, review the hooked values, submit) is unaffected.
	 *
	 * The bPreGuiHooksApplied latch is set only INSIDE the Get() success branch (the Python impl only
	 * exists once init_unreal has registered it) and BEFORE RunPreGuiHooks, so a panel rebuild triggered
	 * while the confirmation modal is up re-enters with the latch already set and cannot double-run.
	 */
	// JobPreset must be non-null: we only pre-populate an MRQ job that has a preset (matching the JobPreset
	// guards on the save/reset handlers); JobTemplateOverrides.Parameters is populated from the preset by
	// ReloadDataFromJobPreset. A saved queue whose preset asset was deleted/failed to load, or a job
	// constructed outside a live engine, can reach CustomizeDetails with a null preset.
	if (MrqJob.IsValid() && MrqJob->JobPreset && !MrqJob->bPreGuiHooksApplied)
	{
		if (UDeadlineCloudPreGuiHookLibrary* HookLibrary = UDeadlineCloudPreGuiHookLibrary::Get())
		{
			MrqJob->bPreGuiHooksApplied = true;
			// Pass the current job state (from the preset-override snapshot the MRQ render actually
			// submits) so hooks can adjust (not just set) it — see RunPreGuiHooks. Seed the parameter
			// context from JobTemplateOverrides.Parameters — the SAME hidden-item-filtered list
			// ApplyOutputToParameters writes back to below — so a hook only sees parameters it can
			// actually override. GetParameterDefinitionWithOverrides() would start from the unfiltered
			// JobPreset->ParameterDefinition, so a hidden template parameter would be visible in the
			// context yet absent from the apply list, producing a spurious "not applied" warning.
			const FDeadlineCloudPreGuiHookOutput HookOutput =
				HookLibrary->RunPreGuiHooks(
					MrqJob->PresetOverrides.JobSharedSettings.Name,
					MrqJob->PresetOverrides.JobSharedSettings.Priority,
					MrqJob->JobTemplateOverrides.Parameters);
			if (HookOutput.bRan)
			{
				TArray<FString> Unapplied = HookOutput.UnappliedKeys;
				UDeadlineCloudPreGuiHookLibrary::ApplyOutputToSharedSettings(
					MrqJob->PresetOverrides.JobSharedSettings, HookOutput, Unapplied);
				UDeadlineCloudPreGuiHookLibrary::ApplyOutputToParameters(
					MrqJob->JobTemplateOverrides.Parameters, HookOutput, Unapplied);
				UDeadlineCloudPreGuiHookLibrary::NotifyUnappliedKeys(Unapplied);
			}
		}
	}

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
		else if (PropertyName == GET_MEMBER_NAME_CHECKED(UMoviePipelineDeadlineCloudExecutorJob, JobPreset))
		{
			const FResetToDefaultOverride ResetDefaultOverride = FResetToDefaultOverride::Create(
				FIsResetToDefaultVisible::CreateLambda([](TSharedPtr<IPropertyHandle> PropertyHandle) {return true; }),
            FResetToDefaultHandler::CreateSP(this, &FMoviePipelineDeadlineCloudExecutorJobCustomization::ResetPresetToDefaultHandler)
			);

			TSharedRef<SWidget> SaveButtonWidget = SNew(SButton)
				.ToolTipText(FText::FromString("Save the current job preset."))
				.ButtonStyle(FAppStyle::Get(), "SimpleButton")
				.ContentPadding(FMargin(2.f))
				.IsEnabled_Lambda([this]() 
					{ 
						return MrqJob.IsValid() && MrqJob->JobPreset != nullptr; 
					})
				.OnClicked_Lambda([this]() 
					{ 
						FDeadlineCloudDetailsWidgetsHelper::CreateSavePresetDialogWidget(MrqJob.Get());
						return FReply::Handled();
					})
					[
						SNew(SImage)
							.Image(FAppStyle::Get().GetBrush("Icons.Save"))
					];
			SaveButtonWidget->AddMetadata(FDriverMetaData::Id(FName("MRQJobSavePresetButton")));

			DeadlineCategory.AddProperty(PropertyName)
				.OverrideResetToDefault(ResetDefaultOverride)
				.CustomWidget()
				.NameContent()
				[
					Property->CreatePropertyNameWidget()
				]
				.ValueContent()
				[
					SNew(SHorizontalBox)
						+ SHorizontalBox::Slot()
						.FillWidth(1.0f)
						[
							Property->CreatePropertyValueWidget()
						]
						+ SHorizontalBox::Slot()
						.AutoWidth()
						.VAlign(VAlign_Top)
						.HAlign(HAlign_Center)
						.Padding(2.0f, 4.0f)
						[
							SaveButtonWidget
						]
				];
		}
		else
		{
			DeadlineCategory.AddProperty(Property);
		}
	}

	IDetailCategoryBuilder& DeadlineCloudCategoryBuilder = DetailBuilder.EditCategory(
		"DeadlineCloud"
	);
}

void FMoviePipelineDeadlineCloudExecutorJobCustomization::ResetPresetToDefaultHandler(TSharedPtr<IPropertyHandle> PropertyHandle) const
{
	if (MrqJob.IsValid() && MrqJob->JobPreset)
	{
		MrqJob->ReloadDataFromJobPreset();
		if (MrqJob->OnRequestDetailsRefresh.IsBound())
		{
			MrqJob->OnRequestDetailsRefresh.Execute();
		}
	}
}
