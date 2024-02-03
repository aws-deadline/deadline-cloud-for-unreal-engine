// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once

#include "IPropertyTypeCustomization.h"
#include "PropertyCustomizationHelpers.h"

class FDetailArrayBuilder;
class FDeadlineCloudAttachmentArrayBuilder;
class IDetailPropertyRow;
class UMoviePipelineDeadlineCloudExecutorJob;

/**
 * Handles Deadline Cloud job properties availability in Deadline Cloud Job DataAsset and MRQ Job preset.
 * Intended to be used in implementations of IPropertyTypeCustomization
 * - Adds checkboxes in details view rows for enabling/disabling property editing
 * - Handles checkboxes state changes
 * @ref FDeadlineCloudJobPresetDetailsCustomization, @ref FDeadlineCloudAttachmentDetailsCustomization, @ref FDeadlineCloudAttachmentArrayCustomization
 */
class FPropertyAvailabilityHandler
{
	UMoviePipelineDeadlineCloudExecutorJob* Job;
	TSet<FName> PropertiesDisabledInDataAsset;
public:
	/**
	 * @param InJob - Deadline Cloud MRQ job for adding customization to detail rows
	 */
	FPropertyAvailabilityHandler(UMoviePipelineDeadlineCloudExecutorJob* InJob);

	/**
	 * @param StructHandle MRQ job property handle
	 * @return MRQ job of the property handle
	 */
	static UMoviePipelineDeadlineCloudExecutorJob* GetOuterJob(TSharedRef<IPropertyHandle> StructHandle);

	/**
	 * Adds check box in "Name" view widget for provided property row. Makes property value editable in MRQ view
	 * @param PropertyRow property row interface
	 */
	void EnableInMovieRenderQueue(IDetailPropertyRow& PropertyRow) const;

	/**
	 * Disables row for editing in Deadline Cloud job preset DataAsset @ref UDeadlineCloudJobPreset 
	 * @param PropertyRow property row interface
	 */
	void DisableRowInDataAsset(const IDetailPropertyRow& PropertyRow);

	/**
	 * Checks if the property should is enabled for editing in MRQ job view
	 * @param InPropertyPath property path, in Unreal reflection format
	 */
	bool IsPropertyRowEnabledInMovieRenderJob(const FName& InPropertyPath);

	/**
	 * Checks if the property should is enabled for editing in Data Asset
	 * @param InPropertyPath property path, in Unreal reflection format
	 */
	bool IsPropertyRowEnabledInDataAsset(const FName& InPropertyPath);
};

/**
 * MRQ Job properties details customization for overridable Deadline cloud job settings.
 * Should be applied to the properties of the DeadlineCloud MRQ job grouped together into ustruct.
 * @ref FDeadlineCloudJobSharedSettingsStruct, @ref FDeadlineCloudHostRequirementsStruct
 */
class FDeadlineCloudJobPresetDetailsCustomization : public IPropertyTypeCustomization
{
public:

	/** Create property customization instance */
	static TSharedRef<IPropertyTypeCustomization> MakeInstance();

	/** Begin IPropertyTypeCustomization interface */
	virtual void CustomizeHeader(TSharedRef<IPropertyHandle> PropertyHandle, FDetailWidgetRow& HeaderRow, IPropertyTypeCustomizationUtils& CustomizationUtils) override;
	virtual void CustomizeChildren(TSharedRef<IPropertyHandle> StructHandle, IDetailChildrenBuilder& ChildBuilder, IPropertyTypeCustomizationUtils& CustomizationUtils) override;
	/** End IPropertyTypeCustomization interface */

	/**
	 * Checks if a property passed in the arguments is hidden in MRQ job details view. Always returns false in current implementation
	 * @param InPropertyPath object property path in Unreal reflection system format
	 */
	static bool IsPropertyHiddenInMovieRenderQueue(const FName& InPropertyPath);
	// static bool IsPropertyRowEnabledInMovieRenderJob(const FName& InPropertyPath, UMoviePipelineDeadlineCloudExecutorJob* Job);
	
protected:
	/**
	 * Adds ability to mark property as overridable in Deadline Cloud DataAsset 
	 * @param PropertyRow Unreal property row interface
	 */
	void CustomizeStructChildrenInAssetDetails(IDetailPropertyRow& PropertyRow) const;

	/**
	 * Adds ability to override default job setting value for Deadline Cloud MRQ job
	 * @param PropertyRow Unreal property ro interface
	 * @param Job Deadline Cloud MRQ job
	 */
	void CustomizeStructChildrenInMovieRenderQueue(IDetailPropertyRow& PropertyRow, UMoviePipelineDeadlineCloudExecutorJob* Job) const;

	// static bool IsResetToDefaultVisibleOverride(TSharedPtr<IPropertyHandle> PropertyHandle, UMoviePipelineDeadlineCloudExecutorJob* Job);
	// static void ResetToDefaultOverride(TSharedPtr<IPropertyHandle> PropertyHandle, UMoviePipelineDeadlineCloudExecutorJob* Job);
protected:
	/** Handles overridden settings in UI */
	TSharedPtr<FPropertyAvailabilityHandler> PropertyOverrideHandler;
};

/**
 * Deadline cloud job attachment properties UI customization.
 */
class FDeadlineCloudAttachmentDetailsCustomization : public IPropertyTypeCustomization
{
public:

	/** Create property customization instance */
	static TSharedRef< IPropertyTypeCustomization > MakeInstance();

	/** Begin IPropertyTypeCustomization interface */
	virtual void CustomizeHeader(TSharedRef<IPropertyHandle> PropertyHandle, FDetailWidgetRow& HeaderRow, IPropertyTypeCustomizationUtils& CustomizationUtils) override;
	virtual void CustomizeChildren(TSharedRef<IPropertyHandle> StructHandle, IDetailChildrenBuilder& ChildBuilder, IPropertyTypeCustomizationUtils& CustomizationUtils) override;
	/** End IPropertyTypeCustomization interface */
protected:
	/** Handles overridden settings in UI */
	TSharedPtr<FPropertyAvailabilityHandler> PropertyOverrideHandler;
};

/**
 * Deadline cloud job attachment array properties UI customization
 */
class FDeadlineCloudAttachmentArrayCustomization : public IPropertyTypeCustomization
{
public:

	/** Creates property customization instance */
	static TSharedRef<IPropertyTypeCustomization> MakeInstance()
	{
		return MakeShared<FDeadlineCloudAttachmentArrayCustomization>();
	}

	FDeadlineCloudAttachmentArrayCustomization() {}
	
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
	/** Attachment arrays UI handler */
	TSharedPtr<FDeadlineCloudAttachmentArrayBuilder> ArrayBuilder;

	/** Handles overridden settings in UI */
	TSharedPtr<FPropertyAvailabilityHandler> PropertyOverrideHandler;
};

/**
 * Array details view customization. Adds ability to show/hide array details view and enable/disable editing array elements rows
 */
class FDeadlineCloudAttachmentArrayBuilder
	: public FDetailArrayBuilder
	, public TSharedFromThis<FDeadlineCloudAttachmentArrayBuilder>
{
public:
	/** Creates property customization instance */
	static TSharedRef<FDeadlineCloudAttachmentArrayBuilder> MakeInstance(
		TSharedRef<IPropertyHandle> InPropertyHandle);

	/**
	 * @param InPropertyHandle - array property handle to display in details view 
	 */
	FDeadlineCloudAttachmentArrayBuilder(
		TSharedRef<IPropertyHandle> InPropertyHandle);
	
	/** FDetailArrayBuilder Interface */
	virtual void GenerateHeaderRowContent(FDetailWidgetRow& NodeRow) override;

	/**
	 * Attachment array properties are wrapped into ustruct objects:
	 * @ref FDeadlineCloudFileAttachmentsStruct @ref FDeadlineCloudDirectoryAttachmentsArray.
	 * This allows to use custom version of ArrayBuilder and provide custom UI handling for property enabled/disabled and visible/invisible statuses
	 * In order to make property look in the UI as ordinary Unreal array property we wrap the struct header row with the widget generated by FDetailArrayBuilder
	 * And don't generate default header for array property in its turn
	 */
	void GenerateWrapperStructHeaderRowContent(FDetailWidgetRow& NodeRow, TSharedRef<SWidget> NameContent);

	/** Delegate for property enabled/disabled check */
	FOnIsEnabled OnIsEnabled;

private:
	/** Generates array element widget */
	void OnGenerateEntry(TSharedRef<IPropertyHandle> ElementProperty, int32 ElementIndex, IDetailChildrenBuilder& ChildrenBuilder) const;

	/** Referenced array property */
	TSharedPtr<IPropertyHandleArray> ArrayProperty;
};

