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
	//UDeadlineCloudStep* Step;
	TArray<UDeadlineCloudStep*> Steps;
	UDeadlineCloudEnvironment* Environment;
	
	/*Read path */
	UFUNCTION()
	TArray <FParameterDefinition> OpenJobFile(const FString& Path);

};
