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
	Variables.Empty();
	for (FEnvVariable Variable : EnvironmentStructure.Variables)
	{
		Variables.Add(Variable.Name, Variable.Value);
	}
}

void UDeadlineCloudEnvironment::CheckEnvironmentVariablesConsistency(UDeadlineCloudEnvironment* Self)
{
	FParametersConsistencyCheckResult  result = UPythonParametersConsistencyChecker::Get()->CheckEnvironmentVariablesConsistency(Self);
	
}

void UDeadlineCloudEnvironment::PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent)
{
		Super::PostEditChangeProperty(PropertyChangedEvent);
		if (PropertyChangedEvent.Property != nullptr) {

			FName PropertyName = PropertyChangedEvent.Property->GetFName();
			if (PropertyName == "FilePath")
			{		
				OpenEnvFile(PathToTemplate.FilePath);
			}
		}
}
