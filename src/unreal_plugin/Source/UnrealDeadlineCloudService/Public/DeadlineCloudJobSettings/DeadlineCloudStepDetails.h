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

public:
    static TSharedRef<IDetailCustomization> MakeInstance();
    virtual  void CustomizeDetails(IDetailLayoutBuilder& DetailBuilder) override;

private:
    TSharedRef<SWidget> GenerateStringsArrayContent(const TArray<FString>& StringArray);
    TSharedRef<SWidget> GenerateTasksContent(const TArray<FStepTaskParameterDefinition> tasks);

};