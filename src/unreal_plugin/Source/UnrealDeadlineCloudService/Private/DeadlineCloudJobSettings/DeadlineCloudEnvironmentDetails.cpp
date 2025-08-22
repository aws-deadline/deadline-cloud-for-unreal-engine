// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "DeadlineCloudJobSettings/DeadlineCloudEnvironmentDetails.h"
#include "DeadlineCloudJobSettings/DeadlineCloudEnvironment.h"
#include "MovieRenderPipeline/MoviePipelineDeadlineCloudExecutorJob.h"
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
#include "Widgets/Input/SCheckBox.h"

#include "Framework/MetaData/DriverMetaData.h"
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

	TSharedRef<IPropertyHandle> PathToTemplate = MainDetailLayout->GetProperty("PathToTemplate");
	IDetailPropertyRow* PathToTemplateRow = MainDetailLayout->EditDefaultProperty(PathToTemplate);

	if (PathToTemplateRow)
	{
		TSharedPtr<SWidget> NameWidget;
		TSharedPtr<SWidget> ValueWidget;
		PathToTemplateRow->GetDefaultWidgets(NameWidget, ValueWidget);

		FName Tag = FName("Environment.PathToTemplate");
		ValueWidget->AddMetadata(FDriverMetaData::Id(Tag));

		PathToTemplateRow->CustomWidget()
			.NameContent()
			[
				NameWidget.ToSharedRef()
			]
			.ValueContent()
			[
				ValueWidget.ToSharedRef()
			];	
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
	Builder->MrqJob = FDeadlineCloudDetailsWidgetsHelper::GetMrqJob(InPropertyHandle);
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

		TSharedPtr<SWidget> CustomValueWidget = FDeadlineCloudDetailsWidgetsHelper::CreatePropertyWidgetByType(ItemHandle, EValueType::STRING, EValueValidationType::EnvParameterValue);
		TSharedPtr<IPropertyHandle> KeyHandle = ItemHandle->GetKeyHandle();
		FString Name;
		KeyHandle->GetValue(Name);
		FName Tag = FName("EnvironmentParameter." + Name);
		CustomValueWidget->AddMetadata(FDriverMetaData::Id(Tag));

		const FString PropertyPathString = ItemHandle->GeneratePathToProperty();
		const FName PropertyPath(*PropertyPathString);

		FDetailWidgetRow& ItemRow = InChildrenBuilder.AddCustomRow(FText::FromString(Name));
		
		ItemRow.NameContent()
			[
				SNew(SHorizontalBox)
					+ SHorizontalBox::Slot()
					.AutoWidth()
					.Padding(4, 0)
					[
						MrqJob
							? SNew(SCheckBox)
							.IsChecked_Lambda([this, PropertyPath]()
								{
									if (MrqJob)
									{
										return MrqJob->IsPropertyRowEnabledInMovieRenderJob(PropertyPath)
											? ECheckBoxState::Checked
											: ECheckBoxState::Unchecked;
									}
									return ECheckBoxState::Unchecked;
								})
							.OnCheckStateChanged_Lambda([this, PropertyPath](ECheckBoxState NewState)
								{
									if (MrqJob)
									{
										const bool bEnabled = (NewState == ECheckBoxState::Checked);
										UE_LOG(LogTemp, Warning, TEXT("Setting PropertyPath = %s, Enabled = %d"), *PropertyPath.ToString(), bEnabled);
										MrqJob->SetPropertyRowEnabledInMovieRenderJob(PropertyPath, bEnabled);
									}
								})
							: SNullWidget::NullWidget
					]
					+ SHorizontalBox::Slot()
					.AutoWidth()
					.Padding(2.0f, 0.0f)
					.HAlign(HAlign_Left)
					.VAlign(VAlign_Center)
					[
						SNew(STextBlock)
						.Text(FText::FromString(Name))
					]
			];

		ItemRow.ValueContent()
			[
				CustomValueWidget.ToSharedRef()
			];

		CustomValueWidget->SetEnabled(
			TAttribute<bool>::CreateLambda([this, PropertyPath]()
				{
					if (MrqJob)
					{
						return MrqJob->IsPropertyRowEnabledInMovieRenderJob(PropertyPath);
					}
					return true;
				})
		);
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
	ArrayBuilder->MrqJob = FDeadlineCloudDetailsWidgetsHelper::GetMrqJob(InPropertyHandle);
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