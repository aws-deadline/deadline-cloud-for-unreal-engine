// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once

#include "DeadlineCloudEnvironment.h"
#include "DeadlineCloudStep.generated.h"

USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudStepParametersArray
{
	GENERATED_BODY()

	/** List of files paths */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	TArray<FStepTaskParameterDefinition> Parameters;
};

USTRUCT(BlueprintType)
struct  FDeadlineCloudStepOverride
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadWrite, Category = "Parameters", meta = (DisplayPriority = 1))
	FString Name;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters", meta = (DisplayPriority = 3, GetOptions = "GetDependsList"))
	TSet<FString> DependsOn;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters", meta = (DisplayPriority = 4))
	TArray<FDeadlineCloudEnvironmentOverride> EnvironmentsOverrides;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters", meta = (DisplayPriority = 4))
	FDeadlineCloudStepParametersArray TaskParameterDefinitions;
};

UCLASS(BlueprintType, Blueprintable)
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudStep : public UDataAsset
{
	GENERATED_BODY()
public:

	UDeadlineCloudStep();

	FSimpleDelegate OnSomethingChanged;

	UPROPERTY(VisibleAnywhere, BlueprintReadWrite, Category = "Parameters", meta = (DisplayPriority = 1))
	FString Name;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters", meta = (DisplayPriority = 3, GetOptions = "GetDependsList"))
	TSet<FString> DependsOn;

	UPROPERTY( EditAnywhere, BlueprintReadWrite, Category = "Parameters", meta = (DisplayPriority = 2))
	FFilePath PathToTemplate;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters", meta = (DisplayPriority = 5))
	TArray<TObjectPtr<UDeadlineCloudEnvironment>> Environments;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters", meta = (DisplayPriority = 4))
	FDeadlineCloudStepParametersArray TaskParameterDefinitions;

	virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override;

	UFUNCTION()
	TArray<FString> GetDependsList();

	UFUNCTION()
	FDeadlineCloudStepOverride GetStepDataToOverride();

	bool IsParameterArrayDefault(FString ParameterName);
	void ResetParameterArray(FString ParameterName);
private:


public:
	/** Read path */
	UFUNCTION()
	void OpenStepFile(const FString& Path);

	UFUNCTION()
	FParametersConsistencyCheckResult CheckStepParametersConsistency(UDeadlineCloudStep* Step);

	UFUNCTION(BlueprintCallable, Category = "Parameters")
	void FixStepParametersConsistency(UDeadlineCloudStep* Step);

    UFUNCTION(BlueprintCallable, Category="Parameters")
	TArray<FStepTaskParameterDefinition> GetStepParameters();

	UFUNCTION(BlueprintCallable, Category="Parameters")
	void SetStepParameters(TArray<FStepTaskParameterDefinition> InStepParameters);
};