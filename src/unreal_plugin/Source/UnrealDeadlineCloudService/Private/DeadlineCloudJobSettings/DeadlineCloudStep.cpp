#include "DeadlineCloudJobSettings/DeadlineCloudStep.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"

UDeadlineCloudStep::UDeadlineCloudStep()
{

}


TArray <FStepParameterDefinition> UDeadlineCloudStep::OpenStepFile(const FString& Path)
{
	//edit
	return UPythonYamlLibrary::Get()->OpenStepFile(Path);
}