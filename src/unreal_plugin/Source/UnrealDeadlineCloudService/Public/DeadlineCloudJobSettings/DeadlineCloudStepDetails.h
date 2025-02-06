// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once

#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "DeadlineCloudJobSettings/DeadlineCloudStep.h"
#include "DetailLayoutBuilder.h"
#include "IDetailCustomization.h"
#include "PropertyCustomizationHelpers.h"
#include "IPropertyTypeCustomization.h"

class UDeadlineCloudStep;
class UMoviePipelineDeadlineCloudExecutorJob;

class FDeadlineCloudStepParametersArrayBuilder
    : public FDetailArrayBuilder
    , public TSharedFromThis<FDeadlineCloudStepParametersArrayBuilder>
{
public:

    static TSharedRef<FDeadlineCloudStepParametersArrayBuilder> MakeInstance(
        TSharedRef<IPropertyHandle> InPropertyHandle);

    FDeadlineCloudStepParametersArrayBuilder(
		TSharedRef<IPropertyHandle> InPropertyHandle);

    void GenerateWrapperStructHeaderRowContent(FDetailWidgetRow& NodeRow, TSharedRef<SWidget> NameContent);

    bool IsResetToDefaultVisible(TSharedPtr<IPropertyHandle> PropertyHandle, FString InParameterName) const;

    void ResetToDefaultHandler(TSharedPtr<IPropertyHandle> PropertyHandle, FString InParameterName) const;

    static UDeadlineCloudStep* GetOuterStep(TSharedRef<IPropertyHandle> Handle);

    FUIAction EmptyCopyPasteAction;
    FOnIsEnabled OnIsEnabled;


    void OnEyeHideWidgetButtonClicked(FName NameWidget) const;
    bool IsPropertyHidden(FName Parameter) const;
    TObjectPtr<UMoviePipelineDeadlineCloudExecutorJob> MrqJob;
    TObjectPtr<UDeadlineCloudStep> Step;
    FName StepName;

    static UMoviePipelineDeadlineCloudExecutorJob* GetMrqJob(TSharedRef<IPropertyHandle> Handle);



private:
    void OnGenerateEntry(TSharedRef<IPropertyHandle> ElementProperty, int32 ElementIndex, IDetailChildrenBuilder& ChildrenBuilder) const;

    TArray<FName> PropertiesToShow = { "ChunkSize" };
	TSharedPtr<IPropertyHandleArray> ArrayProperty;

    bool IsEyeWidgetEnabled(FName Parameter) const;
};

class FDeadlineCloudStepParametersArrayCustomization : public IPropertyTypeCustomization
{
public:

    static TSharedRef<IPropertyTypeCustomization> MakeInstance()
    {
        return MakeShared<FDeadlineCloudStepParametersArrayCustomization>();
    }


    bool IsEnabled(TSharedRef<IPropertyHandle> InPropertyHandle) const;

	FDeadlineCloudStepParametersArrayCustomization() = default;

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
    static UDeadlineCloudStep* GetStep(TSharedRef<IPropertyHandle> Handle);
    TSharedPtr<FDeadlineCloudStepParametersArrayBuilder> ArrayBuilder;
};

class FDeadlineCloudStepParameterListBuilder
    : public FDetailArrayBuilder
    , public TSharedFromThis<FDeadlineCloudStepParameterListBuilder>
{
public:

    static TSharedRef<FDeadlineCloudStepParameterListBuilder> MakeInstance(
        TSharedRef<IPropertyHandle> InPropertyHandle, EValueType Type
    );

	FDeadlineCloudStepParameterListBuilder(
		TSharedRef<IPropertyHandle> InPropertyHandle);

    void GenerateWrapperStructHeaderRowContent(FDetailWidgetRow& NodeRow, TSharedRef<SWidget> NameContent);

    FUIAction EmptyCopyPasteAction;
    FOnIsEnabled OnIsEnabled;

private:
    void OnGenerateEntry(TSharedRef<IPropertyHandle> ElementProperty, int32 ElementIndex, IDetailChildrenBuilder& ChildrenBuilder) const;

    EValueType Type;
    TSharedPtr<IPropertyHandleArray> ArrayProperty;
};

class FDeadlineCloudStepParameterListCustomization : public IPropertyTypeCustomization
{
public:

    static TSharedRef<IPropertyTypeCustomization> MakeInstance()
    {
        return MakeShared<FDeadlineCloudStepParameterListCustomization>();
    }

	FDeadlineCloudStepParameterListCustomization() = default;

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

    TSharedPtr<FDeadlineCloudStepParameterListBuilder> ArrayBuilder;
};

class FDeadlineCloudStepDetails : public IDetailCustomization
{
private:
    TWeakObjectPtr<UDeadlineCloudStep> Settings;
    IDetailLayoutBuilder* MainDetailLayout;
public:
    static TSharedRef<IDetailCustomization> MakeInstance();
    virtual  void CustomizeDetails(IDetailLayoutBuilder& DetailBuilder) override;

    void OnViewAllButtonClicked();
    void OnConsistencyButtonClicked();
    bool CheckConsistency(UDeadlineCloudStep* Step);
    bool bCheckConsistensyPassed = true;
    EVisibility GetWidgetVisibility() const { return (!bCheckConsistensyPassed) ? EVisibility::Visible : EVisibility::Collapsed; }

    EVisibility GetEyeWidgetVisibility() const;

    bool IsEnvironmentContainsErrors() const;
    EVisibility GetEnvironmentErrorWidgetVisibility() const;
    EVisibility GetEnvironmentDefaultWidgetVisibility() const;

private:

    void RespondToEvent();
    void ForceRefreshDetails();
};