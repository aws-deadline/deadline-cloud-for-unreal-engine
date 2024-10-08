#include "DeadlineCloudJobSettings/DeadlineCloudEnvironment.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "PythonAPILibraries/PythonParametersConsistencyChecker.h"

UDeadlineCloudEnvironment::UDeadlineCloudEnvironment()
{
}

TArray <FEnvironmentStruct> UDeadlineCloudEnvironment::OpenEnvFile(const FString& Path)
{
	return UPythonYamlLibrary::Get()->OpenEnvFile(Path);
}

void UDeadlineCloudEnvironment::CheckEnviromnentParametersConsistency(UDeadlineCloudEnvironment* Self)
{
	FParametersConsistencyCheckResult  result = UPythonParametersConsistencyChecker::Get()->CheckEnvironmentParametersConsistency(Self);
}
