#include "DeadlineCloudJobSettings/DeadlineCloudJob.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"

UDeadlineCloudJob::UDeadlineCloudJob()
{
	/*for test only!*/
	if (GEngine)
	{	
		PathToTemplate.FilePath = TEXT("E:/MeerkatDemo/Plugins/deadline-cloud-for-unreal-perforce/src/deadline/unreal_submitter/templates/default_unreal_job_template_v06.yaml");
		TArray <FParameterDefinition> structs = OpenJobFile(PathToTemplate.FilePath);
	}
}


TArray <FParameterDefinition> UDeadlineCloudJob::OpenJobFile(const FString& Path)
{
	return UPythonYamlLibrary::Get()->OpenJobFile(Path);
}