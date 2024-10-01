#include "DeadlineCloudJobSettings/DeadlineCloudEnvironment.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"

UDeadlineCloudEnvironment::UDeadlineCloudEnvironment()
{
}

TArray <FEnvironmentStruct> UDeadlineCloudEnvironment::OpenEnvFile(const FString& Path)
{
	return UPythonYamlLibrary::Get()->OpenEnvFile(Path);
}
