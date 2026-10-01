// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "DeadlineCloudJobSettings/DeadlineCloudHostRequirements.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "HAL/PlatformFilemanager.h"
#include "Misc/Paths.h"
#include "Interfaces/IPluginManager.h"

UDeadlineCloudHostRequirements::UDeadlineCloudHostRequirements()
{
    HiddenAmountsManager.OnGetAllNames.BindLambda([this]()
        {
            TSet<FName> Names;
            for (const auto& KV : HostRequirements.Amounts)
            {
                Names.Add(FName(*KV.Key));
            }
            return Names;
        });

    HiddenAmountsManager.OnGetDefaultHidden.BindLambda([this]()
        {
            return TSet<FName>{};
        });

    HiddenAttributesManager.OnGetAllNames.BindLambda([this]()
        {
            TSet<FName> Names;
            for (const auto& KV : HostRequirements.Attributes)
            {
                Names.Add(FName(*KV.Key));
            }
            return Names;
        });

    HiddenAttributesManager.OnGetDefaultHidden.BindLambda([this]()
        {
            return TSet<FName>{};
        });

    auto OnChanged = [this]()
        {
            Modify();
            MarkPackageDirty();
            ParameterHiddenEvent();
        };

    HiddenAmountsManager.OnChanged.BindLambda(OnChanged);
    HiddenAttributesManager.OnChanged.BindLambda(OnChanged);
}

void UDeadlineCloudHostRequirements::OpenHostRequirementsFile(const FString& Path)
{
    if (auto Library = UPythonYamlLibrary::Get())
    {        
        FDeadlineCloudHostRequirement DeadlineCloudHostReqs = Library->OpenHostRequirementsFile(Path);
        GetAttributesHiddenManager().Clear();
		GetAmountsHiddenManager().Clear();

        // Copy the data from the returned structures
        HostRequirements.Attributes = DeadlineCloudHostReqs.Attributes;
        HostRequirements.Amounts = DeadlineCloudHostReqs.Amounts;
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Error get PythonYamlLibrary"));
    }
}

void UDeadlineCloudHostRequirements::PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent)
{
    Super::PostEditChangeProperty(PropertyChangedEvent);
    if (PropertyChangedEvent.Property != nullptr) {

        FName PropertyName = PropertyChangedEvent.Property->GetFName();
        if (PropertyName == "FilePath")
        {
            OpenHostRequirementsFile(PathToTemplate.FilePath);
            OnPathChanged.ExecuteIfBound();
        }
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Changed property is nullptr"));
    }
}

void FDeadlineCloudHostRequirementsOverrides::CopyParametersValuesFrom(const FDeadlineCloudHostRequirementsOverrides& Other)
{
    HostRequirements.Amounts = Other.HostRequirements.Amounts;
    HostRequirements.Attributes = Other.HostRequirements.Attributes;

	SourceObjectPath = Other.SourceObjectPath;
}