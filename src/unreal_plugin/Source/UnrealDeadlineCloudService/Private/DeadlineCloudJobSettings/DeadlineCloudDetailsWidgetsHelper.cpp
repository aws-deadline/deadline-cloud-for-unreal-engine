// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "DeadlineCloudJobSettings/DeadlineCloudDetailsWidgetsHelper.h"
#include "DeadlineCloudJobSettings/DeadlineCloudInputValidationHelper.h"
#include "MovieRenderPipeline/MoviePipelineDeadlineCloudExecutorJob.h"
#include "Widgets/Input/SFilePathPicker.h"
#include "DetailLayoutBuilder.h"
#include "Widgets/Input/SNumericEntryBox.h"
#include "EditorDirectories.h"
#include "Widgets/Notifications/SPopUpErrorText.h"
#include "DesktopPlatformModule.h"
#include "SWarningOrErrorBox.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "ContentBrowserModule.h"
#include "IContentBrowserSingleton.h"
#include "PackageTools.h"
#include "Framework/MetaData/DriverMetaData.h"
#include "Misc/Optional.h"

#define LOCTEXT_NAMESPACE "DeadlineWidgets"

class SIntSpinAsFloatOptional : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SIntSpinAsFloatOptional)
		: _Required(false)
		, _MinInt(TNumericLimits<int32>::Lowest())
		, _MaxInt(TNumericLimits<int32>::Max())
		, _Step(1)
		, _DefaultFloat(0.f)
		, _MinDesiredWidth(90.f)
		{
		}
		SLATE_ARGUMENT(TSharedPtr<IPropertyHandle>, FloatHandle)
		SLATE_ARGUMENT(TSharedPtr<IPropertyHandle>, TypeHandle) // TEnumAsByte<ERangeBoundTypes::Type>
			SLATE_ARGUMENT(bool, Required)
		SLATE_ARGUMENT(int32, MinInt)
		SLATE_ARGUMENT(int32, MaxInt)
		SLATE_ARGUMENT(int32, Step)
		SLATE_ARGUMENT(float, DefaultFloat)
		SLATE_ARGUMENT(float, MinDesiredWidth)
		SLATE_ATTRIBUTE(FText, OptionalTooltip)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs)
	{
		FloatHandle = InArgs._FloatHandle; check(FloatHandle.IsValid());
		TypeHandle = InArgs._TypeHandle;  check(TypeHandle.IsValid());
		bRequired = InArgs._Required;
		MinInt = InArgs._MinInt;
		MaxInt = InArgs._MaxInt;
		Step = FMath::Max(1, InArgs._Step);
		DefaultFloat = InArgs._DefaultFloat;
		MinDesiredWidth = InArgs._MinDesiredWidth;

		float F = DefaultFloat;
		if (FloatHandle->GetValue(F) != FPropertyAccess::Success) F = DefaultFloat;
		CurrentInt = FMath::Clamp(static_cast<int32>(FMath::RoundHalfFromZero(F)), MinInt, MaxInt);

		uint8 TypeVal = 0;
		if (TypeHandle->GetValue(TypeVal) != FPropertyAccess::Success) TypeVal = 0;

		ChildSlot
			[
				SAssignNew(Spin, SSpinBox<int32>)
					.ToolTipText(InArgs._OptionalTooltip)
					.MinDesiredWidth(MinDesiredWidth)
					.MinValue(MinInt)
					.MaxValue(MaxInt)
					.Value(this, &SIntSpinAsFloatOptional::GetSpinValue)
					.Delta(Step)
					.OnValueChanged(this, &SIntSpinAsFloatOptional::OnSpinChanged)
					.OnValueCommitted(this, &SIntSpinAsFloatOptional::OnSpinCommitted)
					.OnEndSliderMovement(this, &SIntSpinAsFloatOptional::OnSpinEnd)
			];
	}

private:
	TSharedPtr<IPropertyHandle> FloatHandle;
	TSharedPtr<IPropertyHandle> TypeHandle;
	TSharedPtr<SSpinBox<int32>> Spin;

	bool bRequired = false;
	int32 MinInt = 0;
	int32 MaxInt = 0;
	int32 Step = 1;
	int32 CurrentInt = 0;
	float DefaultFloat = 0.f;
	float MinDesiredWidth = 90.f;

	int32 GetSpinValue() const { return CurrentInt; }

	void PushTypeOpen()
	{
		if (TypeHandle.IsValid())
		{
			uint8 OpenVal = 2; // ERangeBoundTypes::Open
			TypeHandle->SetValue(OpenVal);
		}
	}

	void PushTypeInclusive()
	{
		if (TypeHandle.IsValid())
		{
			uint8 InclusiveVal = 1; // ERangeBoundTypes::Inclusive
			TypeHandle->SetValue(InclusiveVal);
		}
	}

	void PushFloatFromInt(int32 V, EPropertyValueSetFlags::Type Flags = EPropertyValueSetFlags::DefaultFlags)
	{
		if (FloatHandle.IsValid())
		{
			const float AsF = static_cast<float>(V);
			if (Flags == EPropertyValueSetFlags::DefaultFlags) FloatHandle->SetValue(AsF);
			else FloatHandle->SetValue(AsF, Flags);
		}
	}

	void OnSpinChanged(int32 NewVal)
	{
		CurrentInt = FMath::Clamp(NewVal, MinInt, MaxInt);
		if (!bRequired && CurrentInt == MinInt)
		{
			PushTypeOpen();
			return;
		}
		PushTypeInclusive();
		PushFloatFromInt(CurrentInt, EPropertyValueSetFlags::InteractiveChange);
	}

	void OnSpinCommitted(int32 NewVal, ETextCommit::Type)
	{
		CurrentInt = FMath::Clamp(NewVal, MinInt, MaxInt);
		if (!bRequired && CurrentInt == MinInt)
		{
			PushTypeOpen();
			PushFloatFromInt(CurrentInt);
			return;
		}
		PushTypeInclusive();
		PushFloatFromInt(CurrentInt);
	}

	void OnSpinEnd(int32 NewVal)
	{
		CurrentInt = FMath::Clamp(NewVal, MinInt, MaxInt);
		if (!bRequired && CurrentInt == MinInt) return;
		PushFloatFromInt(CurrentInt);
	}
};

class SDeadlineCloudSavePresetWidget : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SDeadlineCloudSavePresetWidget)
		: _MrqJob(nullptr)
		{}
		/** The MRQ job to save the preset for. */
		SLATE_ARGUMENT(UMoviePipelineDeadlineCloudExecutorJob*, MrqJob)
		SLATE_ARGUMENT(FString, Name)

	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);
protected:
	EVisibility GetErrorLabelVisibility() const;
	FText GetErrorLabelText() const;
	FText OnGetNameText() const;
	void OnNameTextChanged(const FText& NewText);
	void OnNameTextCommitted(const FText& NewText, ETextCommit::Type CommitType);
	FText OnGetPathText() const;
	void OnPathTextChanged(const FString& NewText);
	FReply HandleChooseFolderButtonClicked();
	FReply HandleCreateButtonClicked();
	//is create button enabled
	bool IsCreateButtonEnabled() const
	{
		return bLastInputValidityCheckSuccessful || LastInputValidityErrorStyle == EMessageStyle::Warning;
	}

	void OnSetAsDefaultChanged(ECheckBoxState NewState)
	{
		bSetAsDefault = (NewState == ECheckBoxState::Checked);
	}

	void CloseWindow();
	FReply HandleCancelButtonClicked();
	FText GetJobResultPath() const;
	void UpdateValidity();
private:
	UMoviePipelineDeadlineCloudExecutorJob* MrqJob;
	FString NewName;
	TSharedPtr<SEditableTextBox> NameEditBox;
	FString NewPath;
	bool bSetAsDefault = false;

	EMessageStyle LastInputValidityErrorStyle = EMessageStyle::Error;
	FText LastInputValidityErrorText;
	bool bLastInputValidityCheckSuccessful = true;
};

void SDeadlineCloudSavePresetWidget::Construct(const FArguments& InArgs)
{
	MrqJob = InArgs._MrqJob;
	NewName = InArgs._Name;

	FContentBrowserModule& ContentBrowserModule = FModuleManager::LoadModuleChecked<FContentBrowserModule>("ContentBrowser");
	FPathPickerConfig PathCfg;
    PathCfg.DefaultPath = TEXT("/Game");
	PathCfg.OnPathSelected = FOnPathSelected::CreateSP(this, &SDeadlineCloudSavePresetWidget::OnPathTextChanged);
	NewPath = PathCfg.DefaultPath;

	TSharedRef<SWarningOrErrorBox> ErrorBox = SNew(SWarningOrErrorBox)
		.MessageStyle_Lambda([this]() { return LastInputValidityErrorStyle; })
		.Message(this, &SDeadlineCloudSavePresetWidget::GetErrorLabelText);
	ErrorBox->AddMetadata(FDriverMetaData::Id(FName("DeadlineCloudSavePresetWidget.ErrorBox")));

	 SAssignNew(NameEditBox, SEditableTextBox)
		.MinDesiredWidth(420.0f)
		.Text(this, &SDeadlineCloudSavePresetWidget::OnGetNameText)
		.OnTextChanged(this, &SDeadlineCloudSavePresetWidget::OnNameTextChanged)
		.OnTextCommitted(this, &SDeadlineCloudSavePresetWidget::OnNameTextCommitted);
	NameEditBox->AddMetadata(FDriverMetaData::Id(FName("DeadlineCloudSavePresetWidget.NameEditBox")));

	TSharedRef<SButton> CreateButton = SNew(SButton)
		.ButtonStyle(FAppStyle::Get(), "PrimaryButton")
		.Text(LOCTEXT("CreateBtn", "Create"))
		.IsEnabled(this, &SDeadlineCloudSavePresetWidget::IsCreateButtonEnabled)
		.OnClicked(this, &SDeadlineCloudSavePresetWidget::HandleCreateButtonClicked);
	CreateButton->AddMetadata(FDriverMetaData::Id(FName("DeadlineCloudSavePresetWidget.CreateButton")));

	TSharedRef<SButton> CancelButton = SNew(SButton)
		.Text(LOCTEXT("CancelBtn", "Cancel"))
		.OnClicked(this, &SDeadlineCloudSavePresetWidget::HandleCancelButtonClicked);
	CancelButton->AddMetadata(FDriverMetaData::Id(FName("DeadlineCloudSavePresetWidget.CancelButton")));

	ChildSlot
	[
		SNew(SBorder)
			.Padding(0)
			.BorderImage(FAppStyle::GetBrush("Brushes.Panel"))
			[
				SNew(SVerticalBox)

				+ SVerticalBox::Slot()
					.AutoHeight()
					[
						SNew(SBorder)
							.Visibility(this, &SDeadlineCloudSavePresetWidget::GetErrorLabelVisibility)
							.Padding(FMargin(12.0f, 8.0f))
							.BorderBackgroundColor(FLinearColor(0.24f, 0.05f, 0.05f)) 
							.BorderImage(FAppStyle::GetBrush("DetailsView.CategoryTop"))
							[
								SNew(SHorizontalBox)
								+ SHorizontalBox::Slot()
									.FillWidth(1.0f)
									.VAlign(VAlign_Center)
									[
										ErrorBox
									]
							]
					]


				+ SVerticalBox::Slot()
				.FillHeight(1.0f)
				.Padding(FMargin(10.0f)) 
					[
						SNew(SBorder)
							.Padding(10.0f)
							.BorderImage(FAppStyle::GetBrush("ToolPanel.GroupBorder")) 
							[
								SNew(SGridPanel)
								.FillColumn(1, 1.0f)      

								+ SGridPanel::Slot(0, 0)
									.VAlign(VAlign_Center)
									.HAlign(HAlign_Left)
									.Padding(0.0f, 0.0f, 12.0f, 0.0f)
									[
										SNew(STextBlock)
										.Text(LOCTEXT("PathLabel", "Folder"))
									]

								+ SGridPanel::Slot(1, 0)
									.VAlign(VAlign_Center)
									[
										ContentBrowserModule.Get().CreatePathPicker(PathCfg)
									]

								+ SGridPanel::Slot(0, 1)
									.VAlign(VAlign_Center)
									.HAlign(HAlign_Left)
									.Padding(0.0f, 6.0f, 12.0f, 6.0f)
									[
										SNew(STextBlock)
										.Text(LOCTEXT("NameLabel", "Name"))
									]

								+ SGridPanel::Slot(1, 1)
									.VAlign(VAlign_Center)
									.Padding(0.0f, 6.0f, 0.0f, 6.0f)
									[
										NameEditBox.ToSharedRef()
									]


								+ SGridPanel::Slot(0, 2)
									.VAlign(VAlign_Center)
									.HAlign(HAlign_Left)
									.Padding(0.0f, 10.0f, 0.0f, 0.0f)
									[
										SNew(STextBlock)
											.Text(LOCTEXT("JobLabel", "Job Path"))
									]

								+ SGridPanel::Slot(1, 2)
									.VAlign(VAlign_Center)
									.Padding(6.0f, 10.0f, 6.0f, 0.0f)
									[
										SNew(STextBlock)
											.Text(this, &SDeadlineCloudSavePresetWidget::GetJobResultPath)
									]
							]
					]

			+ SVerticalBox::Slot()
				.AutoHeight()
				.HAlign(HAlign_Fill)
				.VAlign(VAlign_Center)
				.Padding(FMargin(10.0f, 6.0f))
					[
						SNew(SHorizontalBox)
						+ SHorizontalBox::Slot()
							.AutoWidth()
							.Padding(0.0f, 0.0f, 8.0f, 0.0f)
							.HAlign(HAlign_Left)
							.VAlign(VAlign_Center)
							[
									SNew(SHorizontalBox)
									+ SHorizontalBox::Slot()
										.AutoWidth()
										.Padding(0.0f, 0.0f, 8.0f, 0.0f)
										.HAlign(HAlign_Left)
										.VAlign(VAlign_Center)
										[
											SNew(SCheckBox)
												.OnCheckStateChanged(this, &SDeadlineCloudSavePresetWidget::OnSetAsDefaultChanged)
												.IsChecked_Lambda([this]() { return bSetAsDefault ? ECheckBoxState::Checked : ECheckBoxState::Unchecked; })
													
										]
									+ SHorizontalBox::Slot()
										.AutoWidth()
										.HAlign(HAlign_Left)
										.VAlign(VAlign_Center)
										.Padding(0.0f, 0.0f, 8.0f, 0.0f)
										[
											SNew(STextBlock)
												.Text(LOCTEXT("SetDefaultPreset", "Set as default preset"))
												.Justification(ETextJustify::Center)
										]
							]
						+ SHorizontalBox::Slot()
							.FillWidth(1.0f)
							.HAlign(HAlign_Fill)
							.VAlign(VAlign_Center)
							.Padding(0.0f, 0.0f, 0.0f, 0.0f)
							[
								SNew(SSpacer)
							]

						+ SHorizontalBox::Slot()
							.AutoWidth()
							.Padding(0.0f, 0.0f, 8.0f, 0.0f)
							.HAlign(HAlign_Right)
							.VAlign(VAlign_Center)
							[
								CreateButton
							]

						+ SHorizontalBox::Slot()
							.AutoWidth()
							.HAlign(HAlign_Right)
							[
								CancelButton
							]
					]
			]
	];

	AddMetadata(FDriverMetaData::Id(FName("DeadlineCloudSavePresetWidget")));
}

EVisibility SDeadlineCloudSavePresetWidget::GetErrorLabelVisibility() const
{
	return GetErrorLabelText().IsEmpty() ? EVisibility::Collapsed : EVisibility::Visible;
}

FText SDeadlineCloudSavePresetWidget::GetErrorLabelText() const
{
	if (bLastInputValidityCheckSuccessful)
	{
		return FText::GetEmpty();
	}
	return LastInputValidityErrorText;
}


FText SDeadlineCloudSavePresetWidget::OnGetNameText() const
{
	return FText::FromString(NewName);
}

void SDeadlineCloudSavePresetWidget::OnNameTextChanged(const FText& NewText)
{
	NewName = NewText.ToString();
	UpdateValidity();
}

void SDeadlineCloudSavePresetWidget::OnNameTextCommitted(const FText& NewText, ETextCommit::Type CommitType)
{
	UpdateValidity();
}

FText SDeadlineCloudSavePresetWidget::OnGetPathText() const
{
	return FText::FromString(NewPath);
}

void SDeadlineCloudSavePresetWidget::OnPathTextChanged(const FString& NewText)
{
	NewPath = NewText;

	UpdateValidity();
}

FReply SDeadlineCloudSavePresetWidget::HandleChooseFolderButtonClicked()
{
	IDesktopPlatform* DesktopPlatform = FDesktopPlatformModule::Get();
	if ( DesktopPlatform )
	{
		TSharedPtr<SWindow> ParentWindow = FSlateApplication::Get().FindWidgetWindow(AsShared());
		void* ParentWindowWindowHandle = (ParentWindow.IsValid()) ? ParentWindow->GetNativeWindow()->GetOSWindowHandle() : nullptr;

		FString FolderName;
		const FString Title = LOCTEXT("NewClassBrowseTitle", "Choose a source location").ToString();
		const bool bFolderSelected = DesktopPlatform->OpenDirectoryDialog(
			ParentWindowWindowHandle,
			Title,
			NewPath,
			FolderName
			);

		if ( bFolderSelected )
		{
			if ( !FolderName.EndsWith(TEXT("/")) )
			{
				FolderName += TEXT("/");
			}

			NewPath = FolderName;

			UpdateValidity();
		}
	}

	return FReply::Handled();
}

void SDeadlineCloudSavePresetWidget::CloseWindow()
{
	TSharedPtr<SWindow> ParentWindow = FSlateApplication::Get().FindWidgetWindow(AsShared());
	if (ParentWindow.IsValid())
	{
		ParentWindow->RequestDestroyWindow();
	}
}

FReply SDeadlineCloudSavePresetWidget::HandleCreateButtonClicked()
{
	if (!bLastInputValidityCheckSuccessful && LastInputValidityErrorStyle == EMessageStyle::Warning)
	{
		// Show a warning dialog to the user
		FText WarningTitle = LOCTEXT("CreatePresetWarningTitle", "Warning");
		FText WarningMessage = LOCTEXT("OverrideDialog", "Override existing data assets");

		EAppReturnType::Type Result = FMessageDialog::Open(EAppMsgType::OkCancel, WarningMessage, WarningTitle);

		if (Result != EAppReturnType::Ok)
		{
			return FReply::Handled();
		}
	}

	FString FolderPath = UPackageTools::SanitizePackageName(NewPath + TEXT("/") + NewName);
	MrqJob->SaveAsJobPreset(FolderPath, NewName, bSetAsDefault);

	CloseWindow();

	return FReply::Handled();
}

FReply SDeadlineCloudSavePresetWidget::HandleCancelButtonClicked()
{
	CloseWindow();

	return FReply::Handled();
}

FText SDeadlineCloudSavePresetWidget::GetJobResultPath() const
{
	return FText::FromString(FPaths::Combine(NewPath, NewName));
}

void SDeadlineCloudSavePresetWidget::UpdateValidity()
{
	bLastInputValidityCheckSuccessful = true;

	if (NewName.IsEmpty())
	{
		LastInputValidityErrorText = LOCTEXT("AssetDialog_NoNameSelected", "You must select a name.");
		LastInputValidityErrorStyle = EMessageStyle::Error;
		bLastInputValidityCheckSuccessful = false;
		return;
	}

	if ( NewPath.IsEmpty() )
	{
		LastInputValidityErrorText = LOCTEXT("AssetDialog_NoPathSelected", "You must select a path.");
		LastInputValidityErrorStyle = EMessageStyle::Error;
		bLastInputValidityCheckSuccessful = false;
		return;
	}
	FString FolderPath = UPackageTools::SanitizePackageName(NewPath + TEXT("/") + NewName);

	TMap<UDataAsset*, FString> ObjectsNames;
	UMoviePipelineDeadlineCloudExecutorJob::GeneratePresetObjectsNames(MrqJob, FolderPath, NewName, ObjectsNames);

	TMap<UDataAsset*, FString> CurrentPresetObjects;
	UMoviePipelineDeadlineCloudExecutorJob::GetPresetObjectsNames(MrqJob, CurrentPresetObjects);

	for (const auto& ObjectName : ObjectsNames)
	{
		for (const auto& CurrentObject : CurrentPresetObjects)
		{
			if (ObjectName.Value == CurrentObject.Value)
			{
				LastInputValidityErrorText = FText::Format(LOCTEXT("AssetDialog_OverrideCurrentPreset", "You cannot override current preset asset '{0}'."), FText::FromString(ObjectName.Value));
				bLastInputValidityCheckSuccessful = false;
				LastInputValidityErrorStyle = EMessageStyle::Error;
				return;
			}
		}
	}

	for (const auto& ObjectName : ObjectsNames)
	{
		const FString PackageName = UPackageTools::SanitizePackageName(ObjectName.Value);

		FText Reason;
		if (!FPackageName::IsValidLongPackageName(PackageName, true, &Reason))
		{
			LastInputValidityErrorText = Reason;
			bLastInputValidityCheckSuccessful = false;
			LastInputValidityErrorStyle = EMessageStyle::Error;
			return;
		}

		const FString AssetName  = FPackageName::GetLongPackageAssetName(PackageName);
		const FString ObjectPath = PackageName + TEXT(".") + AssetName;

		FAssetRegistryModule& AssetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
		FAssetData ExistingAsset = AssetRegistryModule.Get().GetAssetByObjectPath(FSoftObjectPath(ObjectPath));
		if (ExistingAsset.IsValid())
		{
			const FString ObjectPathName = FPackageName::ObjectPathToObjectName(ObjectName.Value);
			LastInputValidityErrorText = 
				FText::Format(LOCTEXT("AssetDialog_AssetAlreadyExists", "An asset of type '{0}' already exists at this location with the name '{1}'."), 
					FText::FromString(ExistingAsset.AssetClassPath.ToString()), 
					FText::FromString(AssetName));
			bLastInputValidityCheckSuccessful = false;
			LastInputValidityErrorStyle = EMessageStyle::Warning;
			return;
		}		
	}
}

/*
SDeadlineCloudFilePathWidget is a custom Slate widget class that implements a file path picker interface.
 */
class  SDeadlineCloudFilePathWidget : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SDeadlineCloudFilePathWidget) 
		: _BrowseButtonToolTip(LOCTEXT("BrowseButtonToolTip", "Choose a file from this computer"))
		, _FileTypeFilter(TEXT("All files (*.*)|*.*"))
		, _Font()
		, _IsReadOnly(false)
		, _DialogReturnsFullPath(false)
		{}
		/** The property handle for the file path. */
        SLATE_ARGUMENT(TSharedPtr<IPropertyHandle>, PathPropertyHandle)

		/** The function to call when the text is changed. */
		SLATE_EVENT(FOnVerifyTextChanged, IsValidInput)

		/** Browse button image resource. */
		SLATE_ATTRIBUTE(const FSlateBrush*, BrowseButtonImage)

		/** Browse button visual style. */
		SLATE_STYLE_ARGUMENT(FButtonStyle, BrowseButtonStyle)

		/** Browse button tool tip text. */
		SLATE_ATTRIBUTE(FText, BrowseButtonToolTip)

		/** The directory to browse by default */
		SLATE_ATTRIBUTE(FString, BrowseDirectory)

		/** Title for the browse dialog window. */
		SLATE_ATTRIBUTE(FText, BrowseTitle)

		/** The currently selected file path. */
		SLATE_ATTRIBUTE(FString, FilePath)

		/** File type filter string. */
		SLATE_ATTRIBUTE(FString, FileTypeFilter)

		/** Font color and opacity of the path text box. */
		SLATE_ATTRIBUTE(FSlateFontInfo, Font)

		/** Whether the path text box can be modified by the user. */
		SLATE_ATTRIBUTE(bool, IsReadOnly)

		/** Whether the path returned by the dialog should be converted from relative to full */
		SLATE_ATTRIBUTE(bool, DialogReturnsFullPath)

    SLATE_END_ARGS()
    void Construct(const FArguments& InArgs);
private:
    TSharedPtr<IPropertyHandle> PathProperty;
	FOnVerifyTextChanged IsValidInput;

	/** Holds the directory path to browse by default. */
	TAttribute<FString> BrowseDirectory;

	/** Holds the title for the browse dialog window. */
	TAttribute<FText> BrowseTitle;

	/** Holds the currently selected file path. */
	TAttribute<FString> FilePath;

	/** Holds the file type filter string. */
	TAttribute<FString> FileTypeFilter;

	/** Holds the editable text box. */
	TSharedPtr<SEditableTextBox> TextBox;

	/** Holds the option for the dialog to return full path instead of relative. */
	TAttribute<bool> DialogReturnsFullPath;
    FString GetSelectedFilePath() const;

    void OnPathPickedFromDialog(const FString& PickedPath);
    void OnPathPicked(const FString& PickedPath);

	void OnTextChanged(const FText& InText);
	/** Callback for clicking the browse button. */
	FReply HandleBrowseButtonClicked( );

	/** Callback for getting the text in the path text box. */
	FText HandleTextBoxText( ) const;

	/** Callback for committing the text in the path text box. */
	void HandleTextBoxTextCommitted( const FText& NewText, ETextCommit::Type /*CommitInfo*/ );

	void HandleExternalPathPropertyChanged();
};

void SDeadlineCloudFilePathWidget::Construct(const FArguments& InArgs)
{
	BrowseDirectory = InArgs._BrowseDirectory;
	BrowseTitle = InArgs._BrowseTitle;
	FilePath = InArgs._FilePath;
	FileTypeFilter = InArgs._FileTypeFilter;
	DialogReturnsFullPath = InArgs._DialogReturnsFullPath;
    PathProperty = InArgs._PathPropertyHandle;
	IsValidInput = InArgs._IsValidInput;

    ChildSlot
        [
			SNew(SHorizontalBox)
				+ SHorizontalBox::Slot()
				.VAlign(VAlign_Fill)
				.HAlign(HAlign_Fill)
				.FillWidth(1)
				[
					SNew(SHorizontalBox)

					+ SHorizontalBox::Slot()
						.FillWidth(1.0f)
						.VAlign(VAlign_Center)
						[
							SAssignNew(TextBox, SEditableTextBox)
								.Text(HandleTextBoxText())
								.Font(InArgs._Font)
								.SelectAllTextWhenFocused(true)
								.ClearKeyboardFocusOnCommit(true)
								.OnTextCommitted(this, &SDeadlineCloudFilePathWidget::HandleTextBoxTextCommitted)
								.OnTextChanged(this, &SDeadlineCloudFilePathWidget::OnTextChanged)
								.SelectAllTextOnCommit(false)
								.IsReadOnly(InArgs._IsReadOnly)
						]

					+ SHorizontalBox::Slot()
						.AutoWidth()
						.Padding(4.0f, 0.0f, 0.0f, 0.0f)
						.VAlign(VAlign_Center)
						[
							SNew(SButton)
								.ButtonStyle(InArgs._BrowseButtonStyle)
								.ToolTipText(InArgs._BrowseButtonToolTip)
								.OnClicked(this, &SDeadlineCloudFilePathWidget::HandleBrowseButtonClicked)
								.ContentPadding(2.0f)
								.ForegroundColor(FSlateColor::UseForeground())
								.IsFocusable(false)
								[
									SNew(SImage)
										.Image(InArgs._BrowseButtonImage)
										.ColorAndOpacity(FSlateColor::UseForeground())
								]
						]
				]
		];

	if (IsValidInput.IsBound())
	{
		FText OutError = FText::GetEmpty();
		IsValidInput.Execute(FText::FromString(GetSelectedFilePath()), OutError);
		TextBox->SetError(OutError);
	}

	if (PathProperty.IsValid())
	{
		PathProperty->SetOnPropertyValueChanged(FSimpleDelegate::CreateSP(this, &SDeadlineCloudFilePathWidget::HandleExternalPathPropertyChanged));
	}
}

void SDeadlineCloudFilePathWidget::HandleExternalPathPropertyChanged()
{
	FString NewPath;
	if (PathProperty->GetValue(NewPath) == FPropertyAccess::Success)
	{
		TextBox->SetText(FText::FromString(NewPath));
	}
}

FReply SDeadlineCloudFilePathWidget::HandleBrowseButtonClicked()
{
	IDesktopPlatform* DesktopPlatform = FDesktopPlatformModule::Get();

	if (DesktopPlatform == nullptr)
	{
		return FReply::Handled();
	}

	const FString DefaultPath = BrowseDirectory.IsSet()
		? BrowseDirectory.Get()
		: FPaths::GetPath(GetSelectedFilePath());

	TSharedPtr<SWindow> ParentWindow = FSlateApplication::Get().FindWidgetWindow(AsShared());
	void* ParentWindowHandle = (ParentWindow.IsValid() && ParentWindow->GetNativeWindow().IsValid())
		? ParentWindow->GetNativeWindow()->GetOSWindowHandle()
		: nullptr;

	TArray<FString> OutFiles;

	if (DesktopPlatform->OpenFileDialog(ParentWindowHandle, BrowseTitle.Get().ToString(), DefaultPath, TEXT(""), FileTypeFilter.Get(), EFileDialogFlags::None, OutFiles))
	{
		if (DialogReturnsFullPath.Get())
		{
			OnPathPickedFromDialog(FPaths::ConvertRelativePathToFull(OutFiles[0]));
		}
		else
		{
			OnPathPickedFromDialog(OutFiles[0]);
		}
	}

	return FReply::Handled();
}

FText SDeadlineCloudFilePathWidget::HandleTextBoxText() const
{
	return FText::FromString(GetSelectedFilePath());
}

void SDeadlineCloudFilePathWidget::OnTextChanged(const FText& InText)
{
	if (IsValidInput.IsBound())
	{
		FText Error = FText::GetEmpty();
		IsValidInput.Execute(InText, Error);
		TextBox->SetError(Error);
	}

	TextBox->SetText(InText);
}

void SDeadlineCloudFilePathWidget::HandleTextBoxTextCommitted(const FText& NewText, ETextCommit::Type CommitInfo)
{
	if (IsValidInput.IsBound())
	{
		FText Error = FText::GetEmpty();
		IsValidInput.Execute(NewText, Error);

		if (!Error.IsEmpty())
		{
			TextBox->SetText(HandleTextBoxText());
		}
		else
		{
			OnPathPicked(NewText.ToString());
		}
		TextBox->SetError(FText::GetEmpty());
	}
	else
	{
		OnPathPicked(NewText.ToString());
	}
}

void SDeadlineCloudFilePathWidget::OnPathPickedFromDialog(const FString& PickedPath)
{
	if (IsValidInput.IsBound())
	{
		FText Error = FText::GetEmpty();
		IsValidInput.Execute(FText::FromString(PickedPath), Error);
		TextBox->SetError(Error);
	}

	OnPathPicked(PickedPath);
}

void SDeadlineCloudFilePathWidget::OnPathPicked(const FString& PickedPath)
{
	FPropertyAccess::Result PathResult = PathProperty->SetValue(PickedPath);

	if (PathResult != FPropertyAccess::Success)
	{
		UE_LOG(LogTemp, Error, TEXT("SetValue failed! Result: %d"), static_cast<int32>(PathResult));
	}
}

FString SDeadlineCloudFilePathWidget::GetSelectedFilePath() const
{
	FString PropertyFilePath;
	PathProperty->GetValue(PropertyFilePath);

	return PropertyFilePath;
}

/*
SDeadlineCloudStringWidget is a custom Slate widget that creates an editable text box for string properties.
It handles the display and editing of string values through a property handle.
*/
class SDeadlineCloudStringWidget : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SDeadlineCloudStringWidget) {}
		SLATE_ARGUMENT(TSharedPtr<IPropertyHandle>, StringPropertyHandle)
		SLATE_EVENT(FOnVerifyTextChanged, IsValidInput)
		SLATE_ATTRIBUTE(FText, ToolTip)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs)
	{
		StringProperty = InArgs._StringPropertyHandle;
		IsValidInput = InArgs._IsValidInput;
		ChildSlot
			[
				SNew(SHorizontalBox)
					+ SHorizontalBox::Slot()
					.FillWidth(1.0f)
					.HAlign(HAlign_Fill)
					.VAlign(VAlign_Center)
					[
						SAssignNew(TextBox, SEditableTextBox)
							.Font(IDetailLayoutBuilder::GetDetailFont())
							.Text(this, &SDeadlineCloudStringWidget::GetText)
							.OnTextCommitted(this, &SDeadlineCloudStringWidget::OnTextCommitted)
							.OnTextChanged(this, &SDeadlineCloudStringWidget::OnTextChanged)
							.ToolTipText(InArgs._ToolTip)
					]
			];

		if (IsValidInput.IsBound())
		{
			Error = FText::GetEmpty();
			IsValidInput.Execute(GetText(), Error);
			TextBox->SetError(Error);
		}
	}

private:

	void OnTextChanged(const FText& InText)
	{
		if (IsValidInput.IsBound())
		{
			Error = FText::GetEmpty();
			IsValidInput.Execute(InText, Error);
			TextBox->SetError(Error);
		}
	}

	void OnTextCommitted(const FText& InText, ETextCommit::Type InCommitType)
	{
		if (IsValidInput.IsBound())
		{
			Error = FText::GetEmpty();
			IsValidInput.Execute(InText, Error);
			if (Error.IsEmpty())
			{
				StringProperty->SetValue(InText.ToString());
			}
			else
			{
				TextBox->SetText(GetText());
			}

			TextBox->SetError(FText::GetEmpty());
		}
		else
		{
			StringProperty->SetValue(InText.ToString());
		}
	}

	FText GetText() const
	{
		FString String;
		StringProperty->GetValue(String);

		return FText::FromString(String);
	}

	TSharedPtr<IPropertyHandle> StringProperty;
	TSharedPtr<SEditableTextBox> TextBox;
	FOnVerifyTextChanged IsValidInput;
	FText Error;
};

/*
SDeadlineCloudIntWidget is a custom Slate widget for integer input fields.
It wraps a SNumericEntryBox that converts between string-based input and integer display/editing.
*/
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
					+ SHorizontalBox::Slot()
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
							.OnValueCommitted_Lambda([this](int32 Value, ETextCommit::Type)
								{
									Property->SetValue(FString::FromInt(Value));
								})
					]
			];
	}

private:

	TSharedPtr<IPropertyHandle> Property;
};

/*
SDeadlineCloudFloatWidget is a custom Slate widget for float input fields.
*/
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
					+ SHorizontalBox::Slot()
					.FillWidth(1.0f)
					.VAlign(VAlign_Center)
					[
						SNew(SNumericEntryBox<double>)
							.Font(IDetailLayoutBuilder::GetDetailFont())
							.AllowSpin(false)
							.MinDesiredValueWidth(50.0f)
							.Value_Lambda([this]
								{
									FString String;
									Property->GetValue(String);

									return FCString::Atod(*String);
								})
							.OnValueCommitted_Lambda([this](double Value, ETextCommit::Type)
								{
									Property->SetValue(FString::SanitizeFloat(Value));
								})
					]
			];
	}

private:

	TSharedPtr<IPropertyHandle> Property;
};

/*
SConsistencyWidget shows consistency check result for Deadline Job|Step|Environment parameters and same parameters loaded from .yaml for consistency check.
A part of parameter consistency checking system in a Deadline Cloud plugin, where it notifies users of parameter changes and provides a way to update them.
*/
void FDeadlineCloudDetailsWidgetsHelper::SConsistencyWidget::Construct(const FArguments& InArgs) {

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

				+ SHorizontalBox::Slot()
				.AutoWidth()
				[
					SNew(SButton)
						.Text(FText::FromString("OK"))
						.OnClicked(this, &SConsistencyWidget::HandleButtonClicked)
				]
		];
};
/*
SEyeUpdateWidget shows that some Deadline Job|Step|Environment parameters will be hidden in MRQ tab.
SEyeUpdateWidget makes these parameters visible/hidden to user in Deadline Job|Step|Environment widget.
*/
void FDeadlineCloudDetailsWidgetsHelper::SEyeUpdateWidget::Construct(const FArguments& InArgs) {

	OnEyeUpdateButtonClicked = InArgs._OnEyeUpdateButtonClicked;

	ChildSlot
		[
			SNew(SHorizontalBox)
				+ SHorizontalBox::Slot()
				.AutoWidth()
				.VAlign(VAlign_Center)
				.Padding(5)
				[
					SNew(STextBlock)
						.Text(FText::FromString("Visibility parameters have been changed by the user, restore default values?"))
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(5)
				[
					SNew(SButton)
						.OnClicked(this, &SEyeUpdateWidget::HandleButtonClicked)
						.Text(this, &SEyeUpdateWidget::GetButtonText)
				]
		];
};


void FDeadlineCloudDetailsWidgetsHelper::CreateSavePresetDialogWidget(UMoviePipelineDeadlineCloudExecutorJob* MrqJob, bool bModal)
{
	TSharedRef<SWindow> SaveDialogWindow = SNew(SWindow)
		.Title(FText::FromString("Save Job Preset"))
		.SizingRule(ESizingRule::Autosized)
		.SupportsMinimize(false)
		.SupportsMaximize(false);

	FString PresetName = MrqJob->JobPreset->JobPresetStruct.JobSharedSettings.Name;

	SaveDialogWindow->SetContent(
		SNew(SBox)
		[
			SNew(SDeadlineCloudSavePresetWidget)
				.MrqJob(MrqJob)
				.Name(PresetName)
		]
	);

	if (bModal)
	{
		TSharedPtr<SWindow> ParentWindow = FSlateApplication::Get().FindBestParentWindowForDialogs(nullptr);
		FSlateApplication::Get().AddModalWindow(SaveDialogWindow, ParentWindow, false);
	}
	else
	{
		FSlateApplication::Get().AddWindow(SaveDialogWindow);
	}
}

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreatePropertyWidgetByType(
	TSharedPtr<IPropertyHandle> ParameterHandle, 
	EValueType Type, 
	EValueValidationType ValidationType, 
	FText Tooltip)
{
	switch (Type)
	{
		using enum EValueType;
	case EValueType::STRING:
	{
		FOnVerifyTextChanged Validation = FDeadlineCloudInputValidationHelper::GetStringValidationFunction(ValidationType);
		return CreateStringWidget(ParameterHandle, Validation, Tooltip);
	}
	case EValueType::PATH:
	{
		FOnVerifyTextChanged Validation = FDeadlineCloudInputValidationHelper::GetPathValidationFunction(ValidationType);
		return CreatePathWidget(ParameterHandle, Validation);
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

TSharedPtr<SWidget> FDeadlineCloudDetailsWidgetsHelper::TryCreatePropertyWidgetFromMetadata(TSharedPtr<IPropertyHandle> ParameterHandle)
{
	if (!ParameterHandle.IsValid())
	{
		return nullptr;
	}

	FString TypeString;
	FString ValidationTypeString;

    if (const FString* CustomWidget = ParameterHandle->GetProperty()->FindMetaData(TEXT("CustomWidgetType")))
    {
		FString CustomWidgetName(*CustomWidget);
        UEnum* EnumPtr = StaticEnum<EValueType>();
		if (EnumPtr)
		{
			const int32 EnumValue = EnumPtr->GetValueByName(FName(*CustomWidgetName));
			if (EnumValue != INDEX_NONE)
			{
				EValueValidationType ValidationType = EValueValidationType::Default;

				if (const FString* Validation = ParameterHandle->GetProperty()->FindMetaData(TEXT("ValidationType")))
				{
					FString ValidationString(*Validation);
					UEnum* EnumValueType = StaticEnum<EValueValidationType>();
                    if (EnumValueType)
					{
						const int32 EnumValidationValue = EnumValueType->GetValueByName(FName(*ValidationString));
						if (EnumValidationValue != INDEX_NONE)
                        {
							ValidationType = EValueValidationType(EnumValidationValue);
						}
					}
				}

				return FDeadlineCloudDetailsWidgetsHelper::CreatePropertyWidgetByType(
					ParameterHandle, EValueType(EnumValue), ValidationType);
			}
		}
    }

	return nullptr;
}

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreateNameWidget(FString Parameter)
{
	return  SNew(SHorizontalBox)
		+ SHorizontalBox::Slot()
		.Padding(FMargin(0.0f, 1.0f, 0.0f, 1.0f))
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

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreateMrqCheckBoxWidget(UMoviePipelineDeadlineCloudExecutorJob* MrqJob, FName PropertyPath, bool DefaultValue)
{
	return
		MrqJob
		? SNew(SCheckBox)
		.IsChecked_Lambda([MrqJob, PropertyPath, DefaultValue]()
			{
				if (MrqJob)
				{
					return MrqJob->IsPropertyRowEnabledInMovieRenderJob(PropertyPath)
						? ECheckBoxState::Checked
						: ECheckBoxState::Unchecked;
				}
				return ECheckBoxState::Unchecked;
			})
		.OnCheckStateChanged_Lambda([MrqJob, PropertyPath](ECheckBoxState NewState)
			{
				if (MrqJob)
				{
					const bool bEnabled = (NewState == ECheckBoxState::Checked);
					UE_LOG(LogTemp, Warning, TEXT("Setting PropertyPath = %s, Enabled = %d"), *PropertyPath.ToString(), bEnabled);
					MrqJob->SetPropertyRowEnabledInMovieRenderJob(PropertyPath, bEnabled);
					MrqJob->OnRequestDetailsRefresh.ExecuteIfBound();
				}
			})
		: SNullWidget::NullWidget;
}

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreateMrqCheckBoxWidgetForHostRequiremets(
	UMoviePipelineDeadlineCloudExecutorJob* MrqJob,
	TSharedPtr<IPropertyHandle> IsEnabledHandle,
	TAttribute<bool> IsEnabledAttr
)
{
	return FDeadlineCloudDetailsWidgetsHelper::CreateMrqCheckBoxWidgetCustom(
		MrqJob,
		TAttribute<ECheckBoxState>::Create(
			TAttribute<ECheckBoxState>::FGetter::CreateLambda([MrqJob, IsEnabledHandle, IsEnabledAttr]() -> ECheckBoxState
				{
					if (!MrqJob || !IsEnabledHandle.IsValid())
					{
						return ECheckBoxState::Unchecked;
					}
					bool bEnabled = IsEnabledAttr.Get();

					return bEnabled ? ECheckBoxState::Checked : ECheckBoxState::Unchecked;
				})
		),
		FOnCheckStateChanged::CreateLambda([MrqJob, IsEnabledHandle](ECheckBoxState NewState)
			{
				if (!MrqJob || !IsEnabledHandle.IsValid())
				{
					return;
				}

				const bool bEnabled = (NewState == ECheckBoxState::Checked);

				if (IsEnabledHandle->SetValue(bEnabled) != FPropertyAccess::Result::Success)
				{
					return;
				}
			})
	);
}

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreateMrqCheckBoxWidgetCustom(
	UMoviePipelineDeadlineCloudExecutorJob* MrqJob, 
	TAttribute<ECheckBoxState> StateAttribute, 
	FOnCheckStateChanged ChangeEvent
)
{
	return 
		MrqJob
		? SNew(SCheckBox)
		.IsChecked(StateAttribute)
		.OnCheckStateChanged(ChangeEvent)
		: SNullWidget::NullWidget;
}

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreateDefaultAttributeValueWidget(
	TSharedPtr<IPropertyHandle> AllOfPropertyHandle,
	TSharedPtr<IPropertyHandle> AnyOfPropertyHandle,
	TSharedPtr<IPropertyHandle> SelectedValuePropertyHandle,
	TAttribute<bool>& IsEnabledAttr
)
{
	auto ReadArrayAsStrings = [](const TSharedPtr<IPropertyHandle>& Handle, TArray<FString>& Out)
		{
			Out.Reset();
			if (!Handle.IsValid() || !Handle->AsArray().IsValid()) return;
			uint32 Num = 0;
			Handle->AsArray()->GetNumElements(Num);
			for (uint32 i = 0; i < Num; ++i)
			{
				FString V;
				TSharedPtr<IPropertyHandle> Elem = Handle->AsArray()->GetElement(i);
				if (Elem.IsValid() && Elem->GetValue(V) == FPropertyAccess::Success) Out.Add(V);
			}
		};

	TArray<FString> Options;
	{
		TSet<FString> Unique;
		TArray<FString> Buf;
		ReadArrayAsStrings(AllOfPropertyHandle, Buf);  for (const FString& V : Buf) Unique.Add(V);
		Buf.Reset();
		ReadArrayAsStrings(AnyOfPropertyHandle, Buf);  for (const FString& V : Buf) Unique.Add(V);
		Options = Unique.Array();
	}

	FString Current;
	if (SelectedValuePropertyHandle.IsValid()) SelectedValuePropertyHandle->GetValue(Current);
	if (Current.IsEmpty() && Options.Num() > 0)
	{
		Current = Options[0];
		SelectedValuePropertyHandle->SetValue(Current);
	}

	TSharedPtr<TArray<TSharedPtr<FString>>> OptionsPtr = MakeShared<TArray<TSharedPtr<FString>>>();
	TSharedPtr<FString> InitiallySelected;
	for (const FString& V : Options)
	{
		TSharedPtr<FString> Item = MakeShared<FString>(V);
		if (!InitiallySelected.IsValid() && V == Current) InitiallySelected = Item;
		OptionsPtr->Add(Item);
	}

	return SNew(SHorizontalBox)
		+ SHorizontalBox::Slot()
		.AutoWidth()
		.MinWidth(200.f)
		[
			SNew(SComboBox<TSharedPtr<FString>>)
				.IsEnabled(IsEnabledAttr)
				.OptionsSource(OptionsPtr.Get())
				.InitiallySelectedItem(InitiallySelected)
				.OnGenerateWidget_Lambda([OptionsPtr](TSharedPtr<FString> Item)
					{
						return SNew(STextBlock).Text(FText::FromString(Item.IsValid() ? *Item : TEXT("")));
					})
				.OnSelectionChanged_Lambda([SelectedValuePropertyHandle, OptionsPtr](TSharedPtr<FString> NewSel, ESelectInfo::Type)
					{
						if (NewSel.IsValid()) SelectedValuePropertyHandle->SetValue(*NewSel);
					})
				[
					SNew(STextBlock)
						.Text_Lambda([SelectedValuePropertyHandle]()
							{
								FString V; SelectedValuePropertyHandle->GetValue(V);
								return FText::FromString(V.IsEmpty() ? TEXT("—") : V);
							})
						.Font(IDetailLayoutBuilder::GetDetailFont())
				]
		];
}

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreateCustomAttributeValueWidget(
	TSharedPtr<IPropertyHandle> AllOfPropertyHandle, 
	TSharedPtr<IPropertyHandle> AnyOfPropertyHandle,
	TAttribute<bool>& IsEnabledAttr
)
{
	auto GetArrayCount = [](const TSharedPtr<IPropertyHandle>& ArrHandle) -> uint32
		{
			uint32 Num = 0;
			if (ArrHandle.IsValid() && ArrHandle->AsArray().IsValid())
			{
				ArrHandle->AsArray()->GetNumElements(Num);
			}
			return Num;
		};

	enum class EMode { AllOf, AnyOf };

	TSharedPtr<EMode> CurrentMode = MakeShared<EMode>(
		(GetArrayCount(AnyOfPropertyHandle) > 0) ? EMode::AnyOf : EMode::AllOf
	);

	auto GetActiveMode = [CurrentMode]() -> EMode
	{
		return *CurrentMode;
	};

	auto ReadArrayAsStrings = [](const TSharedPtr<IPropertyHandle>& ArrHandle, TArray<FString>& Out)
		{
			Out.Reset();
			if (!ArrHandle.IsValid() || !ArrHandle->AsArray().IsValid()) return;

			uint32 Num = 0;
			ArrHandle->AsArray()->GetNumElements(Num);
			for (uint32 i = 0; i < Num; ++i)
			{
				TSharedPtr<IPropertyHandle> Elem = ArrHandle->AsArray()->GetElement(i);
				FString Val;
				if (Elem->GetValue(Val) == FPropertyAccess::Success)
				{
					Out.Add(Val);
				}
			}
		};

	auto WriteArrayFromStrings = [](const TSharedPtr<IPropertyHandle>& ArrHandle, const TArray<FString>& In)
		{
			if (!ArrHandle.IsValid() || !ArrHandle->AsArray().IsValid()) return;

			TSharedPtr<IPropertyHandleArray> Array = ArrHandle->AsArray();
			Array->EmptyArray();
			for (const FString& V : In)
			{
				uint32 Num = 0;
				Array->GetNumElements(Num);
				FPropertyHandleItemAddResult Res = ArrHandle->AsArray()->AddItem();

				TSharedPtr<IPropertyHandle> Elem = Array->GetElement(Num);
				if (Elem.IsValid())
				{
					Elem->SetValue(V);
				}
			}
		};

	auto MoveAll = [ReadArrayAsStrings, WriteArrayFromStrings](const TSharedPtr<IPropertyHandle>& From, const TSharedPtr<IPropertyHandle>& To)
		{
			if (!From.IsValid() || !To.IsValid()) return;

			TArray<FString> Buf;
			ReadArrayAsStrings(From, Buf);
			WriteArrayFromStrings(To, Buf);

			if (From->AsArray().IsValid())
			{
				From->AsArray()->EmptyArray();
			}
		};

	auto GetActiveArray = [AllOfPropertyHandle, AnyOfPropertyHandle, GetActiveMode]() -> TSharedPtr<IPropertyHandle>
		{
			return (GetActiveMode() == EMode::AllOf) ? AllOfPropertyHandle : AnyOfPropertyHandle;
		};

	auto GetInactiveArray = [AllOfPropertyHandle, AnyOfPropertyHandle, GetActiveMode]() -> TSharedPtr<IPropertyHandle>
		{
			return (GetActiveMode() == EMode::AllOf) ? AnyOfPropertyHandle : AllOfPropertyHandle;
		};


	return SNew(SHorizontalBox)
		+ SHorizontalBox::Slot()
		.AutoWidth()
		.VAlign(VAlign_Center)
		.Padding(0.f, 0.f, 8.f, 0.f)
		[
			SNew(SCheckBox)
				.IsEnabled(IsEnabledAttr)
				.IsChecked_Lambda([GetActiveMode]()
					{
						return GetActiveMode() == EMode::AllOf ? ECheckBoxState::Checked : ECheckBoxState::Unchecked;
					})
				.OnCheckStateChanged_Lambda([CurrentMode, AllOfPropertyHandle, AnyOfPropertyHandle, MoveAll](ECheckBoxState NewState)
					{
						if (NewState == ECheckBoxState::Checked)
						{
							*CurrentMode = EMode::AllOf;
							MoveAll(AnyOfPropertyHandle, AllOfPropertyHandle);
						}
					})
				[
					SNew(STextBlock).Text(FText::FromString(TEXT("AllOf")))
				]
		]

	+ SHorizontalBox::Slot()
		.AutoWidth()
		.VAlign(VAlign_Center)
		.Padding(0.f, 0.f, 8.f, 0.f)
		[
			SNew(SCheckBox)
				.IsEnabled(IsEnabledAttr)
				.IsChecked_Lambda([GetActiveMode]()
					{
						return GetActiveMode() == EMode::AnyOf ? ECheckBoxState::Checked : ECheckBoxState::Unchecked;
					})
				.OnCheckStateChanged_Lambda([CurrentMode, AllOfPropertyHandle, AnyOfPropertyHandle, MoveAll](ECheckBoxState NewState)
					{
						if (NewState == ECheckBoxState::Checked)
						{
							*CurrentMode = EMode::AnyOf;
							MoveAll(AllOfPropertyHandle, AnyOfPropertyHandle);
						}
					})
				[
					SNew(STextBlock).Text(FText::FromString(TEXT("AnyOf")))
				]
		]

	+ SHorizontalBox::Slot()
		.FillWidth(1.f)
		.VAlign(VAlign_Center)
		.HAlign(HAlign_Fill)
		[
			SNew(SEditableTextBox)
				.ToolTipText(LOCTEXT("CustomAttributeValueTooltip", "Space delimited items"))
				.IsEnabled(IsEnabledAttr)
				.Font(IDetailLayoutBuilder::GetDetailFont())
				.Text_Lambda([GetActiveArray, ReadArrayAsStrings]()
					{
						TArray<FString> Items;
						ReadArrayAsStrings(GetActiveArray(), Items);

						FString Combined;
						for (int32 i = 0; i < Items.Num(); ++i)
						{
							Combined += Items[i];
							if (i < Items.Num() - 1) Combined += TEXT(" ");
						}
						return FText::FromString(Combined);
					})
				.OnTextCommitted_Lambda([GetActiveArray, GetInactiveArray, WriteArrayFromStrings](const FText& NewText, ETextCommit::Type)
					{
						TArray<FString> Values;
						NewText.ToString().ParseIntoArrayWS(Values);

						for (int32 i = Values.Num() - 1; i >= 0; --i)
						{
							Values[i] = Values[i].TrimStartAndEnd();
							if (Values[i].IsEmpty())
							{
								Values.RemoveAt(i);
							}
						}

						WriteArrayFromStrings(GetActiveArray(), Values);

						const TSharedPtr<IPropertyHandle> Inactive = GetInactiveArray();
						if (Inactive.IsValid() && Inactive->AsArray().IsValid())
						{
							Inactive->AsArray()->EmptyArray();
						}
					})
		];
}

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::MakeBoundEditor(
	const FText& Label,
	const TSharedPtr<IPropertyHandle>& TypeHandle,
	const TSharedPtr<IPropertyHandle>& ValueHandle,
	bool bRequired,
	TAttribute<bool>& IsEnabledAttr,
	int32 MinInt,
	FText OptionalTooltip)
{
	TypeHandle->MarkHiddenByCustomization();

	TSharedRef<SWidget> ValueWidget = SNew(SIntSpinAsFloatOptional)
		.FloatHandle(ValueHandle)
		.TypeHandle(TypeHandle)
		.Required(bRequired)
		.MinInt(MinInt)
		.MaxInt(10000)
		.OptionalTooltip(OptionalTooltip);

	return  SNew(SHorizontalBox)
		+ SHorizontalBox::Slot()
		.AutoWidth()
		.Padding(2)
		.VAlign(VAlign_Center)
		[
			SNew(STextBlock)
				.Text(Label)
				.Font(IDetailLayoutBuilder::GetDetailFont())
		]
		+ SHorizontalBox::Slot()
		.AutoWidth()
		.Padding(2)
		.VAlign(VAlign_Center)
		[
			SNew(SBox)
				.IsEnabled(IsEnabledAttr)
				[
					ValueWidget
				]
		];
}

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreateAmountValueWidget(TSharedPtr<IPropertyHandle> RangeHandle, TAttribute<bool>& IsEnabledAttr)
{
	auto LowerBound = RangeHandle->GetChildHandle("LowerBound");
	auto UpperBound = RangeHandle->GetChildHandle("UpperBound");
	auto LowerType = LowerBound->GetChildHandle("Type");
	auto UpperType = UpperBound->GetChildHandle("Type");
	auto LowerValue = LowerBound->GetChildHandle("Value");
	auto UpperValue = UpperBound->GetChildHandle("Value");

	return SNew(SHorizontalBox)
		// Min
		+ SHorizontalBox::Slot()
		.AutoWidth()
		.Padding(2)
		[
			MakeBoundEditor(LOCTEXT("Min", "Min"), LowerType, LowerValue, true, IsEnabledAttr, 0)
		]

		// Max
		+ SHorizontalBox::Slot()
		.AutoWidth()
		.Padding(2)
		[
			MakeBoundEditor(LOCTEXT("Max", "Max"), UpperType, UpperValue, false, IsEnabledAttr, 0, LOCTEXT("Max tooltip", "0 means no Max"))
		];
}

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreateEyeUpdateWidget()
{
	TSharedRef<SEyeUpdateWidget> EyeUpdateWidget = SNew(SEyeUpdateWidget)
		.Visibility(EVisibility::Collapsed);
	return  EyeUpdateWidget;
}

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreatePathWidget(TSharedPtr<IPropertyHandle> ParameterHandle, FOnVerifyTextChanged Validation)
{
	return SNew(SDeadlineCloudFilePathWidget)
		.PathPropertyHandle(ParameterHandle)
		.IsValidInput(Validation)
		.BrowseButtonImage(FAppStyle::GetBrush("PropertyWindow.Button_Ellipsis"))
		.BrowseButtonStyle(FAppStyle::Get(), "HoverHintOnly")
		.BrowseButtonToolTip(LOCTEXT("FileButtonToolTipText", "Choose a file from this computer"))
		.BrowseDirectory(FEditorDirectories::Get().GetLastDirectory(ELastDirectory::GENERIC_OPEN))
		.BrowseTitle(LOCTEXT("PropertyEditorTitle", "File picker..."));
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

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreateStringWidget(TSharedPtr<IPropertyHandle> ParameterHandle, FOnVerifyTextChanged Validation, FText ToolTip)
{
	return SNew(SDeadlineCloudStringWidget)
		.StringPropertyHandle(ParameterHandle)
		.IsValidInput(Validation)
		.ToolTip(ToolTip);
}

UMoviePipelineDeadlineCloudExecutorJob* FDeadlineCloudDetailsWidgetsHelper::GetMrqJob(TSharedRef<IPropertyHandle> Handle)
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
	
	UMoviePipelineDeadlineCloudExecutorJob* MrqJob = Cast<UMoviePipelineDeadlineCloudExecutorJob>(OuterObject);
	if (MrqJob)
	{
		return MrqJob;
	}
	else return nullptr;
}




#undef LOCTEXT_NAMESPACE