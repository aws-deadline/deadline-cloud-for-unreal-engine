// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "DeadlineCloudJobSettings/DeadlineCloudStep.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "PythonAPILibraries/PythonParametersConsistencyChecker.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetRegistry/AssetRegistryHelpers.h"
#include "Interfaces/IPluginManager.h"

UDeadlineCloudStep::UDeadlineCloudStep()
{
    HiddenParamsManager.OnGetAllNames.BindLambda([this]()
        {
            TSet<FName> Names;
            for (const auto& P : TaskParameterDefinitions.Parameters)
            {
                Names.Add(FName(*P.Name));
            }
            return Names;
        });

    HiddenParamsManager.OnGetDefaultHidden = HiddenParamsManager.OnGetAllNames;

    HiddenParamsManager.OnChanged.BindLambda([this]()
        {
            Modify();
            MarkPackageDirty();
            ParameterHiddenEvent();
        });
}

void UDeadlineCloudStep::OpenStepFile(const FString& Path)
{
    if (auto Library = UPythonYamlLibrary::Get())
    {
        auto StepStruct = Library->OpenStepFile(Path);
        Name = StepStruct.Name;
        TaskParameterDefinitions.Parameters = StepStruct.Parameters;
        
        GetHiddenManager().Clear();
        for (auto Parameter :TaskParameterDefinitions.Parameters)
        {
            GetHiddenManager().Add(FName(*Parameter.Name));
        }
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
    StepData.SourceObjectPath = FSoftObjectPath(this);
    StepData.Name = Name;
    StepData.DependsOn = DependsOn;

    // Only add step environments with non-hidden parameters
    for (int i = 0; i < Environments.Num(); i++)
    {
        UDeadlineCloudEnvironment* Environment = Environments[i];
        if (Environment)
        {
            FDeadlineCloudEnvironmentOverride FilteredEnvData;
			FilteredEnvData.SourceObjectPath = FSoftObjectPath(Environment);
            FilteredEnvData.Name = Environment->Name;
            
            // Filter out hidden variables
            for (const auto& VariablePair : Environment->Variables.Variables)
            {
                if (!Environment->GetHiddenManager().Contains(FName(VariablePair.Key)))
                {
                    FilteredEnvData.Variables.Variables.Add(VariablePair.Key, VariablePair.Value);
                }
            }           
            // Only add visible environments
            if (FilteredEnvData.Variables.Variables.Num() > 0)
            {
                Envs.Add(FilteredEnvData);
            }
        }
    }

    StepData.EnvironmentsOverrides = Envs;
    UDeadlineCloudHostRequirements* PresetHostReq;
    if (IsValid(HostRequirements))
    {
        PresetHostReq = HostRequirements;
    }
    else
    {
        FString  PluginContentDir = IPluginManager::Get().FindPlugin(TEXT("UnrealDeadlineCloudService"))->GetBaseDir();
        FString HostReqTemplate = "/Content/Python/openjd_templates/host_requirements.yml";
        PresetHostReq = NewObject<UDeadlineCloudHostRequirements>();

        FString PathToHostReqTemplate = FPaths::Combine(FPaths::ConvertRelativePathToFull(PluginContentDir), HostReqTemplate);
        FPaths::NormalizeDirectoryName(PathToHostReqTemplate);

        PresetHostReq->PathToTemplate.FilePath = PathToHostReqTemplate;
        PresetHostReq->OpenHostRequirementsFile(PathToHostReqTemplate);  
    }


    StepData.HostRequirementsOverride.SourceObjectPath = FSoftObjectPath(HostRequirements);

	FDeadlineCloudHostRequirement HostReqOverrides;

    for (const auto& AmountPair : PresetHostReq->HostRequirements.Amounts)
    {
        if (!PresetHostReq->GetAmountsHiddenManager().Contains(FName(AmountPair.Key)))
        {
            HostReqOverrides.Amounts.Add(AmountPair.Key, AmountPair.Value);
        }
    }

    for (const auto& AttributePair : PresetHostReq->HostRequirements.Attributes)
    {
        if (!PresetHostReq->GetAttributesHiddenManager().Contains(FName(AttributePair.Key)))
        {
            HostReqOverrides.Attributes.Add(AttributePair.Key, AttributePair.Value);
        }
    }

    StepData.HostRequirementsOverride.HostRequirements.Amounts = HostReqOverrides.Amounts;
    StepData.HostRequirementsOverride.HostRequirements.Attributes = HostReqOverrides.Attributes;
    StepData.HostRequirementsOverride.SourceObjectPath = FSoftObjectPath(HostRequirements);

    FDeadlineCloudStepParametersArray LocalTaskParameterDefinitions;

    for (int i = 0; i < TaskParameterDefinitions.Parameters.Num(); i++)
    {
        if (!GetHiddenManager().Contains(FName(TaskParameterDefinitions.Parameters[i].Name)))
        {
            // Add parameter if not hidden
            LocalTaskParameterDefinitions.Parameters.Add(TaskParameterDefinitions.Parameters[i]);
        }
        
    }
    StepData.TaskParameterDefinitions = LocalTaskParameterDefinitions;
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

void FDeadlineCloudStepOverride::CopyParametersValuesFrom(const FDeadlineCloudStepOverride& Other)
{
	// Copy EnvironmentsOverrides
	for (const FDeadlineCloudEnvironmentOverride& OtherEnv : Other.EnvironmentsOverrides)
	{
		bool bFound = false;
		for (FDeadlineCloudEnvironmentOverride& ThisEnv : EnvironmentsOverrides)
		{
			if (ThisEnv.Name == OtherEnv.Name)
			{
				bFound = true;
				ThisEnv.CopyParametersValuesFrom(OtherEnv);
				break;
			}
		}
	}

	HostRequirementsOverride.CopyParametersValuesFrom(Other.HostRequirementsOverride);

	// Copy TaskParameterDefinitions values
	for (const FStepTaskParameterDefinition& OtherParam : Other.TaskParameterDefinitions.Parameters)
	{
		bool bFound = false;
		for (FStepTaskParameterDefinition& ThisParam : TaskParameterDefinitions.Parameters)
		{
			if (ThisParam.Name == OtherParam.Name)
			{
				bFound = true;
				ThisParam.Range = OtherParam.Range;
				break;
			}
		}
	}

	SourceObjectPath = Other.SourceObjectPath;
}