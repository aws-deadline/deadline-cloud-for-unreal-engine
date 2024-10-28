// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "DeadlineCloudJobSettings/DeadlineCloudEnvironment.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "PythonAPILibraries/PythonParametersConsistencyChecker.h"

UDeadlineCloudEnvironment::UDeadlineCloudEnvironment()
{
}

void UDeadlineCloudEnvironment::OpenEnvFile(const FString& Path)
{
	FEnvironmentStruct EnvironmentStructure = UPythonYamlLibrary::Get()->OpenEnvFile(Path);
	Name = EnvironmentStructure.Name;
	Variables.Variables.Empty();
	for (FEnvVariable Variable : EnvironmentStructure.Variables)
	{
		Variables.Variables.Add(Variable.Name, Variable.Value);
	}
}

FParametersConsistencyCheckResult UDeadlineCloudEnvironment::CheckEnvironmentVariablesConsistency(UDeadlineCloudEnvironment* Env)
{
	return UPythonParametersConsistencyChecker::Get()->CheckEnvironmentVariablesConsistency(Env);	
}

void UDeadlineCloudEnvironment::FixEnvironmentVariablesConsistency(UDeadlineCloudEnvironment* Env)
{
	UPythonParametersConsistencyChecker::Get()->FixEnvironmentVariablesConsistency(Env);
}

bool UDeadlineCloudEnvironment::IsDefaultVariables()
{
	FEnvironmentStruct DefaultVariables = UPythonYamlLibrary::Get()->OpenEnvFile(PathToTemplate.FilePath);

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
	FEnvironmentStruct DefaultVariables = UPythonYamlLibrary::Get()->OpenEnvFile(PathToTemplate.FilePath);
	Variables.Variables.Empty();
	for (FEnvVariable Variable : DefaultVariables.Variables)
	{
		Variables.Variables.Add(Variable.Name, Variable.Value);
	}

	OnSomethingChanged.ExecuteIfBound();
}

void UDeadlineCloudEnvironment::PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent)
{
	Super::PostEditChangeProperty(PropertyChangedEvent);
	if (PropertyChangedEvent.Property != nullptr) {

		FName PropertyName = PropertyChangedEvent.Property->GetFName();
		if (PropertyName == "FilePath")
		{		
			OpenEnvFile(PathToTemplate.FilePath);
			OnSomethingChanged.ExecuteIfBound();
		}
	}
}
