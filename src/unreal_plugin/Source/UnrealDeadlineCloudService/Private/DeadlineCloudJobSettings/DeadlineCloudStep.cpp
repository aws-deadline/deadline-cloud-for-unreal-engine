#include "DeadlineCloudJobSettings/DeadlineCloudStep.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"

UDeadlineCloudStep::UDeadlineCloudStep()
{
}


//TArray <FStepParameterSpace> UDeadlineCloudStep::OpenStepFile(const FString& Path)
void UDeadlineCloudStep::OpenStepFile(const FString& Path)
{
	StepParameters = UPythonYamlLibrary::Get()->OpenStepFile(Path);
	// return UPythonYamlLibrary::Get()->OpenStepFile(Path);
}

TArray<FStepParameterSpace> UDeadlineCloudStep::GetStepParameters()
{
	return StepParameters;
}
