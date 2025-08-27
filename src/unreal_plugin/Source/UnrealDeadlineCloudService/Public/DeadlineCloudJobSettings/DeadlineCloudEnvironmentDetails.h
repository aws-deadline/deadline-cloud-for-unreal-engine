// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJob.h"
#include "DetailLayoutBuilder.h"
#include "IDetailCustomization.h"
#include "PropertyCustomizationHelpers.h"


class UDeadlineCloudEnvironment;
class UMoviePipelineDeadlineCloudExecutorJob;

class FDeadlineCloudEnvironmentParametersMapBuilder
    : public IDetailCustomNodeBuilder
    , public TSharedFromThis<FDeadlineCloudEnvironmentParametersMapBuilder>
{
public:

    static TSharedRef<FDeadlineCloudEnvironmentParametersMapBuilder> MakeInstance(
        TSharedRef<IPropertyHandle> InPropertyHandle);

    FDeadlineCloudEnvironmentParametersMapBuilder(
        TSharedRef<IPropertyHandle> InPropertyHandle);

    virtual FName GetName() const override;
    virtual bool InitiallyCollapsed() const override { return false; }
    virtual void GenerateHeaderRowContent(FDetailWidgetRow& InNodeRow) override {}
    virtual void GenerateChildContent(IDetailChildrenBuilder& InChildrenBuilder) override;
    virtual TSharedPtr<IPropertyHandle> GetPropertyHandle() const override;
    virtual void SetOnRebuildChildren(FSimpleDelegate InOnRebuildChildren) override;

    FUIAction EmptyCopyPasteAction;
    TObjectPtr<UMoviePipelineDeadlineCloudExecutorJob> MrqJob;

private:

    void OnEyeHideWidgetButtonClicked(FName Property) const;
    bool IsPropertyHidden(FName Parameter) const;
    bool IsEyeWidgetEnabled(FName Parameter) const;
    bool IsParameterChangedFromDefault(FName Parameter) const;
    UDeadlineCloudEnvironment* GetOuterEnvironment() const;

    FSimpleDelegate OnRebuildChildren;
    TSharedPtr<IPropertyHandleMap> MapProperty;
    TSharedRef<IPropertyHandle> BaseProperty;
};

class FDeadlineCloudEnvironmentParametersMapCustomization : public IPropertyTypeCustomization
{
public:

    static TSharedRef<IPropertyTypeCustomization> MakeInstance()
    {
        return MakeShared<FDeadlineCloudEnvironmentParametersMapCustomization>();
    }

    FDeadlineCloudEnvironmentParametersMapCustomization() = default;

    bool IsResetToDefaultVisible(TSharedPtr<IPropertyHandle> PropertyHandle) const;

    void ResetToDefaultHandler(TSharedPtr<IPropertyHandle> PropertyHandle) const;

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

    static UDeadlineCloudEnvironment* GetOuterEnvironment(TSharedRef<IPropertyHandle> Handle);
private:
    FUIAction EmptyCopyPasteAction;
    TSharedPtr<FDeadlineCloudEnvironmentParametersMapBuilder> ArrayBuilder;
};


class FDeadlineCloudEnvironmentDetails : public IDetailCustomization
{
public:

    static TSharedRef<IDetailCustomization> MakeInstance();
    virtual  void CustomizeDetails(IDetailLayoutBuilder& DetailBuilder) override;
    IDetailLayoutBuilder* MainDetailLayout;
    TWeakObjectPtr<UDeadlineCloudEnvironment> Settings;

    void OnConsistencyButtonClicked();
    EVisibility GetWidgetVisibility() const { return (!bCheckConsistensyPassed) ? EVisibility::Visible : EVisibility::Collapsed; }
	void OnResetHiddenParametersClicked();
    EVisibility GetEyeWidgetVisibility() const;

private:

    void ForceRefreshDetails();
    void RespondToEvent();
    bool CheckConsistency(UDeadlineCloudEnvironment* Env);
    bool bCheckConsistensyPassed = true;
};

