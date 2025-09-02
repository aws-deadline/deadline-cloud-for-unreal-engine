// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "DeadlineCloudJobSettings/DeadlineCloudStepDetails.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJobDetails.h"
#include "DeadlineCloudJobSettings/DeadlineCloudStep.h"
#include "PropertyEditorModule.h"
#include "Modules/ModuleManager.h"
#include "DetailLayoutBuilder.h"
#include "DetailWidgetRow.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/SBoxPanel.h"
#include "DesktopPlatformModule.h"
#include "Widgets/Input/SFilePathPicker.h"
#include "IDetailChildrenBuilder.h"
#include "Widgets/Input/SNumericEntryBox.h"
#include "PythonAPILibraries/PythonParametersConsistencyChecker.h"
#include "DeadlineCloudJobSettings/DeadlineCloudDetailsWidgetsHelper.h"
#include "MovieRenderPipeline/MoviePipelineDeadlineCloudExecutorJob.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJobPresetDetailsCustomization.h"

#include "MovieRenderPipeline/MoviePipelineDeadlineCloudExecutorJob.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJobPresetDetailsCustomization.h"
#include "PropertyCustomizationHelpers.h"

#include "Framework/MetaData/DriverMetaData.h"
#include "Widgets/SNullWidget.h"
#define LOCTEXT_NAMESPACE "StepDetails"



bool FDeadlineCloudStepDetails::CheckConsistency(UDeadlineCloudStep* Step)
{
    FParametersConsistencyCheckResult result;
    result = Step->CheckStepParametersConsistency(Step);

    UE_LOG(LogTemp, Warning, TEXT("Check consistency result: %s"), *result.Reason);
    return result.Passed;
}

void FDeadlineCloudStepDetails::OnResetHiddenParametersClicked()
{
    Settings->ResetParametersHiddenToDefault();
    ForceRefreshDetails();
}

void FDeadlineCloudStepDetails::OnConsistencyButtonClicked()
{
    Settings->FixStepParametersConsistency(Settings.Get());
    UE_LOG(LogTemp, Warning, TEXT("FixStepParametersConsistency"));
    ForceRefreshDetails();
}

void FDeadlineCloudStepDetails::RespondToEvent()
{
    ForceRefreshDetails();
}

void FDeadlineCloudStepDetails::ForceRefreshDetails()
{
    MainDetailLayout->ForceRefreshDetails();
}

/*Details*/
TSharedRef<IDetailCustomization> FDeadlineCloudStepDetails::MakeInstance()
{
    return MakeShareable(new FDeadlineCloudStepDetails);
}

void FDeadlineCloudStepDetails::CustomizeDetails(IDetailLayoutBuilder& DetailBuilder)
{
    MainDetailLayout = &DetailBuilder;
    TArray<TWeakObjectPtr<UObject>> ObjectsBeingCustomized;
    DetailBuilder.GetObjectsBeingCustomized(ObjectsBeingCustomized);
	Settings = Cast<UDeadlineCloudStep>(ObjectsBeingCustomized[0].Get());

	TSharedRef<IPropertyHandle> PathToTemplate = MainDetailLayout->GetProperty("PathToTemplate");
	IDetailPropertyRow* PathToTemplateRow = MainDetailLayout->EditDefaultProperty(PathToTemplate);

	if (PathToTemplateRow)
	{
		TSharedPtr<SWidget> NameWidget;
		TSharedPtr<SWidget> ValueWidget;
		PathToTemplateRow->GetDefaultWidgets(NameWidget, ValueWidget);

		FName Tag = FName("Step.PathToTemplate");
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

	TSharedRef<IPropertyHandle> EnvironmentsHandle = MainDetailLayout->GetProperty("Environments");
	IDetailPropertyRow* EnvironmentsRow = MainDetailLayout->EditDefaultProperty(EnvironmentsHandle);
	TSharedPtr<SWidget> OutNameWidgetEnv;
	TSharedPtr<SWidget> OutValueWidgetEnv;
	EnvironmentsRow->GetDefaultWidgets(OutNameWidgetEnv, OutValueWidgetEnv);
	EnvironmentsRow->ShowPropertyButtons(true);

	EnvironmentsRow->CustomWidget(true)
		.NameContent()
		[
			OutNameWidgetEnv.ToSharedRef()
		]
		.ValueContent()
		[
			SNew(SHorizontalBox)
				+ SHorizontalBox::Slot()
				.HAlign(HAlign_Left)
				.VAlign(VAlign_Center)
				[
					SNew(STextBlock)
						.Text(LOCTEXT("EnvironmentsError", "Contains empty or duplicate items"))
						.Font(IDetailLayoutBuilder::GetDetailFont())
						.ColorAndOpacity(FLinearColor::Red)
						.Visibility(TAttribute<EVisibility>::Create(TAttribute<EVisibility>::FGetter::CreateSP(this, &FDeadlineCloudStepDetails::GetEnvironmentErrorWidgetVisibility)))
				]
				+ SHorizontalBox::Slot()
				.HAlign(HAlign_Left)
				.VAlign(VAlign_Center)
				[
					SNew(SOverlay)
						.Visibility(TAttribute<EVisibility>::Create(TAttribute<EVisibility>::FGetter::CreateSP(this, &FDeadlineCloudStepDetails::GetEnvironmentDefaultWidgetVisibility)))
						+ SOverlay::Slot()
						[
							OutValueWidgetEnv.ToSharedRef()
						]
				]
		];

	TSharedPtr<FDeadlineCloudDetailsWidgetsHelper::SConsistencyWidget> ConsistencyUpdateWidget;
	FParametersConsistencyCheckResult result;

	TSharedPtr<FDeadlineCloudDetailsWidgetsHelper::SEyeUpdateWidget> HiddenParametersUpdateWidget;

	/* Update all when one Parameters widget is checked as hidden */
	if (Settings.IsValid())
	{
		Settings->OnParameterHidden.BindSP(this, &FDeadlineCloudStepDetails::RespondToEvent);
	}
	/* Collapse hidden parameters array  */
	TSharedRef<IPropertyHandle> HideHandle = MainDetailLayout->GetProperty("HiddenParametersList");
	IDetailPropertyRow* HideRow = MainDetailLayout->EditDefaultProperty(HideHandle);
	HideRow->Visibility(EVisibility::Collapsed);

	/* Consistency check */
	if (Settings.IsValid() && Settings->GetStepParameters().Num() > 0)
	{
		UDeadlineCloudStep* MyObject = Settings.Get();
		bCheckConsistensyPassed = CheckConsistency(MyObject);
	}

	IDetailCategoryBuilder& PropertiesCategory = MainDetailLayout->EditCategory("Parameters");

	PropertiesCategory.AddCustomRow(FText::FromString("Consistency"))
		.Visibility(TAttribute<EVisibility>::Create(TAttribute<EVisibility>::FGetter::CreateSP(this, &FDeadlineCloudStepDetails::GetWidgetVisibility)))
		.WholeRowContent()
		[
			SAssignNew(ConsistencyUpdateWidget, FDeadlineCloudDetailsWidgetsHelper::SConsistencyWidget)
				.OnFixButtonClicked(FSimpleDelegate::CreateSP(this, &FDeadlineCloudStepDetails::OnConsistencyButtonClicked))
		];

	if (Settings.IsValid() && (MainDetailLayout != nullptr))
	{
		Settings->OnPathChanged = FSimpleDelegate::CreateSP(this, &FDeadlineCloudStepDetails::ForceRefreshDetails);
	};

	PropertiesCategory.AddCustomRow(FText::FromString("Visibility"))
		.Visibility(TAttribute<EVisibility>::Create(TAttribute<EVisibility>::FGetter::CreateSP(this, &FDeadlineCloudStepDetails::GetEyeWidgetVisibility)))
		.WholeRowContent()
		[
			SAssignNew(HiddenParametersUpdateWidget, FDeadlineCloudDetailsWidgetsHelper::SEyeUpdateWidget)

				.OnEyeUpdateButtonClicked(FSimpleDelegate::CreateSP(this, &FDeadlineCloudStepDetails::OnResetHiddenParametersClicked))
		];
}

bool FDeadlineCloudStepDetails::IsEnvironmentContainsErrors() const
{
	TArray<UObject*> ExistingEnvironment;
	for (auto Environment : Settings->Environments)
	{
		if (!IsValid(Environment) || ExistingEnvironment.Contains(Environment))
		{
			return true;
		}

		ExistingEnvironment.Add(Environment);
	}

	return false;
}

EVisibility FDeadlineCloudStepDetails::GetEyeWidgetVisibility() const
{
	return ((Settings->IsParametersHiddenByDefault())) ? EVisibility::Collapsed : EVisibility::Visible;
}

EVisibility FDeadlineCloudStepDetails::GetEnvironmentErrorWidgetVisibility() const
{
	return IsEnvironmentContainsErrors() ? EVisibility::Visible : EVisibility::Collapsed;
}

EVisibility FDeadlineCloudStepDetails::GetEnvironmentDefaultWidgetVisibility() const
{
	return IsEnvironmentContainsErrors() ? EVisibility::Collapsed : EVisibility::Visible;
}

bool FDeadlineCloudStepParametersArrayCustomization::IsEnabled(TSharedRef<IPropertyHandle> InPropertyHandle) const
{
	UMoviePipelineDeadlineCloudExecutorJob* OuterJob = FDeadlineCloudDetailsWidgetsHelper::GetMrqJob(InPropertyHandle);
	if (!OuterJob)
	{
		return false; 
	}

	//Only if StepsOverride in MrqJob
	if (OuterJob->JobPreset)
	{
		return (OuterJob->GetStepsToOverride(OuterJob->JobPreset).Num()>0);		
	}

	else return false;
}

void FDeadlineCloudStepParametersArrayCustomization::CustomizeHeader(TSharedRef<IPropertyHandle> InPropertyHandle, FDetailWidgetRow& InHeaderRow, IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
	const TSharedPtr<IPropertyHandle> ArrayHandle = InPropertyHandle->GetChildHandle("Parameters", false);

	ArrayBuilder = FDeadlineCloudStepParametersArrayBuilder::MakeInstance(ArrayHandle.ToSharedRef());

	auto OuterJob = FDeadlineCloudDetailsWidgetsHelper::GetMrqJob(InPropertyHandle);
	if (IsValid(OuterJob))
	{
		ArrayBuilder->OnIsEnabled.BindSP(this, &FDeadlineCloudStepParametersArrayCustomization::IsEnabled, InPropertyHandle);
	}

	//Get StepsOverride handle from TaskParametersDefinition handle and get name of RenderStep
	TSharedPtr<IPropertyHandle> ParentHandle = InPropertyHandle->GetParentHandle();
	TSharedPtr<IPropertyHandle> NameHandle = ParentHandle->GetChildHandle("Name");

	FString StepNameValue;
	NameHandle->GetValue(StepNameValue);

	ArrayBuilder->StepName = FName(StepNameValue);
	
	// Check if this is an MRQ job and if we're customizing the TaskParameterDefinitions property
	if (IsValid(OuterJob) && InPropertyHandle->GetProperty() && 
		InPropertyHandle->GetProperty()->GetName() == TEXT("TaskParameterDefinitions"))
	{
		// For MRQ jobs, show empty header without the "TaskParameterDefinitions" label
	}
	else
	{
		// For non-MRQ jobs show the normal header
		ArrayBuilder->GenerateWrapperStructHeaderRowContent(InHeaderRow, InPropertyHandle->CreatePropertyNameWidget());
	}
}

void FDeadlineCloudStepParametersArrayCustomization::CustomizeChildren(TSharedRef<IPropertyHandle> InPropertyHandle, IDetailChildrenBuilder& InChildBuilder, IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
	ArrayBuilder->MrqJob = FDeadlineCloudDetailsWidgetsHelper::GetMrqJob(InPropertyHandle);
	ArrayBuilder->Step = ArrayBuilder->GetOuterStep(InPropertyHandle);
	InChildBuilder.AddCustomBuilder(ArrayBuilder.ToSharedRef());
}


UDeadlineCloudStep* FDeadlineCloudStepParametersArrayBuilder::GetOuterStep(TSharedRef<IPropertyHandle> Handle)
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
	UDeadlineCloudStep* OuterStep = Cast<UDeadlineCloudStep>(OuterObject);
	if (OuterStep)
	{
		return OuterStep;
	}
	
	else return nullptr;
}

TSharedRef<FDeadlineCloudStepParametersArrayBuilder> FDeadlineCloudStepParametersArrayBuilder::MakeInstance(TSharedRef<IPropertyHandle> InPropertyHandle)
{
	TSharedRef<FDeadlineCloudStepParametersArrayBuilder> Builder =
		MakeShared<FDeadlineCloudStepParametersArrayBuilder>(InPropertyHandle);

	Builder->OnGenerateArrayElementWidget(
		FOnGenerateArrayElementWidget::CreateSP(Builder, &FDeadlineCloudStepParametersArrayBuilder::OnGenerateEntry));
	return Builder;
}

FDeadlineCloudStepParametersArrayBuilder::FDeadlineCloudStepParametersArrayBuilder(TSharedRef<IPropertyHandle> InPropertyHandle)
	: FDetailArrayBuilder(InPropertyHandle, false, false, true),
	ArrayProperty(InPropertyHandle->AsArray()),
	OriginalPropertyHandle(InPropertyHandle)
{
	EmptyCopyPasteAction = FUIAction(
		FExecuteAction::CreateLambda([]() {}),
		FCanExecuteAction::CreateLambda([]() { return false; }));
}

void FDeadlineCloudStepParametersArrayBuilder::GenerateWrapperStructHeaderRowContent(FDetailWidgetRow& NodeRow, TSharedRef<SWidget> NameContent)
{
	FDetailArrayBuilder::GenerateHeaderRowContent(NodeRow);

	NodeRow.CopyAction(EmptyCopyPasteAction);
	NodeRow.PasteAction(EmptyCopyPasteAction);

	NodeRow.OverrideResetToDefault(FResetToDefaultOverride::Create(TAttribute<bool>(false)));

	NodeRow.ValueContent()
		.HAlign(HAlign_Left)
		.VAlign(VAlign_Center)
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

bool FDeadlineCloudStepParametersArrayBuilder::IsResetToDefaultVisible(TSharedPtr<IPropertyHandle> PropertyHandle, FString InParameterName) const
{
	if (!PropertyHandle.IsValid())
	{
		return false;
	}

	auto OuterStep = FDeadlineCloudStepParametersArrayBuilder::GetOuterStep(PropertyHandle.ToSharedRef());
	if (!IsValid(OuterStep))
	{
		return false;
	}
	return !OuterStep->IsParameterArrayDefault(InParameterName);
}

void FDeadlineCloudStepParametersArrayBuilder::ResetToDefaultHandler(TSharedPtr<IPropertyHandle> PropertyHandle, FString InParameterName) const
{
	if (!PropertyHandle.IsValid())
	{
		return;
	}

	auto OuterStep = FDeadlineCloudStepParametersArrayBuilder::GetOuterStep(PropertyHandle.ToSharedRef());
	if (!IsValid(OuterStep))
	{
		return;
	}

	OuterStep->ResetParameterArray(InParameterName);
}

void FDeadlineCloudStepParametersArrayBuilder::OnEyeHideWidgetButtonClicked(FName Property) const
{
	if (Step)
	{
		if (Step->ContainsHiddenParameters(Property))
		{
			Step->RemoveHiddenParameters(Property);
		}
		else
		{
			Step->AddHiddenParameter(Property);
		}
	}
}

bool FDeadlineCloudStepParametersArrayBuilder::IsPropertyHidden(FName Parameter) const
{
	bool Contains = false;

	if (MrqJob)
	{
		for (auto StepOverride : MrqJob->JobPreset->Steps)
		{
			if (StepOverride)
			{
				if (FName(StepOverride->Name) == StepName)
				{
					Contains = StepOverride->ContainsHiddenParameters(Parameter);
				}
			}
		}
	}
	return Contains;
}



void FDeadlineCloudStepParametersArrayBuilder::OnGenerateEntry(TSharedRef<IPropertyHandle> ElementProperty, int32 ElementIndex, IDetailChildrenBuilder& ChildrenBuilder) const
{
	IDetailPropertyRow& PropertyRow = ChildrenBuilder.AddProperty(ElementProperty);
	const TSharedPtr<IPropertyHandle> ThisElement = ElementProperty;
	const TSharedPtr<IPropertyHandle> NameHandle = ElementProperty->GetChildHandle("Name", false);
	if (!NameHandle.IsValid())
	{
		UE_LOG(LogTemp, Error, TEXT("FDeadlineCloudStepParametersArrayBuilder Name handle is not valid"));
		return;
	}

	FString ParameterName;
	NameHandle->GetValue(ParameterName);


	auto OuterStep = FDeadlineCloudStepParametersArrayBuilder::GetOuterStep(ElementProperty);
	if (IsValid(OuterStep))
	{
		const FResetToDefaultOverride ResetDefaultOverride = FResetToDefaultOverride::Create(
			FIsResetToDefaultVisible::CreateSP(this, &FDeadlineCloudStepParametersArrayBuilder::IsResetToDefaultVisible, ParameterName),
			FResetToDefaultHandler::CreateSP(this, &FDeadlineCloudStepParametersArrayBuilder::ResetToDefaultHandler, ParameterName)
		);
		PropertyRow.OverrideResetToDefault(ResetDefaultOverride);
	}
	else
	{
		// Hide the reset to default button since it provides little value
		const FResetToDefaultOverride ResetDefaultOverride = FResetToDefaultOverride::Create(TAttribute<bool>(false));
		PropertyRow.OverrideResetToDefault(ResetDefaultOverride);
	}

	PropertyRow.ShowPropertyButtons(false);

	TSharedPtr<SWidget> NameWidget;
	TSharedPtr<SWidget> ValueWidget;

	PropertyRow.GetDefaultWidgets(NameWidget, ValueWidget);
	bool Checked = !(IsEyeWidgetEnabled(FName(ParameterName)));
	bool isChangedByUser = !IsParameterChangedFromDefault(FName(ParameterName));
	TSharedRef<FDeadlineCloudDetailsWidgetsHelper::SEyeCheckBox> EyeWidget = SNew(FDeadlineCloudDetailsWidgetsHelper::SEyeCheckBox, FName(ParameterName), Checked, isChangedByUser);

	EyeWidget->SetOnCheckStateChangedDelegate(FDeadlineCloudDetailsWidgetsHelper::SEyeCheckBox::FOnCheckStateChangedDelegate::CreateSP(this, &FDeadlineCloudStepParametersArrayBuilder::OnEyeHideWidgetButtonClicked));
	EyeWidget->SetVisibility((MrqJob) ? EVisibility::Hidden : EVisibility::Visible);

	const FString StepParameterPropertyPathString = ElementProperty->GeneratePathToProperty();
	const FName StepParameterPropertyPath(*StepParameterPropertyPathString);

	PropertyRow.CustomWidget(true)
		.CopyAction(EmptyCopyPasteAction)
		.PasteAction(EmptyCopyPasteAction)
		.NameContent()
		.HAlign(HAlign_Fill)
		[
			SNew(SHorizontalBox)
				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(4, 0)
				[
					MrqJob
						? SNew(SCheckBox)
						.IsChecked_Lambda([this, StepParameterPropertyPath]()
							{
								if (MrqJob)
								{
									return MrqJob->IsPropertyRowEnabledInMovieRenderJob(StepParameterPropertyPath)
										? ECheckBoxState::Checked
										: ECheckBoxState::Unchecked;
								}
								return ECheckBoxState::Unchecked;
							})
						.OnCheckStateChanged_Lambda([this, StepParameterPropertyPath](ECheckBoxState NewState)
							{
								if (MrqJob)
								{
									const bool bEnabled = (NewState == ECheckBoxState::Checked);
									UE_LOG(LogTemp, Warning, TEXT("Setting StepParameterPropertyPath = %s, Enabled = %d"), *StepParameterPropertyPath.ToString(), bEnabled);
									MrqJob->SetPropertyRowEnabledInMovieRenderJob(StepParameterPropertyPath, bEnabled);
								}
							})
						: SNullWidget::NullWidget
				]
				+ SHorizontalBox::Slot()
				.Padding(FMargin(0.0f, 1.0f, 0.0f, 1.0f))
				.FillWidth(1)
				[
					SNew(STextBlock)
						.Text(FText::FromString(ParameterName))
						.Font(IDetailLayoutBuilder::GetDetailFont())
						.ColorAndOpacity(FSlateColor::UseForeground())
				]
		]
		.ValueContent()
		.HAlign(HAlign_Fill)
		[
			ValueWidget.ToSharedRef()
		]
		.ExtensionContent()
		[
			EyeWidget
		];
		ValueWidget.ToSharedRef()->SetEnabled(
			TAttribute<bool>::CreateLambda([this, StepParameterPropertyPath]()
				{
					if (MrqJob)
					{
						return MrqJob->IsPropertyRowEnabledInMovieRenderJob(StepParameterPropertyPath);
					}
					
					if (OnIsEnabled.IsBound())
						return OnIsEnabled.Execute();
					return true;
				})
		);

	PropertyRow.Visibility(IsPropertyHidden(FName(ParameterName)) ? EVisibility::Collapsed : EVisibility::Visible);
	
}

bool FDeadlineCloudStepParametersArrayBuilder::IsEyeWidgetEnabled(FName Parameter) const
{
	bool result = false;
	if (Step)
	{
		result = Step->ContainsHiddenParameters(Parameter);
	}

	if (MrqJob)
	{
		if (MrqJob->JobPreset)
		{
			for (auto StepOverride : MrqJob->JobPreset->Steps)
			{
				if (StepOverride)
				{
					if (FName(StepOverride->Name) == StepName)
					{
						result = StepOverride->ContainsHiddenParameters(Parameter);

					}
				}
			}
		}

	}
	return result;
}

bool FDeadlineCloudStepParametersArrayBuilder::IsParameterChangedFromDefault(FName Parameter) const
{
	if (!Step)
		return false;
//for step enabled is always by user, not by default
	return Step->ContainsHiddenParameters(Parameter);
}
TSharedRef<FDeadlineCloudStepParameterListBuilder> FDeadlineCloudStepParameterListBuilder::MakeInstance(TSharedRef<IPropertyHandle> InPropertyHandle, EValueType Type, FString Name)
{
	TSharedRef<FDeadlineCloudStepParameterListBuilder> Builder =
		MakeShared<FDeadlineCloudStepParameterListBuilder>(InPropertyHandle);

	Builder->Type = Type;
	Builder->Name = Name;
	Builder->OnGenerateArrayElementWidget(
		FOnGenerateArrayElementWidget::CreateSP(Builder, &FDeadlineCloudStepParameterListBuilder::OnGenerateEntry));
	return Builder;
}

FDeadlineCloudStepParameterListBuilder::FDeadlineCloudStepParameterListBuilder(TSharedRef<IPropertyHandle> InPropertyHandle)
	: FDetailArrayBuilder(InPropertyHandle, false, false, true),
	ArrayProperty(InPropertyHandle->AsArray())
{
}

void FDeadlineCloudStepParameterListBuilder::GenerateWrapperStructHeaderRowContent(FDetailWidgetRow& NodeRow, TSharedRef<SWidget> NameContent)
{
	FDetailArrayBuilder::GenerateHeaderRowContent(NodeRow);

	EmptyCopyPasteAction = FUIAction(
		FExecuteAction::CreateLambda([]() {}),
		FCanExecuteAction::CreateLambda([]() { return false; })
	);

	NodeRow.CopyAction(EmptyCopyPasteAction);
	NodeRow.PasteAction(EmptyCopyPasteAction);

	NodeRow.ValueContent()
		[
			SNew(SHorizontalBox)
				+ SHorizontalBox::Slot()
				.AutoWidth()
				.HAlign(HAlign_Right)
				[
					PropertyCustomizationHelpers::MakeAddButton(
						FSimpleDelegate::CreateLambda([this]()
						{
							if (ArrayProperty.IsValid())
							{
								ArrayProperty->AddItem();
							}
						}),
						TAttribute<FText>(),
						TAttribute<bool>::CreateLambda([this]()
						{
							if (OnIsEnabled.IsBound())
								return OnIsEnabled.Execute();
							return true;
						})
					)
				]
				+ SHorizontalBox::Slot()
				.AutoWidth()
				.HAlign(HAlign_Right)
				[
					PropertyCustomizationHelpers::MakeEmptyButton(
						FSimpleDelegate::CreateLambda([this]()
						{
							if (ArrayProperty.IsValid())
							{
								ArrayProperty->EmptyArray();
							}
						}),
						TAttribute<FText>(),
						TAttribute<bool>::CreateLambda([this]()
						{
							if (OnIsEnabled.IsBound())
								return OnIsEnabled.Execute();
							return true;
						})
					)
				]
		];

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

void FDeadlineCloudStepParameterListBuilder::OnGenerateEntry(TSharedRef<IPropertyHandle> ElementProperty, int32 ElementIndex, IDetailChildrenBuilder& ChildrenBuilder) const
{
	IDetailPropertyRow& PropertyRow = ChildrenBuilder.AddProperty(ElementProperty);

	// Hide the reset to default button since it provides little value
	const FResetToDefaultOverride ResetDefaultOverride =
		FResetToDefaultOverride::Create(TAttribute<bool>(false));

	PropertyRow.OverrideResetToDefault(ResetDefaultOverride);
	PropertyRow.ShowPropertyButtons(true);

	TSharedPtr<SWidget> NameWidget;
	TSharedPtr<SWidget> ValueWidget;
	
	TSharedPtr<SWidget> CustomWidget = FDeadlineCloudDetailsWidgetsHelper::CreatePropertyWidgetByType(ElementProperty, Type, EValueValidationType::StepParameterValue);
	FName Tag = FName("StepParameter." + Name);
	CustomWidget->AddMetadata(FDriverMetaData::Id(Tag));

	PropertyRow.GetDefaultWidgets(NameWidget, ValueWidget);

	PropertyRow.CustomWidget(true)
		.CopyAction(EmptyCopyPasteAction)
		.PasteAction(EmptyCopyPasteAction)
		.NameContent()
		.HAlign(HAlign_Fill)
		[
			NameWidget.ToSharedRef()
		]
		.ValueContent()
		.HAlign(HAlign_Fill)
		.VAlign(VAlign_Center)
		[
			SNew(SHorizontalBox)
				+ SHorizontalBox::Slot()
				[
					CustomWidget.ToSharedRef()
				]

		];

	CustomWidget.ToSharedRef()->SetEnabled(
		TAttribute<bool>::CreateLambda([this, ElementProperty]()
			{
				// Get the property path for the parent property that contains the checkbox state
				FString PropertyPathString;
				if (ParentPropertyHandle.IsValid())
				{
					PropertyPathString = ParentPropertyHandle->GeneratePathToProperty();
				}
				else
				{
					// Fallback to element property path
					PropertyPathString = ElementProperty->GeneratePathToProperty();
				}
				const FName PropertyPath(*PropertyPathString);
				
				// Check if we have an MrqJob and use its enabled state
				if (MrqJob)
				{
					return MrqJob->IsPropertyRowEnabledInMovieRenderJob(PropertyPath);
				}
				
				// Fallback to OnIsEnabled delegate
				if (OnIsEnabled.IsBound())
					return OnIsEnabled.Execute();
				return true;
			})
		);
}

void FDeadlineCloudStepParameterListCustomization::CustomizeHeader(TSharedRef<IPropertyHandle> InPropertyHandle, FDetailWidgetRow& InHeaderRow, IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
	TSharedPtr<IPropertyHandle> ArrayHandle = InPropertyHandle->GetChildHandle("Range", false);

	const TSharedPtr<IPropertyHandle> TypeHandle = InPropertyHandle->GetChildHandle("Type", false);
	const TSharedPtr<IPropertyHandle> NameHandle = InPropertyHandle->GetChildHandle("Name", false);
	if (!TypeHandle.IsValid())
	{
		UE_LOG(LogTemp, Error, TEXT("FDeadlineCloudStepParameterListBuilder Type handle is not valid"));
		return;
	}

	uint8 TypeValue;
	TypeHandle->GetValue(TypeValue);

	auto Type = (EValueType)TypeValue;

	FString NameValue;
	NameHandle->GetValue(NameValue);

	ArrayBuilder = FDeadlineCloudStepParameterListBuilder::MakeInstance(ArrayHandle.ToSharedRef(), Type, NameValue);
	ArrayBuilder->ParentPropertyHandle = InPropertyHandle;

	ArrayBuilder->GenerateWrapperStructHeaderRowContent(InHeaderRow, InPropertyHandle->CreatePropertyNameWidget());
}


void FDeadlineCloudStepParameterListCustomization::CustomizeChildren(TSharedRef<IPropertyHandle> InPropertyHandle, IDetailChildrenBuilder& InChildBuilder, IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
	ArrayBuilder->MrqJob = FDeadlineCloudDetailsWidgetsHelper::GetMrqJob(InPropertyHandle);
	InChildBuilder.AddCustomBuilder(ArrayBuilder.ToSharedRef());
}

#undef LOCTEXT_NAMESPACE
