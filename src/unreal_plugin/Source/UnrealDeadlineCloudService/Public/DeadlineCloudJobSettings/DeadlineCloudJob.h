#pragma once

#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "DeadlineCloudStep.h"

#include "DeadlineCloudJobDataAsset.h"
#include "DeadlineCloudEnvironment.h"
#include "DeadlineCloudJob.generated.h"

/**
 * All Deadline Cloud job settings container struct
 */



UCLASS(BlueprintType, Blueprintable, Config = Game)
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudJob : public UObject
{
	GENERATED_BODY()
public:

	UDeadlineCloudJob();


	UPROPERTY(Config, EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FString Name;

	UPROPERTY(Config, EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FFilePath PathToTemplate;

	/** Deadline cloud job settings container struct */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Preset")
	FDeadlineCloudJobPresetStruct JobPresetStruct;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	TArray<UDeadlineCloudStep*> Steps;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	TArray<UDeadlineCloudEnvironment*> Environments;

private:	
	TArray <FParameterDefinition> JobParameters;

public:
	/*Read path */
	UFUNCTION()
	void OpenJobFile(const FString& Path);

	TArray <FParameterDefinition> GetJobParameters();

};
