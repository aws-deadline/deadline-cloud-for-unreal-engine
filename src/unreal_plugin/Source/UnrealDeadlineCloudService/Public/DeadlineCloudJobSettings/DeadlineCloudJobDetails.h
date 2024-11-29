// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once

#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJob.h"
#include "DetailLayoutBuilder.h"
#include "IDetailCustomization.h"
#include "Fonts/SlateFontInfo.h"
#include "Misc/App.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Modules/ModuleManager.h"
#include "Styling/SlateTypes.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SCheckBox.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Input/SFilePathPicker.h"
#include "Widgets/Input/SMultiLineEditableTextBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SSeparator.h"
#include "Widgets/Notifications/SNotificationList.h"
#include "Framework/Notifications/NotificationManager.h"
#include "EditorDirectories.h"
#include "EditorStyleSet.h"
#include "SourceControlOperations.h"
#include "PropertyCustomizationHelpers.h"


class UDeadlineCloudJob;
class UMoviePipelineDeadlineCloudExecutorJob;


class FDeadlineCloudJobParametersArrayBuilder
    : public FDetailArrayBuilder
    , public TSharedFromThis<FDeadlineCloudJobParametersArrayBuilder>
{
public:

    static TSharedRef<FDeadlineCloudJobParametersArrayBuilder> MakeInstance(
        TSharedRef<IPropertyHandle> InPropertyHandle);

    FDeadlineCloudJobParametersArrayBuilder(
        TSharedRef<IPropertyHandle> InPropertyHandle);

    void GenerateWrapperStructHeaderRowContent(FDetailWidgetRow& NodeRow, TSharedRef<SWidget> NameContent);

    void OnEyeHideWidgetButtonClicked(FName NameWidget) const;
    bool IsPropertyHidden(FName Parameter) const;


    FUIAction EmptyCopyPasteAction;
    FOnIsEnabled OnIsEnabled;

    TObjectPtr<UMoviePipelineDeadlineCloudExecutorJob> MrqJob;
    TObjectPtr<UDeadlineCloudJob> Job;

private:
    //
    static UDeadlineCloudJob* GetOuterJob(TSharedRef<IPropertyHandle> Handle);

    void OnGenerateEntry(TSharedRef<IPropertyHandle> ElementProperty, int32 ElementIndex, IDetailChildrenBuilder& ChildrenBuilder) const;
    bool IsResetToDefaultVisible(TSharedPtr<IPropertyHandle> PropertyHandle, FString InParameterName) const;

    void ResetToDefaultHandler(TSharedPtr<IPropertyHandle> PropertyHandle, FString InParameterName) const;
    TSharedPtr<IPropertyHandleArray> ArrayProperty;
    TSharedRef<IPropertyHandle> BaseProperty;

    bool IsEyeWidgetEnabled(FName Parameter) const;
};

class FDeadlineCloudJobParametersArrayCustomization : public IPropertyTypeCustomization
{
public:

    static TSharedRef<IPropertyTypeCustomization> MakeInstance()
    {
        return MakeShared<FDeadlineCloudJobParametersArrayCustomization>();
    }

    FDeadlineCloudJobParametersArrayCustomization() = default;

    /** Begin IPropertyTypeCustomization interface */
    virtual void CustomizeHeader(
        TSharedRef<IPropertyHandle> InPropertyHandle,
        FDetailWidgetRow& InHeaderRow,
        IPropertyTypeCustomizationUtils& InCustomizationUtils) override;

    virtual void CustomizeChildren(
        TSharedRef<IPropertyHandle> InPropertyHandle,
        IDetailChildrenBuilder& InChildBuilder,
        IPropertyTypeCustomizationUtils& InCustomizationUtils) override;
    /** End IPropertyTypeCustomization interface */

private:
    static UMoviePipelineDeadlineCloudExecutorJob* GetMrqJob(TSharedRef<IPropertyHandle> Handle);
    static UDeadlineCloudJob* GetJob(TSharedRef<IPropertyHandle> Handle);

    TSharedPtr<FDeadlineCloudJobParametersArrayBuilder> ArrayBuilder;

};


class FDeadlineCloudJobDetails : public IDetailCustomization
{
public:

    static TSharedRef<IDetailCustomization> MakeInstance();
    virtual  void CustomizeDetails(IDetailLayoutBuilder& DetailBuilder) override;
    IDetailLayoutBuilder* MainDetailLayout;

    TWeakObjectPtr<UDeadlineCloudJob> Settings;

    void OnConsistencyButtonClicked();
    void OnViewAllButtonClicked();

    EVisibility GetConsistencyWidgetVisibility() const;
    EVisibility GetEyeWidgetVisibility() const;

private:
    void RespondToEvent();
    void ForceRefreshDetails();
    bool CheckConsistency(UDeadlineCloudJob* Job);
    bool bCheckConsistensyPassed = true;

    bool IsStepContainsErrors() const;
    EVisibility GetStepErrorWidgetVisibility() const;
    EVisibility GetStepDefaultWidgetVisibility() const;

    bool IsEnvironmentContainsErrors() const;
    EVisibility GetEnvironmentErrorWidgetVisibility() const;
    EVisibility GetEnvironmentDefaultWidgetVisibility() const;
};

