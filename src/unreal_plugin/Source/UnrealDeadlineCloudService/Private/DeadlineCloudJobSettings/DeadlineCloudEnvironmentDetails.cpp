// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "DeadlineCloudJobSettings/DeadlineCloudEnvironmentDetails.h"
#include "DeadlineCloudJobSettings/DeadlineCloudEnvironment.h"
#include "PropertyEditorModule.h"
#include "Modules/ModuleManager.h"
#include "DetailLayoutBuilder.h"
#include "DetailWidgetRow.h"
#include "DesktopPlatformModule.h"
#include "UnrealDeadlineCloudServiceModule.h"
#include "CoreMinimal.h"

#include "Templates/SharedPointer.h"
#include "IDetailsView.h"
#include "IDetailChildrenBuilder.h"
#include "IDetailPropertyRow.h"
#include "DeadlineCloudJobSettings/DeadlineCloudDetailsWidgetsHelper.h"
#include "PythonAPILibraries/PythonParametersConsistencyChecker.h"
#include "EditorDirectories.h"
#include "Widgets/Input/SFilePathPicker.h"
#include "Widgets/Input/SEditableTextBox.h"

#define LOCTEXT_NAMESPACE "EnvironmentDetails"

bool FDeadlineCloudEnvironmentDetails::CheckConsistency(UDeadlineCloudEnvironment* Env)
{
    FParametersConsistencyCheckResult result;
    if (Env != nullptr)
    {
        result = Env->CheckEnvironmentVariablesConsistency(Env);

        UE_LOG(LogTemp, Warning, TEXT("Check consistency result: %s"), *result.Reason);
        return result.Passed;
	}
	else
	{
		UE_LOG(LogTemp, Error, TEXT("Deadline Environment is nullptr"));
		return false;
	}
}
/*Details*/
TSharedRef<IDetailCustomization> FDeadlineCloudEnvironmentDetails::MakeInstance()
{
	return MakeShareable(new FDeadlineCloudEnvironmentDetails);
}

void FDeadlineCloudEnvironmentDetails::CustomizeDetails(IDetailLayoutBuilder& DetailBuilder)
{
	// The detail layout builder that is using us
	MainDetailLayout = &DetailBuilder;

	TArray<TWeakObjectPtr<UObject>> ObjectsBeingCustomized;
	MainDetailLayout->GetObjectsBeingCustomized(ObjectsBeingCustomized);
	Settings = Cast<UDeadlineCloudEnvironment>(ObjectsBeingCustomized[0].Get());

	TSharedPtr<FDeadlineCloudDetailsWidgetsHelper::SConsistencyWidget> ConsistencyUpdateWidget;
	FParametersConsistencyCheckResult result;

	/* Consistency check */
	if (Settings.IsValid() && Settings->Variables.Variables.Num() > 0)
	{
		UDeadlineCloudEnvironment* MyObject = Settings.Get();
		bCheckConsistensyPassed = CheckConsistency(MyObject);
	}

	IDetailCategoryBuilder& PropertiesCategory = MainDetailLayout->EditCategory("Parameters");

	PropertiesCategory.AddCustomRow(FText::FromString("Consistency"))
		.Visibility(TAttribute<EVisibility>::Create(TAttribute<EVisibility>::FGetter::CreateSP(this, &FDeadlineCloudEnvironmentDetails::GetWidgetVisibility)))
		.WholeRowContent()
		[
			SAssignNew(ConsistencyUpdateWidget, FDeadlineCloudDetailsWidgetsHelper::SConsistencyWidget)
				.OnFixButtonClicked(FSimpleDelegate::CreateSP(this, &FDeadlineCloudEnvironmentDetails::OnConsistencyButtonClicked))
		];

	//  Dispatcher handle bind
	if (Settings.IsValid() && (MainDetailLayout != nullptr))
	{
		Settings->OnPathChanged = FSimpleDelegate::CreateSP(this, &FDeadlineCloudEnvironmentDetails::ForceRefreshDetails);
	};
}

void FDeadlineCloudEnvironmentDetails::OnConsistencyButtonClicked()
{
	{
		Settings->FixEnvironmentVariablesConsistency(Settings.Get());
		UE_LOG(LogTemp, Warning, TEXT("FixStepParametersConsistency"));
		ForceRefreshDetails();
	}
}


void FDeadlineCloudEnvironmentDetails::ForceRefreshDetails()
{
	MainDetailLayout->ForceRefreshDetails();
}

TSharedRef<FDeadlineCloudEnvironmentParametersMapBuilder> FDeadlineCloudEnvironmentParametersMapBuilder::MakeInstance(TSharedRef<IPropertyHandle> InPropertyHandle)
{
	TSharedRef<FDeadlineCloudEnvironmentParametersMapBuilder> Builder =
		MakeShared<FDeadlineCloudEnvironmentParametersMapBuilder>(InPropertyHandle);

	return Builder;
}

FDeadlineCloudEnvironmentParametersMapBuilder::FDeadlineCloudEnvironmentParametersMapBuilder(TSharedRef<IPropertyHandle> InPropertyHandle)
	: MapProperty(InPropertyHandle->AsMap()),
	BaseProperty(InPropertyHandle)
{
	check(MapProperty.IsValid());
}

FName FDeadlineCloudEnvironmentParametersMapBuilder::GetName() const
{
	return BaseProperty->GetProperty()->GetFName();
}

void FDeadlineCloudEnvironmentParametersMapBuilder::GenerateChildContent(IDetailChildrenBuilder& InChildrenBuilder)
{
	uint32 NumChildren = 0;
	BaseProperty->GetNumChildren(NumChildren);

	EmptyCopyPasteAction = FUIAction(
		FExecuteAction::CreateLambda([]() {}),
		FCanExecuteAction::CreateLambda([]() { return false; })
	);

	for (uint32 ChildIndex = 0; ChildIndex < NumChildren; ++ChildIndex)
	{
		TSharedPtr<IPropertyHandle> ItemHandle = BaseProperty->GetChildHandle(ChildIndex);
		if (!ItemHandle.IsValid())
		{
			continue;
		}

		IDetailPropertyRow& ItemRow = InChildrenBuilder.AddProperty(ItemHandle.ToSharedRef());
		ItemRow.ShowPropertyButtons(false);
		ItemRow.OverrideResetToDefault(FResetToDefaultOverride::Create(TAttribute<bool>(false)));

		TSharedPtr<SWidget> NameWidget;
		TSharedPtr<SWidget> ValueWidget;

		ItemRow.GetDefaultWidgets(NameWidget, ValueWidget);
		ItemRow.CustomWidget(true)
			.CopyAction(EmptyCopyPasteAction)
			.PasteAction(EmptyCopyPasteAction)
			.WholeRowContent()
			[
				SNew(SHorizontalBox)
					+ SHorizontalBox::Slot()
					.AutoWidth()
					.Padding(2.0f, 0.0f)
					.HAlign(HAlign_Left)
					.VAlign(VAlign_Center)
					[
						NameWidget.ToSharedRef()
					]
					+ SHorizontalBox::Slot()
					.FillWidth(1.0f)
					.Padding(2.0f, 0.0f)
					[
						ValueWidget.ToSharedRef()
					]
			];

		NameWidget->SetEnabled(false);
	}
}

TSharedPtr<IPropertyHandle> FDeadlineCloudEnvironmentParametersMapBuilder::GetPropertyHandle() const
{
	return BaseProperty;
}

void FDeadlineCloudEnvironmentParametersMapBuilder::SetOnRebuildChildren(FSimpleDelegate InOnRebuildChildren)
{
	OnRebuildChildren = InOnRebuildChildren;
}

bool FDeadlineCloudEnvironmentParametersMapCustomization::IsResetToDefaultVisible(TSharedPtr<IPropertyHandle> PropertyHandle) const
{
	if (!PropertyHandle.IsValid())
	{
		return false;
	}

	auto OuterEnvironment = GetOuterEnvironment(PropertyHandle.ToSharedRef());

	if (!IsValid(OuterEnvironment))
	{
		return false;
	}

	return !OuterEnvironment->IsDefaultVariables();
}

void FDeadlineCloudEnvironmentParametersMapCustomization::ResetToDefaultHandler(TSharedPtr<IPropertyHandle> PropertyHandle) const
{
	if (!PropertyHandle.IsValid())
	{
		return;
	}

	auto OuterEnvironment = GetOuterEnvironment(PropertyHandle.ToSharedRef());

	if (!IsValid(OuterEnvironment))
	{
		return;
	}

	OuterEnvironment->ResetVariables();
}

void FDeadlineCloudEnvironmentParametersMapCustomization::CustomizeHeader(TSharedRef<IPropertyHandle> InPropertyHandle, FDetailWidgetRow& InHeaderRow, IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
	TSharedPtr<IPropertyHandle> ArrayHandle = InPropertyHandle->GetChildHandle("Variables", false);

	EmptyCopyPasteAction = FUIAction(
		FExecuteAction::CreateLambda([]() {}),
		FCanExecuteAction::CreateLambda([]() { return false; })
	);

	auto OuterEnvironment = GetOuterEnvironment(InPropertyHandle);
	if (IsValid(OuterEnvironment))
	{
		const FResetToDefaultOverride ResetDefaultOverride = FResetToDefaultOverride::Create(
			FIsResetToDefaultVisible::CreateSP(this, &FDeadlineCloudEnvironmentParametersMapCustomization::IsResetToDefaultVisible),
			FResetToDefaultHandler::CreateSP(this, &FDeadlineCloudEnvironmentParametersMapCustomization::ResetToDefaultHandler)
		);
		InHeaderRow.OverrideResetToDefault(ResetDefaultOverride);
	}
	else
	{
		// Hide the reset to default button since it provides little value
		const FResetToDefaultOverride ResetDefaultOverride = FResetToDefaultOverride::Create(TAttribute<bool>(false));
		InHeaderRow.OverrideResetToDefault(ResetDefaultOverride);
	}

	InHeaderRow.ValueContent()
		.HAlign(HAlign_Left)
		.VAlign(VAlign_Center)
		.MinDesiredWidth(170.f)
		.MaxDesiredWidth(170.f);

	InHeaderRow.NameContent()
		[
			ArrayHandle->CreatePropertyNameWidget()
		];

	InHeaderRow.CopyAction(EmptyCopyPasteAction);
	InHeaderRow.PasteAction(EmptyCopyPasteAction);

	ArrayBuilder = FDeadlineCloudEnvironmentParametersMapBuilder::MakeInstance(ArrayHandle.ToSharedRef());
}

void FDeadlineCloudEnvironmentParametersMapCustomization::CustomizeChildren(TSharedRef<IPropertyHandle> InPropertyHandle, IDetailChildrenBuilder& InChildBuilder, IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
	InChildBuilder.AddCustomBuilder(ArrayBuilder.ToSharedRef());
}

UDeadlineCloudEnvironment* FDeadlineCloudEnvironmentParametersMapCustomization::GetOuterEnvironment(TSharedRef<IPropertyHandle> Handle)
{
	TArray<UObject*> OuterObjects;
	Handle->GetOuterObjects(OuterObjects);

	if (OuterObjects.Num() == 0)
	{
		return nullptr;
	}

	const TWeakObjectPtr<UObject> OuterObject = OuterObjects[0];
	if (!OuterObject.IsValid())
	{
		return nullptr;
	}
	UDeadlineCloudEnvironment* OuterJob = Cast<UDeadlineCloudEnvironment>(OuterObject);
	return OuterJob;
}

#undef LOCTEXT_NAMESPACE