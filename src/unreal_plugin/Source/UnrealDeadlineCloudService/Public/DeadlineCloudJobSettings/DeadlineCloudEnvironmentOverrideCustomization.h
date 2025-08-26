// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once

#include "IPropertyTypeCustomization.h"

#include "PropertyCustomizationHelpers.h"
#include "Widgets/SWidget.h"



class FDetailArrayBuilder;
class FDeadlineCloudEnvironmentOverrideCustomization : public IPropertyTypeCustomization
{
public:
    static TSharedRef<IPropertyTypeCustomization> MakeInstance();

    virtual void CustomizeHeader(TSharedRef<IPropertyHandle> StructPropertyHandle, FDetailWidgetRow& HeaderRow, IPropertyTypeCustomizationUtils& StructCustomizationUtils) override;
    virtual void CustomizeChildren(TSharedRef<IPropertyHandle> StructPropertyHandle, IDetailChildrenBuilder& StructBuilder, IPropertyTypeCustomizationUtils& StructCustomizationUtils) override;
private:
	void AddDefaultEnvironmentOverrideHeaderRow(TSharedRef<IPropertyHandle> InPropertyHandle, FDetailWidgetRow& HeaderRow, const FString& TitlePrefix, const FString& TagPrefix);
};

class FDeadlineCloudEnvOverrideArrayBuilder
    : public FDetailArrayBuilder
    , public TSharedFromThis<FDeadlineCloudEnvOverrideArrayBuilder>
{
public:
    /** Creates property customization instance */
    static TSharedRef<FDeadlineCloudEnvOverrideArrayBuilder> MakeInstance(
        TSharedRef<IPropertyHandle> InPropertyHandle);

    /**
     * @param InPropertyHandle - array property handle to display in details view
     */
    FDeadlineCloudEnvOverrideArrayBuilder(
        TSharedRef<IPropertyHandle> InPropertyHandle);

    /** FDetailArrayBuilder Interface */
    virtual void GenerateHeaderRowContent(FDetailWidgetRow& NodeRow) override;

    /** Generates wrapper struct header row content */
    void GenerateWrapperStructHeaderRowContent(FDetailWidgetRow& NodeRow, TSharedRef<SWidget> NameContent);

private:
    /** Generates array element widget */
    void OnGenerateEntry(TSharedRef<IPropertyHandle> ElementProperty, int32 ElementIndex, IDetailChildrenBuilder& ChildrenBuilder) const;

    /** Referenced array property */
    TSharedPtr<IPropertyHandleArray> ArrayProperty;

    /** Original property handle */
    TSharedPtr<IPropertyHandle> PropertyHandle;
}; 