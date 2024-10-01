#pragma once

#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "DeadlineCloudStep.h"
#include "DeadlineCloudEnvironment.h"
#include "DeadlineCloudJob.generated.h"



UCLASS(BlueprintType, Blueprintable, Config = Game)
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudJob : public UObject
{
	GENERATED_BODY()
public:

	UDeadlineCloudJob();

	UPROPERTY(Config, EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FFilePath PathToTemplate;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")

	TArray<UDeadlineCloudStep*> Steps;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	UDeadlineCloudEnvironment* Environment;

private:	
	TArray <FParameterDefinition> JobParameters;

public:
	/*Read path */
	UFUNCTION()
	void OpenJobFile(const FString& Path);

	TArray <FParameterDefinition> GetJobParameters();

};
