#pragma once

#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "DeadlineCloudJob.generated.h"



UCLASS(BlueprintType, Blueprintable, Config = Game)
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudJob : public UObject
{
	GENERATED_BODY()
public:

	UDeadlineCloudJob();

	UPROPERTY(Config, EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FFilePath PathToTemplate;
	
	/*Read path */
	UFUNCTION()
	TArray <FParameterDefinition> OpenJobFile(const FString& Path);

	//TArray <FParameterDefinition> jobParameters;

};
