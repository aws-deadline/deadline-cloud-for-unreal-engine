#pragma once

#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "DeadlineCloudJobSettings/DeadlineCloudStep.h"
#include "DetailLayoutBuilder.h"
#include "IDetailCustomization.h"


class UDeadlineCloudStep;


class FDeadlineCloudStepDetails : public IDetailCustomization
{
private:
    TWeakObjectPtr<UDeadlineCloudStep> Settings;
    TArray <FStepParameterSpace> StepParameters;

public:
    static TSharedRef<IDetailCustomization> MakeInstance();
    virtual  void CustomizeDetails(IDetailLayoutBuilder& DetailBuilder) override;

private:
    FString CurrentFilePath;
    FString GetCurrentFilePath() const
    {
        return CurrentFilePath;
    }

    void OnFilePathPicked(const FString& PickedPath)
    {
        CurrentFilePath = PickedPath;
    }


};