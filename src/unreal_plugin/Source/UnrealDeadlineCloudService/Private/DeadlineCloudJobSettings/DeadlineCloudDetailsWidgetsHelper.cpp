// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "DeadlineCloudJobSettings/DeadlineCloudDetailsWidgetsHelper.h"
#include "Widgets/Input/SFilePathPicker.h"
#include "DetailLayoutBuilder.h"
#include "Widgets/Input/SNumericEntryBox.h"
#include "EditorDirectories.h"

#define LOCTEXT_NAMESPACE "DeadlineWidgets"

class  SDeadlineCloudFilePathWidget : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SDeadlineCloudFilePathWidget) {}
        SLATE_ARGUMENT(TSharedPtr<IPropertyHandle>, PathPropertyHandle)
    SLATE_END_ARGS()
    void Construct(const FArguments& InArgs);
private:
    TSharedPtr<IPropertyHandle> PathProperty;
    FString GetSelectedFilePath() const;
    void OnPathPicked(const FString& PickedPath);
};

void SDeadlineCloudFilePathWidget::Construct(const FArguments& InArgs)
{
    PathProperty = InArgs._PathPropertyHandle;
    ChildSlot
        [
            SNew(SFilePathPicker)
		            .BrowseButtonImage(FAppStyle::GetBrush("PropertyWindow.Button_Ellipsis"))
		            .BrowseButtonStyle(FAppStyle::Get(), "HoverHintOnly")
		            .BrowseButtonToolTip(LOCTEXT("FileButtonToolTipText", "Choose a file from this computer"))
		            .BrowseDirectory(FEditorDirectories::Get().GetLastDirectory(ELastDirectory::GENERIC_OPEN))
		            .BrowseTitle(LOCTEXT("PropertyEditorTitle", "File picker..."))
		            .FilePath(this, &SDeadlineCloudFilePathWidget::GetSelectedFilePath)
		            .OnPathPicked(this, &SDeadlineCloudFilePathWidget::OnPathPicked)
        ];
}

void SDeadlineCloudFilePathWidget::OnPathPicked(const FString& PickedPath)
{
    PathProperty->SetValue(PickedPath);
}

FString SDeadlineCloudFilePathWidget::GetSelectedFilePath() const
{
	FString FilePath;
	PathProperty->GetValue(FilePath);

	return FilePath;
}

class SDeadlineCloudStringWidget : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SDeadlineCloudStringWidget) {}
        SLATE_ARGUMENT(TSharedPtr<IPropertyHandle>, StringPropertyHandle)
    SLATE_END_ARGS()

	void Construct(const FArguments& InArgs)
	{
		PathProperty = InArgs._StringPropertyHandle;

		ChildSlot
			[
				SNew(SHorizontalBox)
				+SHorizontalBox::Slot()
					.FillWidth(1.0f)
					.VAlign(VAlign_Center)
					[
						SNew(SEditableTextBox)
							.Font(IDetailLayoutBuilder::GetDetailFont())
							.OnTextChanged(this, &SDeadlineCloudStringWidget::HandleTextChanged)
							.Text(this, &SDeadlineCloudStringWidget::GetText)
					]
            ];
    }

private:
    void HandleTextChanged(const FText& NewText)
	{
		PathProperty->SetValue(NewText.ToString());
    }

	FText GetText() const
	{
		FString String;
		PathProperty->GetValue(String);

		return FText::FromString(String);
	}

	TSharedPtr<IPropertyHandle> PathProperty;
};

class SDeadlineCloudIntWidget : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SDeadlineCloudIntWidget) {}
        SLATE_ARGUMENT(TSharedPtr<IPropertyHandle>, PropertyHandle)
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs)
    {
		Property = InArgs._PropertyHandle;

        ChildSlot
            [
				SNew(SHorizontalBox)
				+SHorizontalBox::Slot()
					.FillWidth(1.0f)
					.VAlign(VAlign_Center)
					[
				SNew(SNumericEntryBox<int32>)
					.Font(IDetailLayoutBuilder::GetDetailFont())
					.AllowSpin(false)
					.MinDesiredValueWidth(50.0f)
					.Value_Lambda([this]
						{
							FString String;
							Property->GetValue(String);
							return FCString::Atoi(*String);
						})
					.OnValueCommitted_Lambda([this](int32 Value, ETextCommit::Type InCommitType)
						{
							Property->SetValue(FString::FromInt(Value));
						})
					]
            ];
    }

private:

	TSharedPtr<IPropertyHandle> Property;
};

class SDeadlineCloudFloatWidget : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SDeadlineCloudFloatWidget) {}
        SLATE_ARGUMENT(TSharedPtr<IPropertyHandle>, PropertyHandle)
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs)
    {
		Property = InArgs._PropertyHandle;

        ChildSlot
            [
				SNew(SHorizontalBox)
				+SHorizontalBox::Slot()
					.FillWidth(1.0f)
					.VAlign(VAlign_Center)
					[
				SNew(SNumericEntryBox<float>)
					.Font(IDetailLayoutBuilder::GetDetailFont())
					.AllowSpin(false)
					.MinDesiredValueWidth(50.0f)
					.Value_Lambda([this]
						{
							FString String;
							Property->GetValue(String);

							return FCString::Atof(*String);
						})
					.OnValueCommitted_Lambda([this](float Value, ETextCommit::Type InCommitType)
						{
							Property->SetValue(FString::SanitizeFloat(Value));
						})
					]
            ];
    }

private:

	TSharedPtr<IPropertyHandle> Property;
};




	void FDeadlineCloudDetailsWidgetsHelper::SConsistencyWidget::Construct(const FArguments & InArgs) {

		OnFixButtonClicked = InArgs._OnFixButtonClicked;

		ChildSlot
			[
				SNew(SHorizontalBox)
					+ SHorizontalBox::Slot()
					.AutoWidth()
					.Padding(5)
					[
						SNew(STextBlock)
							.Text(FText::FromString("Parameters changed. Update parameters?"))
							.ColorAndOpacity(FLinearColor::Yellow) // 
					]

					//update?
					+ SHorizontalBox::Slot()
					.AutoWidth()
					[
						SNew(SButton)
							.Text(FText::FromString("OK"))
							.OnClicked(this, &SConsistencyWidget::HandleButtonClicked)
					]
			];
	};

	void FDeadlineCloudDetailsWidgetsHelper::SEyeUpdateWidget::Construct(const FArguments& InArgs) {

		OnEyeUpdateButtonClicked = InArgs._OnEyeUpdateButtonClicked;

		ChildSlot
			[
				SNew(SHorizontalBox)
					+ SHorizontalBox::Slot()
					.AutoWidth()
					.Padding(5)
					[
						SNew(STextBlock)
							.Text(FText::FromString("Some parameters are hidden. "))
							//.ColorAndOpacity(FLinearColor::Red) // 
					]

					//update?
					+ SHorizontalBox::Slot()
					.AutoWidth()
					[
						SNew(SButton)
							.Text(FText::FromString("Show"))
							.OnClicked(this, &SEyeUpdateWidget::HandleButtonClicked)
					]
			];
	};


TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreatePropertyWidgetByType(TSharedPtr<IPropertyHandle> ParameterHandle, EValueType Type)
{
	switch (Type)
	{
	case EValueType::STRING:
	{
		return CreateStringWidget(ParameterHandle);
	}
	case EValueType::PATH:
	{
		return CreatePathWidget(ParameterHandle);
	}
	case EValueType::INT:
	{
		return CreateIntWidget(ParameterHandle);
	}
	case EValueType::FLOAT:
	{
		return CreateFloatWidget(ParameterHandle);
	}
	default:
	{
		UE_LOG(LogTemp, Error, TEXT("CreatePropertyWidgetByType : Unknown type"));
		break;
	}
	}

	return SNullWidget::NullWidget;
}

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreateNameWidget(FString Parameter)
{
	return  SNew(SHorizontalBox)
			+ SHorizontalBox::Slot()
			.Padding( FMargin( 0.0f, 1.0f, 0.0f, 1.0f) )
			.FillWidth(1)
			[
				SNew(STextBlock)
					.Text(FText::FromString(Parameter))
					.Font(IDetailLayoutBuilder::GetDetailFont())
					.ColorAndOpacity(FSlateColor::UseForeground())
			];
}

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreateConsistencyWidget(FString ResultString)
{
	TSharedRef<SConsistencyWidget> ConsistensyWidget = SNew(SConsistencyWidget)
		.CheckResult(ResultString)
		.Visibility(EVisibility::Collapsed);
	return  ConsistensyWidget;
}

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreateEyeCheckBoxWidget(FName ResultString)
{

	TSharedRef<SEyeCheckBox> EyeWidget = SNew(SEyeCheckBox, ResultString)
		.Visibility(EVisibility::Visible);
	return  EyeWidget;

}

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreateEyeUpdateWidget()
{
	TSharedRef<SEyeUpdateWidget> EyeUpdateWidget = SNew(SEyeUpdateWidget)
		.Visibility(EVisibility::Collapsed);
	return  EyeUpdateWidget;
}

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreatePathWidget(TSharedPtr<IPropertyHandle> ParameterHandle)
{
    return SNew(SDeadlineCloudFilePathWidget)
		.PathPropertyHandle(ParameterHandle);
}

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreateIntWidget(TSharedPtr<IPropertyHandle> ParameterHandle)
{
	return SNew(SDeadlineCloudIntWidget)
		.PropertyHandle(ParameterHandle);
}

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreateFloatWidget(TSharedPtr<IPropertyHandle> ParameterHandle)
{
	return SNew(SDeadlineCloudFloatWidget)
		.PropertyHandle(ParameterHandle);
}

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreateStringWidget(TSharedPtr<IPropertyHandle> ParameterHandle)
{
	return SNew(SDeadlineCloudStringWidget)
		.StringPropertyHandle(ParameterHandle);
}


#undef LOCTEXT_NAMESPACE