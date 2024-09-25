#pragma once

#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "DeadlineCloudJob.h"
#include "DeadlineCloudRenderJob.generated.h"


UCLASS(BlueprintType, Blueprintable)
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudRenderJob : public UDeadlineCloudJob
{
	GENERATED_BODY()
public:

	UDeadlineCloudRenderJob() {};

	UPROPERTY(Config, EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	int TaskChunkSize;


};
