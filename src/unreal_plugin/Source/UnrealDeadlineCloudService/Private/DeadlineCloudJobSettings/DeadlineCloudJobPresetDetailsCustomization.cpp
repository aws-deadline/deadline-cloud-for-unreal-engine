// Copyright Epic Games, Inc. All Rights Reserved.

#include "DeadlineCloudJobSettings/DeadlineCloudJobPresetDetailsCustomization.h"
#include "MovieRenderPipeline/MoviePipelineDeadlineCloudExecutorJob.h"
#include "DetailWidgetRow.h"
#include "IDetailChildrenBuilder.h"
#include "IDetailGroup.h"
#include "PropertyCustomizationHelpers.h"
#include "Widgets/Input/SCheckBox.h"
#include "Misc/EngineVersionComparison.h"

class SEyeCheckBox : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS( SEyeCheckBox ){}

	SLATE_END_ARGS()
	
	void Construct(const FArguments& InArgs, const FName& InPropertyPath)
	{		
		ChildSlot
		[
			SNew(SBox)
			.Visibility(EVisibility::Visible)
			.HAlign(HAlign_Right)
			.WidthOverride(28)
			.HeightOverride(20)
#if UE_VERSION_NEWER_THAN(5, 1, -1)
			.Padding(4, 0)
#else
			.Padding(4)
#endif
			[
				SAssignNew(CheckBoxPtr, SCheckBox)
				.Style(&FAppStyle::Get().GetWidgetStyle<FCheckBoxStyle>("ToggleButtonCheckbox"))
				.Visibility_Lambda([this]()
				{
					return CheckBoxPtr.IsValid() && !CheckBoxPtr->IsChecked() ? EVisibility::Visible : IsHovered() ? EVisibility::Visible : EVisibility::Hidden;
				})
				.CheckedImage(FAppStyle::Get().GetBrush("Icons.Visible"))
				.CheckedHoveredImage(FAppStyle::Get().GetBrush("Icons.Visible"))
				.CheckedPressedImage(FAppStyle::Get().GetBrush("Icons.Visible"))
				.UncheckedImage(FAppStyle::Get().GetBrush("Icons.Hidden"))
				.UncheckedHoveredImage(FAppStyle::Get().GetBrush("Icons.Hidden"))
				.UncheckedPressedImage(FAppStyle::Get().GetBrush("Icons.Hidden"))
				.ToolTipText(NSLOCTEXT("FDeadlineJobPresetLibraryCustomization", "VisibleInMoveRenderQueueToolTip", "If true this property will be visible for overriding from Movie Render Queue."))
				.IsChecked_Lambda([InPropertyPath]()
				{
					return FDeadlineCloudJobPresetDetailsCustomization::IsPropertyHiddenInMovieRenderQueue(InPropertyPath)
								? ECheckBoxState::Unchecked
								: ECheckBoxState::Checked;
				})
			]
		];
	}

	TSharedPtr<SCheckBox> CheckBoxPtr;
};

TSharedRef<IPropertyTypeCustomization> FDeadlineCloudJobPresetDetailsCustomization::MakeInstance()
{
	return MakeShared<FDeadlineCloudJobPresetDetailsCustomization>();
}

void FDeadlineCloudJobPresetDetailsCustomization::CustomizeHeader(TSharedRef<IPropertyHandle> PropertyHandle, FDetailWidgetRow& HeaderRow,
	IPropertyTypeCustomizationUtils& CustomizationUtils)
{
}

void FDeadlineCloudJobPresetDetailsCustomization::CustomizeChildren(TSharedRef<IPropertyHandle> StructHandle,
                                                                    IDetailChildrenBuilder& ChildBuilder, IPropertyTypeCustomizationUtils& CustomizationUtils)
{
	UMoviePipelineDeadlineCloudExecutorJob* OuterJob = FPropertyAvailabilityHandler::GetOuterJob(StructHandle);
	PropertyOverrideHandler = MakeShared<FPropertyAvailabilityHandler>(OuterJob);

	TMap<FName, IDetailGroup*> CreatedCategories;
	const FName StructName(StructHandle->GetProperty()->GetFName());

	if (OuterJob)
	{
		IDetailGroup& BaseCategoryGroup = ChildBuilder.AddGroup(StructName, StructHandle->GetPropertyDisplayName());
		CreatedCategories.Add(StructName, &BaseCategoryGroup);
	}
	
	// For each map member and each struct member in the map member value
	uint32 NumChildren;
	StructHandle->GetNumChildren(NumChildren);
	
	// For each struct member
	for (uint32 ChildIndex = 0; ChildIndex < NumChildren; ++ChildIndex)
	{
		const TSharedRef<IPropertyHandle> ChildHandle = StructHandle->GetChildHandle(ChildIndex).ToSharedRef();

		// Skip properties that are hidden so we don't end up creating empty categories in the job details
		if (OuterJob && IsPropertyHiddenInMovieRenderQueue(*ChildHandle->GetProperty()->GetPathName()))
		{
			continue;
		}
		
		IDetailGroup* GroupToUse = nullptr;
		if (const FString* PropertyCategoryString = ChildHandle->GetProperty()->FindMetaData(TEXT("Category")))
		{
			FName PropertyCategoryName(*PropertyCategoryString);

			if (IDetailGroup** FoundCategory = CreatedCategories.Find(PropertyCategoryName))
			{
				GroupToUse = *FoundCategory;
			}
			else
			{
				if (OuterJob)
				{
					// IDetailGroup& NewGroup = CreatedCategories.FindChecked(StructName)->AddGroup(PropertyCategoryName, FText::FromName(PropertyCategoryName), true);
					// UE_LOG(LogTemp, Log, TEXT("Category 0: %s"), *StructName.ToString());
					// GroupToUse = CreatedCategories.Add(PropertyCategoryName, &NewGroup);
					GroupToUse = CreatedCategories.FindChecked(StructName);
				}
				else
				{
					// IDetailGroup& NewGroup = ChildBuilder.AddGroup(PropertyCategoryName, FText::FromName(PropertyCategoryName));
					// NewGroup.ToggleExpansion(true);
					// GroupToUse = CreatedCategories.Add(PropertyCategoryName, &NewGroup);
					IDetailGroup& NewGroup = ChildBuilder.AddGroup(StructName, StructHandle->GetPropertyDisplayName());
					NewGroup.ToggleExpansion(true);
					GroupToUse = CreatedCategories.Add(PropertyCategoryName, &NewGroup);
				}
			}
		}
		
		IDetailPropertyRow& PropertyRow = GroupToUse->AddPropertyRow(ChildHandle);

		if (OuterJob)
		{
			CustomizeStructChildrenInMovieRenderQueue(PropertyRow, OuterJob);
		}
		else
		{
			CustomizeStructChildrenInAssetDetails(PropertyRow);
		}
	}

	// Force expansion of all categories
	for (const TTuple<FName, IDetailGroup*>& Pair : CreatedCategories)
	{
		if (Pair.Value)
		{
			Pair.Value->ToggleExpansion(true);
		}
	}
}

void FDeadlineCloudJobPresetDetailsCustomization::CustomizeStructChildrenInAssetDetails(
	IDetailPropertyRow& PropertyRow) const
{
	TSharedPtr<SWidget> NameWidget;
	TSharedPtr<SWidget> ValueWidget;
	FDetailWidgetRow Row;
	PropertyRow.GetDefaultWidgets(NameWidget, ValueWidget, Row);

	PropertyRow.CustomWidget(true)
	.NameContent()
	.MinDesiredWidth(Row.NameWidget.MinWidth)
	.MaxDesiredWidth(Row.NameWidget.MaxWidth)
	.HAlign(HAlign_Fill)
	[
		NameWidget.ToSharedRef()
	]
	.ValueContent()
	.MinDesiredWidth(Row.ValueWidget.MinWidth)
	.MaxDesiredWidth(Row.ValueWidget.MaxWidth)
	.VAlign(VAlign_Center)
	[
		ValueWidget.ToSharedRef()
	]
	.ExtensionContent()
	[
		SNew(SEyeCheckBox, *PropertyRow.GetPropertyHandle()->GetProperty()->GetPathName())
	];
}

void FDeadlineCloudJobPresetDetailsCustomization::CustomizeStructChildrenInMovieRenderQueue(
	IDetailPropertyRow& PropertyRow, UMoviePipelineDeadlineCloudExecutorJob* Job) const
{
	PropertyOverrideHandler->EnableInMovieRenderQueue(PropertyRow);
}

TSharedRef<IPropertyTypeCustomization> FDeadlineCloudAttachmentDetailsCustomization::MakeInstance()
{
	return MakeShared<FDeadlineCloudAttachmentDetailsCustomization>();
}

void FDeadlineCloudAttachmentDetailsCustomization::CustomizeHeader(
	TSharedRef<IPropertyHandle> PropertyHandle, FDetailWidgetRow& HeaderRow,
    IPropertyTypeCustomizationUtils& CustomizationUtils)
{
	const auto NameWidget = PropertyHandle->CreatePropertyNameWidget();
	const auto ValueWidget = PropertyHandle->CreatePropertyValueWidget();
	
	HeaderRow
	.NameContent()
	[
		NameWidget
	]
	.ValueContent()
	[
		ValueWidget
	];
}

void FDeadlineCloudAttachmentDetailsCustomization::CustomizeChildren(
	TSharedRef<IPropertyHandle> StructHandle, IDetailChildrenBuilder& ChildBuilder,
	IPropertyTypeCustomizationUtils& CustomizationUtils)
{
	auto ShowAutoDetectedHandle = StructHandle->GetChildHandle(0);
	const auto PathsHandle = StructHandle->GetChildHandle(1);
	const auto AutoDetectedPathsHandle = StructHandle->GetChildHandle(2);

	// Show autodetect
	auto& ShowAutoDetectedRow = ChildBuilder.AddProperty(ShowAutoDetectedHandle.ToSharedRef());
	auto& PathsRow = ChildBuilder.AddProperty(PathsHandle.ToSharedRef());
	auto& AutoDetectedPathsRow = ChildBuilder.AddProperty(AutoDetectedPathsHandle.ToSharedRef());

	UMoviePipelineDeadlineCloudExecutorJob* OuterJob = FPropertyAvailabilityHandler::GetOuterJob(StructHandle);
	PropertyOverrideHandler = MakeShared<FPropertyAvailabilityHandler>(OuterJob);

	// Slava Auto-detected are not enabled for overrides
	// PropertyOverrideHandler->EnableOverridesInMovieRenderQueue(ShowAutoDetectedRow);

	// Slava Auto-detected are not enabled for overrides
	// PropertyOverrideHandler->EnableOverridesInMovieRenderQueue(AutoDetectedPathsRow);

	if (OuterJob)
	{
		PropertyOverrideHandler->EnableInMovieRenderQueue(PathsRow);
		AutoDetectedPathsRow
		.Visibility(
			TAttribute<EVisibility>::Create([ShowAutoDetectedHandle]
			{
				bool bVisible = false;
				ShowAutoDetectedHandle->GetValue(bVisible);
				return bVisible
					? EVisibility::Visible
					: EVisibility::Hidden;
			}));
	}
	else
		PropertyOverrideHandler->DisableRowInDataAsset(AutoDetectedPathsRow);

	// TODO Slava: bad place for updating auto-detected files
	// But since we do it mostly to show them in the UI. We don't want to put it into job initialization methods
	if (OuterJob && StructHandle->GetProperty()->GetName() == "InputFiles")
	{
		OuterJob->UpdateAttachmentFields();
	}
}

bool FDeadlineCloudJobPresetDetailsCustomization::IsPropertyHiddenInMovieRenderQueue(const FName& InPropertyPath)
{
	return false;
}

bool GetPresetValueAsString(const FProperty* PropertyPtr, UMoviePipelineDeadlineCloudExecutorJob* Job, FString& OutFormattedValue)
{
	if (!PropertyPtr || !Job)
	{
		return false;
	}

	UDeadlineCloudJobPreset* SelectedJobPreset = Job->JobPreset;
	if (!SelectedJobPreset)
	{
		return false;
	}

	const void* ValuePtr = PropertyPtr->ContainerPtrToValuePtr<void>(&SelectedJobPreset->JobPresetStruct);
	PropertyPtr->ExportText_Direct(OutFormattedValue, ValuePtr, ValuePtr, nullptr, PPF_None);
	return true;
}

TSharedRef<FDeadlineCloudAttachmentArrayBuilder> FDeadlineCloudAttachmentArrayBuilder::MakeInstance(
	TSharedRef<IPropertyHandle> InPropertyHandle
	)
{
	TSharedRef<FDeadlineCloudAttachmentArrayBuilder> Builder =
		MakeShared<FDeadlineCloudAttachmentArrayBuilder>(InPropertyHandle);
	
	Builder->OnGenerateArrayElementWidget(
		FOnGenerateArrayElementWidget::CreateSP(Builder, &FDeadlineCloudAttachmentArrayBuilder::OnGenerateEntry));
	return Builder;
}

FDeadlineCloudAttachmentArrayBuilder::FDeadlineCloudAttachmentArrayBuilder(
	TSharedRef<IPropertyHandle> InPropertyHandle
	) : FDetailArrayBuilder(InPropertyHandle, true, false, true),
		ArrayProperty(InPropertyHandle->AsArray())
{
}

void FDeadlineCloudAttachmentArrayBuilder::GenerateHeaderRowContent(FDetailWidgetRow& NodeRow)
{
	// Do nothing since we don't want to show the "InnerArray" row, see FDeadlineCloudAttachmentArrayCustomization::CustomizeHeader
	// Source FOptimusParameterBindingArrayCustomization
}

void FDeadlineCloudAttachmentArrayBuilder::GenerateWrapperStructHeaderRowContent(
	FDetailWidgetRow& NodeRow,
	TSharedRef<SWidget> NameContent)
{
	FDetailArrayBuilder::GenerateHeaderRowContent(NodeRow);
	NodeRow.ValueContent()
	.HAlign( HAlign_Left )
	.VAlign( VAlign_Center )
	// Value grabbed from SPropertyEditorArray::GetDesiredWidth
	.MinDesiredWidth(170.f)
	.MaxDesiredWidth(170.f);

	NodeRow.NameContent()
	[
		NameContent
	];

	NodeRow.IsEnabled(TAttribute<bool>::CreateLambda([this]()
		{
			if (OnIsEnabled.IsBound())
				return OnIsEnabled.Execute();
			return true;
		})
	);
}

void FDeadlineCloudAttachmentArrayBuilder::OnGenerateEntry(
	TSharedRef<IPropertyHandle> ElementProperty,
	int32, IDetailChildrenBuilder& ChildrenBuilder) const
{
	IDetailPropertyRow& PropertyRow = ChildrenBuilder.AddProperty(ElementProperty);
	// PropertyRow.ShowPropertyButtons(true);
	// PropertyRow.ShouldAutoExpand(false);

	// Hide the reset to default button since it provides little value
	const FResetToDefaultOverride ResetDefaultOverride =
		FResetToDefaultOverride::Create(TAttribute<bool>(false));
	
	PropertyRow.OverrideResetToDefault(ResetDefaultOverride);
	
	TSharedPtr<SWidget> NameWidget;
	TSharedPtr<SWidget> ValueWidget;
	PropertyRow.GetDefaultWidgets( NameWidget, ValueWidget);
	PropertyRow.CustomWidget(true)
	.NameContent()
	.HAlign(HAlign_Fill)
	[
		NameWidget.ToSharedRef()
	]
	.ValueContent()
	.HAlign(HAlign_Fill)
	[
		ValueWidget.ToSharedRef()
	];
	ValueWidget.ToSharedRef()->SetEnabled(
		TAttribute<bool>::CreateLambda([this]()
		{
			if (OnIsEnabled.IsBound())
				return OnIsEnabled.Execute();
			return true;
		})
	);
}

void FDeadlineCloudAttachmentArrayCustomization::CustomizeHeader(
	TSharedRef<IPropertyHandle> InPropertyHandle,
	FDetailWidgetRow& InHeaderRow,
	IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
	const TSharedPtr<IPropertyHandle> ArrayHandle = InPropertyHandle->GetChildHandle("Paths", false);

	UMoviePipelineDeadlineCloudExecutorJob* OuterJob = FPropertyAvailabilityHandler::GetOuterJob(InPropertyHandle);
	PropertyOverrideHandler = MakeShared<FPropertyAvailabilityHandler>(OuterJob);

	const FName PropertyPath = *InPropertyHandle->GetProperty()->GetPathName();

	ArrayBuilder = FDeadlineCloudAttachmentArrayBuilder::MakeInstance(ArrayHandle.ToSharedRef());
	if (PropertyOverrideHandler->GetOuterJob(InPropertyHandle))
	{
		ArrayBuilder->OnIsEnabled.BindLambda([this, PropertyPath]()
		{
			return this->PropertyOverrideHandler->IsPropertyRowEnabledInMovieRenderJob(PropertyPath);
		});
	}
	else
	{
		ArrayBuilder->OnIsEnabled.BindLambda([this, PropertyPath]()
		{
			return this->PropertyOverrideHandler->IsPropertyRowEnabledInDataAsset(PropertyPath);
		});
	}
	ArrayBuilder->GenerateWrapperStructHeaderRowContent(InHeaderRow, InPropertyHandle->CreatePropertyNameWidget());
}

void FDeadlineCloudAttachmentArrayCustomization::CustomizeChildren(
	TSharedRef<IPropertyHandle> InPropertyHandle,
    IDetailChildrenBuilder& InChildBuilder,
    IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
	InChildBuilder.AddCustomBuilder(ArrayBuilder.ToSharedRef());
}

FPropertyAvailabilityHandler::FPropertyAvailabilityHandler(UMoviePipelineDeadlineCloudExecutorJob* InJob)
	: Job(InJob)
{
	
}

UMoviePipelineDeadlineCloudExecutorJob* FPropertyAvailabilityHandler::GetOuterJob(TSharedRef<IPropertyHandle> StructHandle)
{
	TArray<UObject*> OuterObjects;
	StructHandle->GetOuterObjects(OuterObjects);

	if (OuterObjects.Num() == 0)
	{
		return nullptr;
	}

	const TWeakObjectPtr<UObject> OuterObject = OuterObjects[0];
	if (!OuterObject.IsValid())
	{
		return nullptr;
	}
	UMoviePipelineDeadlineCloudExecutorJob* OuterJob = Cast<UMoviePipelineDeadlineCloudExecutorJob>(OuterObject);
	return OuterJob;
}

bool FPropertyAvailabilityHandler::IsPropertyRowEnabledInMovieRenderJob(const FName& InPropertyPath)
{
	return Job && Job->IsPropertyRowEnabledInMovieRenderJob(InPropertyPath);
}

bool FPropertyAvailabilityHandler::IsPropertyRowEnabledInDataAsset(const FName& InPropertyPath)
{
	if (PropertiesDisabledInDataAsset.Contains(InPropertyPath))
	{
		return false;
	}
	return true;
}

void FPropertyAvailabilityHandler::DisableRowInDataAsset(const IDetailPropertyRow& PropertyRow)
{
	const FName PropertyPath = *PropertyRow.GetPropertyHandle()->GetProperty()->GetPathName();
	PropertiesDisabledInDataAsset.Add(PropertyPath);
}


void FPropertyAvailabilityHandler::EnableInMovieRenderQueue(IDetailPropertyRow& PropertyRow) const
{
	if (!Job) return;
	
	TSharedPtr<SWidget> NameWidget;
	TSharedPtr<SWidget> ValueWidget;
	FDetailWidgetRow Row;
	PropertyRow.GetDefaultWidgets(NameWidget, ValueWidget, Row);
	
	const FName PropertyPath = *PropertyRow.GetPropertyHandle()->GetProperty()->GetPathName();
	ValueWidget->SetEnabled(
		TAttribute<bool>::CreateLambda([this, PropertyPath]()
			{
				return Job->IsPropertyRowEnabledInMovieRenderJob(PropertyPath); 
			}
		)
	);
	
	PropertyRow
	// .OverrideResetToDefault(
	// 	FResetToDefaultOverride::Create(
	// 		FIsResetToDefaultVisible::CreateStatic( &FDeadlineCloudJobPresetDetailsCustomization::IsResetToDefaultVisibleOverride, Job),
	// 		FResetToDefaultHandler::CreateStatic(&FDeadlineCloudJobPresetDetailsCustomization::ResetToDefaultOverride, Job)))
	.CustomWidget(true)
	.NameContent()
	.MinDesiredWidth(Row.NameWidget.MinWidth)
	.MaxDesiredWidth(Row.NameWidget.MaxWidth)
	.HAlign(HAlign_Fill)
	[
		SNew(SHorizontalBox)
		+ SHorizontalBox::Slot()
		.AutoWidth()
		.Padding(4, 0)
		[
			SNew(SCheckBox)
			.IsChecked_Lambda([this, PropertyPath]()
			{
				return Job->IsPropertyRowEnabledInMovieRenderJob(PropertyPath) ?
					ECheckBoxState::Checked : ECheckBoxState::Unchecked; 
			})
			.OnCheckStateChanged_Lambda([this, PropertyPath](const ECheckBoxState NewState)
			{
				return Job->SetPropertyRowEnabledInMovieRenderJob(
					PropertyPath, NewState == ECheckBoxState::Checked
				); 
			})
		]
		+ SHorizontalBox::Slot()
		[
			NameWidget.ToSharedRef()
		]
	]
	.ValueContent()
	.MinDesiredWidth(Row.ValueWidget.MinWidth)
	.MaxDesiredWidth(Row.ValueWidget.MaxWidth)
	.VAlign(VAlign_Center)
	[
		ValueWidget.ToSharedRef()
	];
}
