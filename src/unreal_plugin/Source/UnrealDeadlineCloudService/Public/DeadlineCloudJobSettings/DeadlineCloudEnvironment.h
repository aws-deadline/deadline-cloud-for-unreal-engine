// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "DeadlineCloudJobSettings/DeadlineCloudHiddenParameters.h"
#include "DeadlineCloudEnvironment.generated.h"

USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudEnvironmentVariablesMap
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
    TMap<FString, FString> Variables;
};

USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudEnvironmentOverride
{
    GENERATED_BODY()

public:

    UPROPERTY(VisibleAnywhere, BlueprintReadWrite, Category = "Parameters")
	FString Name;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FDeadlineCloudEnvironmentVariablesMap Variables;

	UPROPERTY()
	FSoftObjectPath SourceObjectPath;

	//copy only values for existing parameters
	void CopyParametersValuesFrom(const FDeadlineCloudEnvironmentOverride& Other);
};

UCLASS(BlueprintType, Blueprintable)
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudEnvironment : public UDataAsset
{
	GENERATED_BODY()
public:

	UDeadlineCloudEnvironment();

	FSimpleDelegate OnPathChanged;

	UPROPERTY(VisibleAnywhere, BlueprintReadWrite, Category = "Parameters")
	FString Name; 

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FFilePath PathToTemplate;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FDeadlineCloudEnvironmentVariablesMap Variables;

	/** Read path */
	UFUNCTION()
	void OpenEnvFile(const FString& Path);

	UFUNCTION()
	FParametersConsistencyCheckResult CheckEnvironmentVariablesConsistency(const UDeadlineCloudEnvironment* Env);

	UFUNCTION()
	void FixEnvironmentVariablesConsistency(UDeadlineCloudEnvironment* Env);

	FDeadlineCloudEnvironmentOverride GetEnvironmentData();

	bool IsDefaultVariables();
	void ResetVariables();

	virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override;

	FSimpleDelegate OnParameterHidden;

	void ParameterHiddenEvent() {
		if (OnParameterHidden.IsBound())
		{
			OnParameterHidden.Execute();
		}
	};

	FHiddenItemsManager& GetHiddenManager() { return HiddenVarsManager; }

private:

	UPROPERTY()
	FHiddenItemsManager HiddenVarsManager;
};