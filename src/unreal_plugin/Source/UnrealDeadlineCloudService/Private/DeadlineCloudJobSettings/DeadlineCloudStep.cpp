#include "DeadlineCloudJobSettings/DeadlineCloudStep.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"

UDeadlineCloudStep::UDeadlineCloudStep()
{
}


TArray <FStepParameterSpace> UDeadlineCloudStep::OpenStepFile(const FString& Path)
{
	return UPythonYamlLibrary::Get()->OpenStepFile(Path);
}