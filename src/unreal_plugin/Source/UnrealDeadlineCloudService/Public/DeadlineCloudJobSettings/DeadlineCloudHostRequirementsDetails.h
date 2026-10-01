// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "DetailLayoutBuilder.h"
#include "IDetailChildrenBuilder.h"
#include "IDetailCustomization.h"
#include "PropertyCustomizationHelpers.h"
#include "DeadlineCloudJobSettings/DeadlineCloudDetailsWidgetsHelper.h"
#include "Misc/Optional.h"

class FDeadlineCloudHostRequirementsDetails : public IDetailCustomization
{
public:
    static TSharedRef<IDetailCustomization> MakeInstance();
    virtual  void CustomizeDetails(IDetailLayoutBuilder& DetailBuilder) override;
    IDetailLayoutBuilder* MainDetailLayout;
    TWeakObjectPtr<class UDeadlineCloudHostRequirements> Settings;

	void OnResetHiddenParametersClicked();
    EVisibility GetEyeWidgetVisibility() const;

private:
    void ForceRefreshDetails();
    void RespondToEvent();
};

class FDeadlineCloudHostRequirementCustomization : public IPropertyTypeCustomization
{
public:
	static TSharedRef<IPropertyTypeCustomization> MakeInstance();

	virtual void CustomizeHeader(TSharedRef<IPropertyHandle> StructPropertyHandle,
		FDetailWidgetRow& HeaderRow,
		IPropertyTypeCustomizationUtils& CustomizationUtils) override;
	virtual void CustomizeChildren(TSharedRef<IPropertyHandle> StructPropertyHandle,
		IDetailChildrenBuilder& StructBuilder,
		IPropertyTypeCustomizationUtils& CustomizationUtils) override;

private:
	void AddDefaultsAmountsRequirementsRows(
		TSharedPtr<IPropertyHandle> AttributesMapHandle,
		IDetailChildrenBuilder& StructBuilder,
		TSharedRef<IPropertyHandle> StructPropertyHandle);
	void AddDefaultsAttributesRequirementsRows(
		TSharedPtr<IPropertyHandle> AttributesMapHandle,
		IDetailChildrenBuilder& StructBuilder,
		TSharedRef<IPropertyHandle> StructPropertyHandle);
};


class FDeadlineCloudCustomRequirementCustomization
	: public IDetailCustomNodeBuilder
{
public:
	FDeadlineCloudCustomRequirementCustomization(TSharedRef<IPropertyHandle> InPropertyHandle);

	virtual void GenerateHeaderRowContent(FDetailWidgetRow& InNodeRow) override;
	virtual void GenerateChildContent(IDetailChildrenBuilder& InChildrenBuilder) override;
	virtual TSharedPtr<IPropertyHandle> GetPropertyHandle() const override;

	virtual FText GetHeaderRowName() const = 0;
	virtual TSharedRef<class IDetailCustomNodeBuilder> CreateChildBuilder(
		TSharedRef<IPropertyHandle> InPropertyHandle, bool bIsDefaultAttribute) = 0;
	virtual bool IsDefaultRequirement(const TSharedPtr<IPropertyHandle>& MapHandle) = 0;
	virtual int32 GetFilteredCount(const TSharedPtr<IPropertyHandle>& Map) = 0;
	virtual FName GetName() const override = 0;
private:
	TSharedRef<IPropertyHandle> Property;
};

class FDeadlineCloudCustomAttributeRequirementCustomization
	: public FDeadlineCloudCustomRequirementCustomization
	, public TSharedFromThis<FDeadlineCloudCustomAttributeRequirementCustomization>
{
public:
	static TSharedRef<FDeadlineCloudCustomAttributeRequirementCustomization> MakeInstance(TSharedRef<IPropertyHandle> InPropertyHandle);
	FDeadlineCloudCustomAttributeRequirementCustomization(TSharedRef<IPropertyHandle> InPropertyHandle);

	virtual FText GetHeaderRowName() const override;
	virtual TSharedRef<class IDetailCustomNodeBuilder> CreateChildBuilder(
		TSharedRef<IPropertyHandle> InPropertyHandle, bool bIsDefaultAttribute) override;
	virtual bool IsDefaultRequirement(const TSharedPtr<IPropertyHandle>& MapHandle) override;
	virtual int32 GetFilteredCount(const TSharedPtr<IPropertyHandle>& Map) override;
	virtual FName GetName() const override;
private:
};

class FDeadlineCloudCustomAmountRequirementCustomization 
	: public FDeadlineCloudCustomRequirementCustomization
	, public TSharedFromThis<FDeadlineCloudCustomAmountRequirementCustomization>
{
public:
	static TSharedRef<FDeadlineCloudCustomAmountRequirementCustomization> MakeInstance(TSharedRef<IPropertyHandle> InPropertyHandle);
	FDeadlineCloudCustomAmountRequirementCustomization(TSharedRef<IPropertyHandle> InPropertyHandle);

	virtual FText GetHeaderRowName() const override;
	virtual TSharedRef<class IDetailCustomNodeBuilder> CreateChildBuilder(
		TSharedRef<IPropertyHandle> InPropertyHandle, bool bIsDefaultAttribute) override;
	virtual bool IsDefaultRequirement(const TSharedPtr<IPropertyHandle>& MapHandle) override;
	virtual int32 GetFilteredCount(const TSharedPtr<IPropertyHandle>& Map) override;
	virtual FName GetName() const override;
private:

};

class FDeadlineCloudRequirementBuilder
	: public IDetailCustomNodeBuilder
{
public:
	FDeadlineCloudRequirementBuilder(
		TSharedRef<IPropertyHandle> InPropertyHandle, bool IsDefaultRequirement);

	virtual FName GetName() const override = 0;
	virtual bool InitiallyCollapsed() const override { return true; }

	virtual void GenerateHeaderRowContent(FDetailWidgetRow& InNodeRow) override;
	virtual void GenerateChildContent(IDetailChildrenBuilder& InChildrenBuilder) override;
	virtual TSharedPtr<IPropertyHandle> GetPropertyHandle() const override;

	virtual TSharedRef<SWidget> CreateNameWidget(TSharedPtr<IPropertyHandle> NameHandle, FString Name, FString FriendlyName) = 0;
	virtual TSharedRef<SWidget> CreateValueWidget() = 0;
	virtual bool IsPropertyHidden(FName Parameter) const = 0;
	virtual bool IsEyeWidgetEnabled(FName Parameter) const  = 0;
	virtual bool IsParameterChangedFromDefault(FName Parameter) const = 0;
	virtual void OnEyeHideWidgetButtonClicked(FName PropertyName) const = 0;
	virtual void BindEyeWidget(TSharedRef<FDeadlineCloudDetailsWidgetsHelper::SEyeCheckBox> EyeWidget) = 0;

	TObjectPtr<UMoviePipelineDeadlineCloudExecutorJob> MrqJob;
	TObjectPtr<UDeadlineCloudHostRequirements> HostReq;
protected:

	TSharedRef<IPropertyHandle> Property;
	bool bIsDefaultRequirement;
	TSharedPtr<IPropertyHandle> IsEnabledHandle;
	TAttribute<bool> IsEnabledAttr;
};

class FDeadlineCloudAmountBuilder
	: public FDeadlineCloudRequirementBuilder
	, public TSharedFromThis<FDeadlineCloudAmountBuilder>
{
public:
	static TSharedRef<FDeadlineCloudAmountBuilder> MakeInstance(
		TSharedRef<IPropertyHandle> InPropertyHandle, bool IsDefaultRequirement);
	FDeadlineCloudAmountBuilder(
		TSharedRef<IPropertyHandle> InPropertyHandle, bool IsDefaultRequirement);

	virtual FName GetName() const override;

	virtual TSharedRef<SWidget> CreateNameWidget(TSharedPtr<IPropertyHandle> NameHandle, FString Name, FString FriendlyName) override;
	virtual TSharedRef<SWidget> CreateValueWidget() override;
	virtual bool IsPropertyHidden(FName Parameter) const override;
	virtual bool IsEyeWidgetEnabled(FName Parameter) const override;
	virtual bool IsParameterChangedFromDefault(FName Parameter) const override;
	virtual void OnEyeHideWidgetButtonClicked(FName Property) const override;
	virtual void BindEyeWidget(TSharedRef<FDeadlineCloudDetailsWidgetsHelper::SEyeCheckBox> EyeWidget) override;
private:
};

class FDeadlineCloudAttributeBuilder
	: public FDeadlineCloudRequirementBuilder
	, public TSharedFromThis<FDeadlineCloudAttributeBuilder>
{
public:
	static TSharedRef<FDeadlineCloudAttributeBuilder> MakeInstance(
		TSharedRef<IPropertyHandle> InPropertyHandle, bool bIsDefaultRequirement);
	FDeadlineCloudAttributeBuilder(
		TSharedRef<IPropertyHandle> InPropertyHandle, bool IsDefaultRequirement);

	virtual FName GetName() const override;

	virtual TSharedRef<SWidget> CreateNameWidget(TSharedPtr<IPropertyHandle> NameHandle, FString Name, FString FriendlyName) override;
	virtual TSharedRef<SWidget> CreateValueWidget() override;
	virtual bool IsPropertyHidden(FName Parameter) const override;
	virtual bool IsEyeWidgetEnabled(FName Parameter) const override;
	virtual bool IsParameterChangedFromDefault(FName Parameter) const override;
	virtual void OnEyeHideWidgetButtonClicked(FName Property) const override;
	virtual void BindEyeWidget(TSharedRef<FDeadlineCloudDetailsWidgetsHelper::SEyeCheckBox> EyeWidget) override;
private:

};