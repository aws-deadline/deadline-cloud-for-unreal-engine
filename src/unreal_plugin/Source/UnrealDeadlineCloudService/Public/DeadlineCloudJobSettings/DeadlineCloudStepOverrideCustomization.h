
// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once

#include "IPropertyTypeCustomization.h"
#include "PropertyCustomizationHelpers.h"
#include "Widgets/SWidget.h"

class FDetailArrayBuilder;
class FDeadlineCloudAttachmentArrayBuilder;
class IDetailPropertyRow;
class UMoviePipelineDeadlineCloudExecutorJob;
class FPropertyAvailabilityHandler;


class FDeadlineCloudStepOverrideCustomization : public IPropertyTypeCustomization
{
public:
	static TSharedRef<IPropertyTypeCustomization> MakeInstance();

	virtual void CustomizeHeader(TSharedRef<IPropertyHandle> StructPropertyHandle, FDetailWidgetRow& HeaderRow, IPropertyTypeCustomizationUtils& StructCustomizationUtils) override;
	virtual void CustomizeChildren(TSharedRef<IPropertyHandle> StructPropertyHandle, IDetailChildrenBuilder& StructBuilder, IPropertyTypeCustomizationUtils& StructCustomizationUtils) override;
};

class FDeadlineCloudStepOverrideArrayBuilder
	: public FDetailArrayBuilder
	, public TSharedFromThis<FDeadlineCloudStepOverrideArrayBuilder>
{
public:
	/** Creates property customization instance */
	static TSharedRef<FDeadlineCloudStepOverrideArrayBuilder> MakeInstance(
		TSharedRef<IPropertyHandle> InPropertyHandle);

	/**
	 * @param InPropertyHandle - array property handle to display in details view
	 */
	FDeadlineCloudStepOverrideArrayBuilder(
		TSharedRef<IPropertyHandle> InPropertyHandle);

	/** FDetailArrayBuilder Interface */
	virtual void GenerateHeaderRowContent(FDetailWidgetRow& NodeRow) override;

	/** Generates wrapper struct header row content */
	void GenerateWrapperStructHeaderRowContent(FDetailWidgetRow& NodeRow, TSharedRef<SWidget> NameContent);

	/** Delegate for property enabled/disabled check */
	FOnIsEnabled OnIsEnabled;

private:
	/** Generates array element widget */
	void OnGenerateEntry(TSharedRef<IPropertyHandle> ElementProperty, int32 ElementIndex, IDetailChildrenBuilder& ChildrenBuilder) const;

	/** Referenced array property */
	TSharedPtr<IPropertyHandleArray> ArrayProperty;

	/** Original property handle */
	TSharedPtr<IPropertyHandle> PropertyHandle;

	/** Handles overridden settings in UI */
	TSharedPtr<FPropertyAvailabilityHandler> PropertyOverrideHandler;
};
