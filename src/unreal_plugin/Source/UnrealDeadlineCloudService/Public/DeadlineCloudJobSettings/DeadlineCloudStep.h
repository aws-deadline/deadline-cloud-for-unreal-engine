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

	FSimpleDelegate OnPathChanged;

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
	FParametersConsistencyCheckResult CheckStepParametersConsistency(const UDeadlineCloudStep* Step);

	UFUNCTION(BlueprintCallable, Category = "Parameters")
	void FixStepParametersConsistency(UDeadlineCloudStep* Step);

    UFUNCTION(BlueprintCallable, Category="Parameters")
	TArray<FStepTaskParameterDefinition> GetStepParameters();

	UFUNCTION(BlueprintCallable, Category="Parameters")
	void SetStepParameters(TArray<FStepTaskParameterDefinition> InStepParameters);

	void AddHiddenParameter(FName Parameter)
	{
		HiddenParametersList.Add(Parameter);
		Modify();
		MarkPackageDirty();
		ParameterHiddenEvent();
	};
	void ClearHiddenParameters()
	{
		HiddenParametersList.Empty();
		Modify();
		MarkPackageDirty();
	};
	bool AreEmptyHiddenParameters() { return HiddenParametersList.IsEmpty(); };
	bool ContainsHiddenParameters(FName Parameter) { return HiddenParametersList.Contains(Parameter); };
	void RemoveHiddenParameters(FName Parameter) {
		HiddenParametersList.Remove(Parameter);
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
	bool GetDisplayHiddenParameters() { return bDisplayHiddenWidgets; };
	void SetDisplayHiddenParameters(bool ShowParameters) { bDisplayHiddenWidgets = ShowParameters; };
private:
	UPROPERTY(EditAnywhere, Category = "Parameters", meta = (HideInDetailPanel))
	TArray<FName> HiddenParametersList;
	bool bDisplayHiddenWidgets = false;
};