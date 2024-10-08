#pragma once


#include "DeadlineCloudEnvironment.h"
#include "DeadlineCloudStep.generated.h"



UCLASS(BlueprintType, Blueprintable)
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudStep : public UDataAsset
{
	GENERATED_BODY()
public:

	UDeadlineCloudStep();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FString Name;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FString DependsOn;

	UPROPERTY( EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FFilePath PathToTemplate;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	TArray<UDeadlineCloudEnvironment*> Environments;

private:
	TArray<FStepTaskParameterDefinition> StepTaskParameterDefinitions;

public:
	/** Read path */
	UFUNCTION()
	void OpenStepFile(const FString& Path);

	UFUNCTION()
	void CheckStepParametersConsistency(UDeadlineCloudStep* Self);


	TArray<FStepTaskParameterDefinition> GetStepParameters();
};