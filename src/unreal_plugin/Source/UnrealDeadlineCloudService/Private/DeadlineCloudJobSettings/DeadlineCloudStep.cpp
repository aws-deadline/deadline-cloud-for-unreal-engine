#include "DeadlineCloudJobSettings/DeadlineCloudStep.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "PythonAPILibraries/PythonParametersConsistencyChecker.h"

UDeadlineCloudStep::UDeadlineCloudStep()
{
}

void UDeadlineCloudStep::OpenStepFile(const FString& Path)
{
	StepTaskParameterDefinitions = UPythonYamlLibrary::Get()->OpenStepFile(Path);

}

void UDeadlineCloudStep::CheckStepParametersConsistency(UDeadlineCloudStep* Self)
{
	FParametersConsistencyCheckResult  result = UPythonParametersConsistencyChecker::Get()->CheckStepParametersConsistency(Self);
}

TArray<FStepTaskParameterDefinition> UDeadlineCloudStep::GetStepParameters()
{
	return StepTaskParameterDefinitions;
}

void UDeadlineCloudStep::SetStepParameters(TArray<FStepTaskParameterDefinition> InStepParameters)
{
    StepTaskParameterDefinitions = InStepParameters;
}