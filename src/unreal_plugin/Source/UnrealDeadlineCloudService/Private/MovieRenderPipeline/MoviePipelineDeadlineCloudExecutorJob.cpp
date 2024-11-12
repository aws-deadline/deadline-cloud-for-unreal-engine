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

        // TODO Also skip if it's shown but not enabled
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
        this->EnvironmentsVariablesOverrides = GetEnvironmentsToOverride(SelectedJobPreset);

        // UpdateAttachmentFields();
    }

    UE_LOG(LogTemp, Log, TEXT("Deadline Cloud job changed: %s"),
        *PropertyChangedEvent.Property->GetPathName());

    // auto Result = GetDeadlineJobPresetStructWithOverrides();
    // FString JsonString;
    // FJsonObjectConverter::UStructToJsonObjectString(Result, JsonString);
    // UE_LOG(LogTemp, Log, TEXT("Make Deadline Cloud job: %s"), *JsonString);
}

void UMoviePipelineDeadlineCloudExecutorJob::CollectDependencies()
{
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
    return UDeadlineCloudJobBundleLibrary::Get()->GetCpuArchitectures();
}

TArray<FString> UMoviePipelineDeadlineCloudExecutorJob::GetOperatingSystems()
{
    return UDeadlineCloudJobBundleLibrary::Get()->GetOperatingSystems();
}

TArray<FString> UMoviePipelineDeadlineCloudExecutorJob::GetJobInitialStateOptions()
{
    return UDeadlineCloudJobBundleLibrary::Get()->GetJobInitialStateOptions();
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
            DeadlineStepsOverrides.Add(step->GetStepDataToOverride());
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
            EnvOverrides.Add(env->GetEnvironmentData());
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

    // We hide these properties because we want to use "Name", "UserName" and "Comment" from the Deadline preset
    const TArray<FName> PropertiesToHide = { "JobName", "Author", "Comment", "ExtraCmdArgs"};

    for (const TSharedRef<IPropertyHandle>& PropertyHandle : OutMrpCategoryProperties)
    {
        if (PropertiesToHide.Contains(PropertyHandle->GetProperty()->GetFName()))
        {
            PropertyHandle->MarkHiddenByCustomization();
        }
    }


    TSharedPtr<IPropertyHandle> JobPropertyHandle = DetailBuilder.GetProperty(GET_MEMBER_NAME_CHECKED(UMoviePipelineDeadlineCloudExecutorJob, JobPreset));

    if (JobPropertyHandle.IsValid())
    {
        TArray<TWeakObjectPtr<UObject>> ObjectsBeingCustomized; DetailBuilder.GetObjectsBeingCustomized(ObjectsBeingCustomized);

        if (ObjectsBeingCustomized.Num() > 0)
        {
            UObject* Object = ObjectsBeingCustomized[0].Get();
            if (Object)
            {
                FPropertyChangedEvent PropertyChangedEvent(JobPropertyHandle->GetProperty());
                FString ObjectName = Object->GetName(); //
                // UE_LOG(LogTemp, Log, TEXT("Object Name: %s"), *ObjectName);

                DetailBuilder.ForceRefreshDetails();
                Object->PostEditChangeProperty(PropertyChangedEvent);
            }
        }

    }

}


