// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "DeadlineCloudJobSettings/DeadlineCloudEnvironment.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "PythonAPILibraries/PythonParametersConsistencyChecker.h"

UDeadlineCloudEnvironment::UDeadlineCloudEnvironment()
{
    HiddenVarsManager.OnGetAllNames.BindLambda([this]()
        {
            TSet<FName> Names;
            for (const auto& KV : Variables.Variables)
            {
                Names.Add(FName(*KV.Key));
            }
            return Names;
        });

    HiddenVarsManager.OnGetDefaultHidden.BindLambda([this]()
        {
            return HiddenVarsManager.OnGetAllNames.IsBound()
                ? HiddenVarsManager.OnGetAllNames.Execute()
                : TSet<FName>{};
        });

    HiddenVarsManager.OnChanged.BindLambda([this]()
        {
            Modify();
            MarkPackageDirty();
            ParameterHiddenEvent();
        });
}

void UDeadlineCloudEnvironment::OpenEnvFile(const FString& Path)
{
    if (auto Library = UPythonYamlLibrary::Get())
    {
        FEnvironmentStruct EnvironmentStructure = Library->OpenEnvFile(Path);
        Name = EnvironmentStructure.Name;
        Variables.Variables.Empty();
        GetHiddenManager().Clear();
        for (FEnvVariable Variable : EnvironmentStructure.Variables)
        {
            Variables.Variables.Add(Variable.Name, Variable.Value);
            GetHiddenManager().Add(FName(*Variable.Name));
        }
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Error get PythonYamlLibrary"));
    }
}

FParametersConsistencyCheckResult UDeadlineCloudEnvironment::CheckEnvironmentVariablesConsistency(const UDeadlineCloudEnvironment* Env)
{
    if (auto Library = UPythonParametersConsistencyChecker::Get())
    {
        return Library->CheckEnvironmentVariablesConsistency(Env);
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Error get PythonParametersConsistencyChecker"));
    }
    return FParametersConsistencyCheckResult();
}

void UDeadlineCloudEnvironment::FixEnvironmentVariablesConsistency(UDeadlineCloudEnvironment* Env)
{
    if (auto Library = UPythonParametersConsistencyChecker::Get())
    {
        Library->FixEnvironmentVariablesConsistency(Env);
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Error get PythonParametersConsistencyChecker"));
    }
}

FDeadlineCloudEnvironmentOverride UDeadlineCloudEnvironment::GetEnvironmentData()
{
    FDeadlineCloudEnvironmentOverride FilteredEnvData;
    FilteredEnvData.Name = this->Name;
	FilteredEnvData.SourceObjectPath = FSoftObjectPath(this);
    // Filter out hidden variables from the environment
    for (const auto& VariablePair : this->Variables.Variables)
    {
        if (!HiddenVarsManager.Contains(FName(VariablePair.Key)))
        {
            FilteredEnvData.Variables.Variables.Add(VariablePair.Key, VariablePair.Value);
        }
    }
    
    return FilteredEnvData;
}

bool UDeadlineCloudEnvironment::IsDefaultVariables()
{
    FEnvironmentStruct DefaultVariables;
    if (auto Library = UPythonYamlLibrary::Get())
    {
        DefaultVariables = Library->OpenEnvFile(PathToTemplate.FilePath);
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Error get PythonYamlLibrary"));
    }

    if (Variables.Variables.Num() == DefaultVariables.Variables.Num())
    {
        for (FEnvVariable Variable : DefaultVariables.Variables)
        {
            if (!Variables.Variables.Contains(Variable.Name))
            {
                return false;
            }

            if (!Variables.Variables[Variable.Name].Equals(Variable.Value))
            {
                return false;
            }
        }
        return true;
    }

    return false;
}

void UDeadlineCloudEnvironment::ResetVariables()
{
    FEnvironmentStruct DefaultVariables;

    if (auto Library = UPythonYamlLibrary::Get())
    {
        DefaultVariables = Library->OpenEnvFile(PathToTemplate.FilePath);
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Error get PythonYamlLibrary"));
    }

    Variables.Variables.Empty();
    for (FEnvVariable Variable : DefaultVariables.Variables)
    {
        Variables.Variables.Add(Variable.Name, Variable.Value);
    }

    OnPathChanged.ExecuteIfBound();
}

void UDeadlineCloudEnvironment::PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent)
{
    Super::PostEditChangeProperty(PropertyChangedEvent);
    if (PropertyChangedEvent.Property != nullptr) {

        FName PropertyName = PropertyChangedEvent.Property->GetFName();
        if (PropertyName == "FilePath")
        {
            OpenEnvFile(PathToTemplate.FilePath);
            OnPathChanged.ExecuteIfBound();
        }
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Changed property is nullptr"));
    }
}

void FDeadlineCloudEnvironmentOverride::CopyParametersValuesFrom(const FDeadlineCloudEnvironmentOverride& Other)
{
	for (auto& VarPair : Other.Variables.Variables)
	{
		auto FoundVar = Variables.Variables.Find(VarPair.Key);
		if (FoundVar)
		{
			*FoundVar = VarPair.Value;
		}
	}

	SourceObjectPath = Other.SourceObjectPath;
}
