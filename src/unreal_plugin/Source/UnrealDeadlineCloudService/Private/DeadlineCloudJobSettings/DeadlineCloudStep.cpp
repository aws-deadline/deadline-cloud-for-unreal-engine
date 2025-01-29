// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "DeadlineCloudJobSettings/DeadlineCloudStep.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "PythonAPILibraries/PythonParametersConsistencyChecker.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetRegistry/AssetRegistryHelpers.h"

UDeadlineCloudStep::UDeadlineCloudStep()
{
}

void UDeadlineCloudStep::OpenStepFile(const FString& Path)
{
    if (auto Library = UPythonYamlLibrary::Get())
    {
        auto StepStruct = Library->OpenStepFile(Path);
        Name = StepStruct.Name;
        TaskParameterDefinitions.Parameters = StepStruct.Parameters;
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Error get PythonYamlLibrary"));
    }
}


void UDeadlineCloudStep::FixStepParametersConsistency(UDeadlineCloudStep* Step)
{
    if (auto Library = UPythonParametersConsistencyChecker::Get())
    {
        Library->FixStepParametersConsistency(Step);
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Error get PythonParametersConsistencyChecker"));
    }
}


FParametersConsistencyCheckResult UDeadlineCloudStep::CheckStepParametersConsistency(const UDeadlineCloudStep* Self)
{
    if (auto Library = UPythonParametersConsistencyChecker::Get())
    {
        return Library->CheckStepParametersConsistency(Self);
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Error get PythonParametersConsistencyChecker"));
    }
    return FParametersConsistencyCheckResult();
}

TArray<FStepTaskParameterDefinition> UDeadlineCloudStep::GetStepParameters()
{
    return TaskParameterDefinitions.Parameters;
}

void UDeadlineCloudStep::SetStepParameters(TArray<FStepTaskParameterDefinition> InStepParameters)
{
    TaskParameterDefinitions.Parameters = InStepParameters;
}
void UDeadlineCloudStep::PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent)
{
    Super::PostEditChangeProperty(PropertyChangedEvent);
    if (PropertyChangedEvent.Property != nullptr) {

        FName PropertyName = PropertyChangedEvent.Property->GetFName();
        FName MemberName = PropertyChangedEvent.MemberProperty->GetFName();
        if (PropertyName == "FilePath" && MemberName == "PathToTemplate")
        {
            OpenStepFile(PathToTemplate.FilePath);
            OnPathChanged.ExecuteIfBound();
        }
    }
}

TArray<FString> UDeadlineCloudStep::GetDependsList()
{
    TArray<FString> DependsList;

    FAssetRegistryModule& AssetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
    TArray< FString > ContentPaths;
    ContentPaths.Add(TEXT("/Game/"));
    TArray<FAssetData> AssetData;

    AssetRegistryModule.Get().ScanPathsSynchronous(ContentPaths);
    FTopLevelAssetPath ClassPathName = UDeadlineCloudStep::StaticClass()->GetClassPathName();
    TSet<FTopLevelAssetPath> DerivedNames;

    TArray<FTopLevelAssetPath> ParentNames;
    ParentNames.Add(ClassPathName);
    TSet<FTopLevelAssetPath> Excluded;
    AssetRegistryModule.Get().GetDerivedClassNames(ParentNames, Excluded, DerivedNames);

    FARFilter Filter;
    Filter.ClassPaths.Add(UDataAsset::StaticClass()->GetClassPathName());
    Filter.bRecursiveClasses = true;
    Filter.bRecursivePaths = true;

    AssetRegistryModule.Get().GetAssets(Filter, AssetData);

    for (const FAssetData& Data : AssetData)
    {
        if (DerivedNames.Contains(Data.AssetClassPath))
        {
            auto DataAsset = TSoftObjectPtr<UDataAsset>(FSoftObjectPath(Data.GetSoftObjectPath()));
            DataAsset.LoadSynchronous();

            UDeadlineCloudStep* StepAsset = Cast<UDeadlineCloudStep>(DataAsset.Get());
            if (StepAsset && StepAsset->Name != Name && !StepAsset->Name.IsEmpty())
            {
                DependsList.Add(StepAsset->Name);
            }
        }
    }
    return DependsList;
}

FDeadlineCloudStepOverride UDeadlineCloudStep::GetStepDataToOverride()
{
    FDeadlineCloudStepOverride StepData;
    TArray<FDeadlineCloudEnvironmentOverride> Envs;

    StepData.Name = Name;
    StepData.DependsOn = DependsOn;

    for (int i = 0; i < Environments.Num(); i++)
    {
        Envs.Add({ Environments[i]->GetEnvironmentData() });
    }

    StepData.EnvironmentsOverrides = Envs;
    StepData.TaskParameterDefinitions = TaskParameterDefinitions;
    return StepData;
}

bool UDeadlineCloudStep::IsParameterArrayDefault(FString ParameterName)
{
    TArray<FStepTaskParameterDefinition> DefaultParameters;
    if (auto Library = UPythonYamlLibrary::Get())
    {
        DefaultParameters = Library->OpenStepFile(PathToTemplate.FilePath).Parameters;
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Error get PythonYamlLibrary"));
    }
    for (FStepTaskParameterDefinition& Parameter : TaskParameterDefinitions.Parameters)
    {
        if (Parameter.Name == ParameterName)
        {
            for (FStepTaskParameterDefinition& DefaultParameter : DefaultParameters)
            {
                if (DefaultParameter.Name == ParameterName)
                {
                    if (Parameter.Range.Num() != DefaultParameter.Range.Num())
                    {
                        return false;
                    }

                    for (int i = 0; i < Parameter.Range.Num(); i++)
                    {
                        if (Parameter.Range[i] != DefaultParameter.Range[i])
                        {
                            return false;
                        }
                    }
                }
            }

        }
    }

    return true;
}

void UDeadlineCloudStep::ResetParameterArray(FString ParameterName)
{
    TArray<FStepTaskParameterDefinition> DefaultParameters;
    if (auto Library = UPythonYamlLibrary::Get())
    {
        DefaultParameters = Library->OpenStepFile(PathToTemplate.FilePath).Parameters;
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Error get PythonYamlLibrary"));
    }

    bool bFound = false;
    for (FStepTaskParameterDefinition& Parameter : TaskParameterDefinitions.Parameters)
    {
        if (Parameter.Name == ParameterName)
        {
            for (FStepTaskParameterDefinition& DefaultParameter : DefaultParameters)
            {
                if (DefaultParameter.Name == ParameterName)
                {
                    bFound = true;
                    Parameter.Range = DefaultParameter.Range;
                    OnPathChanged.ExecuteIfBound();
                    return;
                }
            }
        }
    }

    if (!bFound)
    {
        for (FStepTaskParameterDefinition& Parameter : TaskParameterDefinitions.Parameters)
        {
            if (Parameter.Name == ParameterName)
            {
                for (int i = 0; i < Parameter.Range.Num(); i++)
                {
                    Parameter.Range[i] = "";
                }
            }
        }
    }
}
