#pragma once

#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "DeadlineCloudStep.h"
#include "CoreMinimal.h"
#include "DeadlineCloudJobDataAsset.h"
#include "DeadlineCloudEnvironment.h"
#include "DeadlineCloudJob.generated.h"

/**
 * All Deadline Cloud job settings container struct
 */

//DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnDataChanged);


USTRUCT(BlueprintType)
struct FPathToFile
{
	GENERATED_BODY()


	UPROPERTY( EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FFilePath PathToTemplate;
};

UCLASS(BlueprintType, Blueprintable, Config = Game)
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudJob : public UDataAsset
{
	GENERATED_BODY()
public:

	UDeadlineCloudJob();

	FSimpleMulticastDelegate OnSomethingChanged;


	void TriggerChange()
	{
		OnSomethingChanged.Broadcast();
	}

	UPROPERTY(Config, EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FString Name;

	UPROPERTY(Config, EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FFilePath PathToTemplate;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FPathToFile PathToTemplateStruct;

	/** Deadline cloud job settings container struct */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Preset")
	FDeadlineCloudJobPresetStruct JobPresetStruct;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	TArray<UDeadlineCloudStep*> Steps;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	TArray<UDeadlineCloudEnvironment*> Environments;

//private:	
//	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	TArray <FParameterDefinition> JobParameters;

public:
	/*Read path */
	UFUNCTION()
	void OpenJobFile(const FString& Path);

	UFUNCTION()
	void ReadName(const FString& Path);

	TArray <FParameterDefinition> GetJobParameters();



public:

	virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override
	{
		Super::PostEditChangeProperty(PropertyChangedEvent);
		if (PropertyChangedEvent.Property != nullptr) {

			FName PropertyName = PropertyChangedEvent.Property->GetFName();
			if (PropertyName == "FilePath")
			{		
				TriggerChange();
			}
		}
	}


};
