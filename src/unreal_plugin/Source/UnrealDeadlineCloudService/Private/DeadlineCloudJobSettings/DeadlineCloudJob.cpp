#include "DeadlineCloudJobSettings/DeadlineCloudJob.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"

UDeadlineCloudJob::UDeadlineCloudJob()
{
}


TArray <FParameterDefinition> UDeadlineCloudJob::OpenJobFile(const FString& Path)
{
	return UPythonYamlLibrary::Get()->OpenJobFile(Path);
}