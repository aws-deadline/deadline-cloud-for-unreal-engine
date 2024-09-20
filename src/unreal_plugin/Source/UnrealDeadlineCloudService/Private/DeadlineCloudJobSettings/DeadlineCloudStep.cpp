#include "DeadlineCloudJobSettings/DeadlineCloudStep.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"

UDeadlineCloudStep::UDeadlineCloudStep()
{
	if (GEngine)
	{
		PathToTemplate.FilePath = TEXT("E:/MeerkatDemo/Plugins/deadline-cloud-for-unreal-perforce/src/deadline/unreal_submitter/templates/default_unreal_step_template_v05.yaml");
		TArray <FStepParameterSpace> s = OpenStepFile(PathToTemplate.FilePath);
	}

}


TArray <FStepParameterSpace> UDeadlineCloudStep::OpenStepFile(const FString& Path)
{
	//edit
		return UPythonYamlLibrary::Get()->OpenStepFile(Path);
}