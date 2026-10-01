// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once
#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "DeadlineCloudJobSettings/DeadlineCloudHiddenParameters.h"

#include "DeadlineCloudHostRequirements.generated.h"

USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudHostRequirementsOverrides
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FDeadlineCloudHostRequirement HostRequirements;

	UPROPERTY()
	FSoftObjectPath SourceObjectPath;

	//copy only values for existing parameters
	void CopyParametersValuesFrom(const FDeadlineCloudHostRequirementsOverrides& Other);

	bool IsEmpty()
	{
		return HostRequirements.Amounts.IsEmpty() && HostRequirements.Attributes.IsEmpty();
	};
};


UCLASS(BlueprintType, Blueprintable)
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudHostRequirements : public UDataAsset
{
    GENERATED_BODY()
public:

    UDeadlineCloudHostRequirements();

	FSimpleDelegate OnPathChanged;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Host Requirements")
	FFilePath PathToTemplate;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Host Requirements")
	FDeadlineCloudHostRequirement HostRequirements;

	UFUNCTION(BlueprintCallable, Category = "Host Requirements")
	void OpenHostRequirementsFile(const FString& Path);

	virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override;

	FSimpleDelegate OnParameterHidden;

	void ParameterHiddenEvent() {
		if (OnParameterHidden.IsBound())
		{
			OnParameterHidden.Execute();
		}
	};

	FHiddenItemsManager& GetAmountsHiddenManager() { return HiddenAmountsManager; };
	FHiddenItemsManager& GetAttributesHiddenManager() { return HiddenAttributesManager; };

private:

	UPROPERTY()
	FHiddenItemsManager HiddenAmountsManager;

	UPROPERTY()
	FHiddenItemsManager HiddenAttributesManager;

};

