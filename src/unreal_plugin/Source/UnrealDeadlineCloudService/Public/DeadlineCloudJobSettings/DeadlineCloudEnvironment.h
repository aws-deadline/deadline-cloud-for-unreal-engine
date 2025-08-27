// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once
#include "PythonAPILibraries/PythonYamlLibrary.h"
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

    UPROPERTY(VisibleAnywhere, BlueprintReadWrite, Category = "Parameters")
	FString Name;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FDeadlineCloudEnvironmentVariablesMap Variables;

	TArray<FName> HiddenVarsList;

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

	void AddHiddenParameter(FName Parameter)
	{
		UserHiddenParametersList.Add(Parameter);
		Modify();
		MarkPackageDirty();
		ParameterHiddenEvent();
	};
	void ClearHiddenParameters()
	{
		UserHiddenParametersList.Empty();
		Modify();
		MarkPackageDirty();
	};
	bool AreEmptyHiddenParameters() { return UserHiddenParametersList.IsEmpty(); };
	bool ContainsHiddenParameters(FName Parameter) { return UserHiddenParametersList.Contains(Parameter); };
	void RemoveHiddenParameter(FName Parameter) {
		UserHiddenParametersList.Remove(Parameter);
		Modify();
		MarkPackageDirty();
		ParameterHiddenEvent();
	};
	FSimpleDelegate OnParameterHidden;

	void ParameterHiddenEvent() {
		if (OnParameterHidden.IsBound())
		{
			OnParameterHidden.Execute();
		}
	};

	void ResetParametersHiddenToDefault() 
	{
		for (auto Variable : Variables.Variables)
		{
			AddHiddenParameter(FName(Variable.Key));
		}
	};

	bool IsParametersHiddenByDefault() 
	{ 
		bool bAllParametersHidden = true;
		for (auto Variable : Variables.Variables)
		{
			if (!UserHiddenParametersList.Contains(Variable.Key))
			{
				bAllParametersHidden = false;
				break;
			}
		}
		return bAllParametersHidden;
	};

private:
	UPROPERTY(EditAnywhere, meta = (HideInDetailPanel, Category = "Parameters"))
	TArray<FName> UserHiddenParametersList;//hidden by user parameters
};