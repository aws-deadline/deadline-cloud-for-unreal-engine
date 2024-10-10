#include "DeadlineCloudJobSettings/DeadlineCloudEnvironment.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "PythonAPILibraries/PythonParametersConsistencyChecker.h"

UDeadlineCloudEnvironment::UDeadlineCloudEnvironment()
{
}

void UDeadlineCloudEnvironment::OpenEnvFile(const FString& Path)
{
	EnvironmentStructure = UPythonYamlLibrary::Get()->OpenEnvFile(Path);
}

void UDeadlineCloudEnvironment::CheckEnvironmentVariablesConsistency(UDeadlineCloudEnvironment* Self)
{
	FParametersConsistencyCheckResult  result = UPythonParametersConsistencyChecker::Get()->CheckEnvironmentVariablesConsistency(Self);
	
}
