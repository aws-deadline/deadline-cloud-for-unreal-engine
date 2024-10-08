#include "DeadlineCloudJobSettings/DeadlineCloudStep.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"

UDeadlineCloudStep::UDeadlineCloudStep()
{
}

void UDeadlineCloudStep::OpenStepFile(const FString& Path)
{
	StepTaskParameterDefinitions = UPythonYamlLibrary::Get()->OpenStepFile(Path);

}

TArray<FStepTaskParameterDefinition> UDeadlineCloudStep::GetStepParameters()
{
	return StepTaskParameterDefinitions;
}
