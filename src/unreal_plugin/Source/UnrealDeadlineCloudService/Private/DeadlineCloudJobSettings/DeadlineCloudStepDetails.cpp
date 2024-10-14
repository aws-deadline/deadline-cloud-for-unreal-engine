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

#include "DeadlineCloudJobSettings/DeadlineCloudDetailsWidgetsHelper.h"

#define LOCTEXT_NAMESPACE "StepDetails"


void FDeadlineCloudStepDetails::ForceRefreshDetails()
{
    MyDetailLayout->ForceRefreshDetails();
}

TSharedRef<SWidget> FDeadlineCloudStepDetails::GenerateStringsArrayContent(const TArray<FString>& StringArray)
{

    TSharedRef<SVerticalBox> VBox = SNew(SVerticalBox);
    if (StringArray.Num() > 0)
    {
        for (const FString& Str : StringArray)
        {
            VBox->AddSlot()
                .AutoHeight()
                .Padding(5)
                [
                    SNew(SEditableTextBox)
                        .Text(FText::FromString(Str))
                ];
        }
    }

    return VBox;
}

TSharedRef<SWidget> FDeadlineCloudStepDetails::GenerateTasksContent(const TArray<FStepTaskParameterDefinition> tasks)
{

    TSharedRef<SVerticalBox> VBox = SNew(SVerticalBox);
    if (tasks.Num() > 0)
    {
        for (auto& task : tasks)
        {
            VBox->AddSlot()
                .AutoHeight()
                .HAlign(HAlign_Fill)
                .Padding(2)
                [
                    SNew(SHorizontalBox)

                        + SHorizontalBox::Slot()
                        .AutoWidth()
                        .VAlign(VAlign_Top)
                        .Padding(2)
                        [
                            SNew(STextBlock)
                                .Text(FText::FromString(task.Name))
                        ]

                        + SHorizontalBox::Slot()
                        //.FillWidth(1.0f)
                        .VAlign(VAlign_Top)
                        .Padding(2)
                        [
                            SNew(SEditableTextBox)
                                .Text(FText::FromString(""))
                        ]

                        + SHorizontalBox::Slot()
                        .AutoWidth()
                        .VAlign(VAlign_Top)
                        .Padding(2)
                        [
                            SNew(SVerticalBox)
                                + SVerticalBox::Slot()
                                .AutoHeight()
                                [
                                    this->GenerateStringsArrayContent(task.Range)
                                ]
                        ]
                ];
        }
    }

    return VBox;
}

/*Details*/
TSharedRef<IDetailCustomization> FDeadlineCloudStepDetails::MakeInstance()
{
    return MakeShareable(new FDeadlineCloudStepDetails);
}

void FDeadlineCloudStepDetails::CustomizeDetails(IDetailLayoutBuilder& DetailBuilder)
{
	MyDetailLayout = &DetailBuilder;
    TArray<TWeakObjectPtr<UObject>> ObjectsBeingCustomized;
    DetailBuilder.GetObjectsBeingCustomized(ObjectsBeingCustomized);
    Settings = Cast<UDeadlineCloudStep>(ObjectsBeingCustomized[0].Get());

    if (Settings.IsValid() && (MyDetailLayout != nullptr))
    {
        Settings->OnSomethingChanged = FSimpleDelegate::CreateSP(this, &FDeadlineCloudStepDetails::ForceRefreshDetails);
    };

    //FString CurrentName;

    //if (Settings->PathToTemplate.FilePath.Len() > 0)
    //{
    //    TArray <FStepTaskParameterDefinition> Parameters;
    //    Settings->OpenStepFile(Settings->PathToTemplate.FilePath);
    //    Parameters = Settings->GetStepParameters();
    //    if (Parameters.Num() > 0) {

    //        IDetailCategoryBuilder& PropertiesCategory = DetailBuilder.EditCategory("DeadlineCloudStepParameters");

    //        for (auto& StepParameter : Parameters) {

    //            CurrentName = StepParameter.Name;

    //            {
    //                PropertiesCategory.AddCustomRow(LOCTEXT("Parameter Definitions", "Parameter Definitions"))
    //                    .NameContent()
    //                    [CreateStepNameWidget(StepParameter.Name)]
    //                    .ValueContent()
    //                    [GenerateStringsArrayContent(StepParameter.Range)];
    //            }

    //        }
    //    }
    //    else
    //    {
    //        UE_LOG(LogTemp, Error, TEXT("PARAMETERS PARSING ERROR"));
    //    }
    //}

    //else
    //{
    //    UE_LOG(LogTemp, Warning, TEXT("Empty step path string"));
    //}
}

void FDeadlineCloudStepParametersArrayCustomization::CustomizeHeader(TSharedRef<IPropertyHandle> InPropertyHandle, FDetailWidgetRow& InHeaderRow, IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
	const TSharedPtr<IPropertyHandle> ArrayHandle = InPropertyHandle->GetChildHandle("Parameters", false);
	ArrayBuilder = FDeadlineCloudStepParametersArrayBuilder::MakeInstance(ArrayHandle.ToSharedRef());

	auto OuterStep = FDeadlineCloudStepParametersArrayBuilder::GetOuterStep(InPropertyHandle);
	if (IsValid(OuterStep))
	{
		ArrayBuilder->OnIsEnabled.BindSPLambda(this, [OuterStep]()->bool
			{
				return !OuterStep->TaskParameterDefinitions.Parameters.IsEmpty();
			});
	}

    ArrayBuilder->GenerateWrapperStructHeaderRowContent(InHeaderRow, InPropertyHandle->CreatePropertyNameWidget());
}

void FDeadlineCloudStepParametersArrayCustomization::CustomizeChildren(TSharedRef<IPropertyHandle> InPropertyHandle, IDetailChildrenBuilder& InChildBuilder, IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
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
	return OuterStep;
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
		ArrayProperty(InPropertyHandle->AsArray())
{

}

void FDeadlineCloudStepParametersArrayBuilder::GenerateHeaderRowContent(FDetailWidgetRow& NodeRow)
{
}

void FDeadlineCloudStepParametersArrayBuilder::GenerateWrapperStructHeaderRowContent(FDetailWidgetRow& NodeRow, TSharedRef<SWidget> NameContent)
{
	FDetailArrayBuilder::GenerateHeaderRowContent(NodeRow);

	EmptyCopyPasteAction = FUIAction(
		FExecuteAction::CreateLambda([]() {}),
		FCanExecuteAction::CreateLambda([]() { return false; })
	);

	NodeRow.CopyAction(EmptyCopyPasteAction);
	NodeRow.PasteAction(EmptyCopyPasteAction);

	NodeRow.OverrideResetToDefault(FResetToDefaultOverride::Create(TAttribute<bool>(false)));

	NodeRow.ValueContent()
	.HAlign( HAlign_Left )
	.VAlign( VAlign_Center )
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

void FDeadlineCloudStepParametersArrayBuilder::OnGenerateEntry(TSharedRef<IPropertyHandle> ElementProperty, int32 ElementIndex, IDetailChildrenBuilder& ChildrenBuilder) const
{
	IDetailPropertyRow& PropertyRow = ChildrenBuilder.AddProperty(ElementProperty);

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
			FIsResetToDefaultVisible::CreateSPLambda(this, [this, OuterStep, ParameterName](TSharedPtr<IPropertyHandle> PropertyHandle)->bool 
                { 
                    if (!PropertyHandle.IsValid())
                    {
                        return false;
                    }

					if (!IsValid(OuterStep))
					{
                        return false;
					}
                          
                    return !OuterStep->IsParameterArrayDefault(ParameterName); 
                }),
            FResetToDefaultHandler::CreateSPLambda(this, [this, ParameterName, OuterStep](TSharedPtr<IPropertyHandle> PropertyHandle) 
                {
                    if (!PropertyHandle.IsValid())
                    {
                        return;
                    }

					if (!IsValid(OuterStep))
					{
                        return;
					}

					OuterStep->ResetParameterArray(ParameterName);
                })
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

	PropertyRow.GetDefaultWidgets( NameWidget, ValueWidget);

	PropertyRow.CustomWidget(true)
	.CopyAction(EmptyCopyPasteAction)
	.PasteAction(EmptyCopyPasteAction)
	.NameContent()
	.HAlign(HAlign_Fill)
	[
        SNew(SHorizontalBox)
            + SHorizontalBox::Slot()
		    .Padding( FMargin( 0.0f, 1.0f, 0.0f, 1.0f) )
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

TSharedRef<FDeadlineCloudStepParameterListBuilder> FDeadlineCloudStepParameterListBuilder::MakeInstance(TSharedRef<IPropertyHandle> InPropertyHandle, EValueType Type)
{
	TSharedRef<FDeadlineCloudStepParameterListBuilder> Builder =
		MakeShared<FDeadlineCloudStepParameterListBuilder>(InPropertyHandle);

	Builder->Type = Type;

	Builder->OnGenerateArrayElementWidget(
		FOnGenerateArrayElementWidget::CreateSP(Builder, &FDeadlineCloudStepParameterListBuilder::OnGenerateEntry));
	return Builder;
}

FDeadlineCloudStepParameterListBuilder::FDeadlineCloudStepParameterListBuilder(TSharedRef<IPropertyHandle> InPropertyHandle)
    : FDetailArrayBuilder(InPropertyHandle, true, false, true),
		ArrayProperty(InPropertyHandle->AsArray())
{
}

void FDeadlineCloudStepParameterListBuilder::GenerateHeaderRowContent(FDetailWidgetRow& NodeRow)
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

	PropertyRow.GetDefaultWidgets( NameWidget, ValueWidget);

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
			FDeadlineCloudDetailsWidgetsHelper::CreatePropertyWidgetByType(ElementProperty, Type)
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

void FDeadlineCloudStepParameterListCustomization::CustomizeHeader(TSharedRef<IPropertyHandle> InPropertyHandle, FDetailWidgetRow& InHeaderRow, IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
    TSharedPtr<IPropertyHandle> ArrayHandle = InPropertyHandle->GetChildHandle("Range", false);

	const TSharedPtr<IPropertyHandle> TypeHandle = InPropertyHandle->GetChildHandle("Type", false);

	if (!TypeHandle.IsValid())
	{
		UE_LOG(LogTemp, Error, TEXT("FDeadlineCloudStepParameterListBuilder Type handle is not valid"));
		return;
	}

	uint8 TypeValue;
	TypeHandle->GetValue(TypeValue);

	EValueType Type = (EValueType)TypeValue;

	ArrayBuilder = FDeadlineCloudStepParameterListBuilder::MakeInstance(ArrayHandle.ToSharedRef(), Type);

    ArrayBuilder->GenerateWrapperStructHeaderRowContent(InHeaderRow, InPropertyHandle->CreatePropertyNameWidget());
}

void FDeadlineCloudStepParameterListCustomization::CustomizeChildren(TSharedRef<IPropertyHandle> InPropertyHandle, IDetailChildrenBuilder& InChildBuilder, IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
    InChildBuilder.AddCustomBuilder(ArrayBuilder.ToSharedRef());
}

#undef LOCTEXT_NAMESPACE
