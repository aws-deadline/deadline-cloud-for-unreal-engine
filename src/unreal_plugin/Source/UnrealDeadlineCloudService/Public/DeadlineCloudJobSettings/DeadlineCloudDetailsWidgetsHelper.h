// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once
#include "CoreMinimal.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJobPresetDetailsCustomization.h"

DECLARE_DELEGATE_RetVal_OneParam(FText, FIsValidInputSignature, const FText);

class DeadlineCloudJobPresetDetailsCustomization;

class FDeadlineCloudDetailsWidgetsHelper
{
public:

	static TSharedRef<SWidget> CreatePropertyWidgetByType(TSharedPtr<IPropertyHandle> ParameterHandle, EValueType Type, EValueValidationType ValidationType = EValueValidationType::Default);
	static TSharedPtr<SWidget> TryCreatePropertyWidgetFromMetadata(TSharedPtr<IPropertyHandle> ParameterHandle);
	static TSharedRef<SWidget> CreateNameWidget(FString Parameter);

	static TSharedRef<SWidget> CreateConsistencyWidget(FString ResultString);

	class SConsistencyWidget : public SCompoundWidget
	{
	public:
		SLATE_BEGIN_ARGS(SConsistencyWidget) {}
			SLATE_ARGUMENT(FString, CheckResult)
			SLATE_EVENT(FSimpleDelegate, OnFixButtonClicked)
		SLATE_END_ARGS()

		/** Construct */
		void Construct(const FArguments& InArgs);

	private:
		FSimpleDelegate OnFixButtonClicked;
		FReply HandleButtonClicked()
		{
			if (OnFixButtonClicked.IsBound())
			{
				OnFixButtonClicked.Execute();  // 
			}

			return FReply::Handled();
		}
	};

	class SEyeUpdateWidget : public SCompoundWidget
	{
	public:
		SLATE_BEGIN_ARGS(SEyeUpdateWidget)
			{}
			SLATE_EVENT(FSimpleDelegate, OnEyeUpdateButtonClicked)
		SLATE_END_ARGS()
		
		void Construct(const FArguments& InArgs);
	
	private:
		FText ButtonText;
		FSimpleDelegate OnEyeUpdateButtonClicked;

		
		FReply HandleButtonClicked()
		{
			if (OnEyeUpdateButtonClicked.IsBound())
			{
				OnEyeUpdateButtonClicked.Execute();
			}

			return FReply::Handled();
		}
		FText GetButtonText() const
		{
			return FText::FromString("Reset to default");

		}

	
	};

	class SEyeCheckBox : public SCompoundWidget
	{
	public:

		SLATE_BEGIN_ARGS(SEyeCheckBox) {}
		SLATE_END_ARGS()
	public:


		void Construct(const FArguments& InArgs, const FName& InPropertyPath_, const bool bIsChecked_, const bool bIsChangedByUser_)
		{
			InPropertyPath = InPropertyPath_;
			bIsChecked = bIsChecked_;
			bIsChangedByUser = bIsChangedByUser_;

			DynamicStyle = FAppStyle::Get().GetWidgetStyle<FCheckBoxStyle>("ToggleButtonCheckbox");

			FLinearColor TintColor = bIsChangedByUser
				? FLinearColor(1.f, 1.f, 0.f, 1.f) // w
				: FLinearColor::White; // y

			DynamicStyle.CheckedImage = *FAppStyle::Get().GetBrush("Icons.Visible");
			DynamicStyle.CheckedHoveredImage = *FAppStyle::Get().GetBrush("Icons.Hidden");
			DynamicStyle.CheckedPressedImage = *FAppStyle::Get().GetBrush("Icons.Hidden");
			DynamicStyle.UncheckedImage = *FAppStyle::Get().GetBrush("Icons.Hidden");
			DynamicStyle.UncheckedHoveredImage = *FAppStyle::Get().GetBrush("Icons.Visible");
			DynamicStyle.UncheckedPressedImage = *FAppStyle::Get().GetBrush("Icons.Visible");

			DynamicStyle.UncheckedImage.TintColor = FSlateColor(TintColor);
			DynamicStyle.CheckedImage.TintColor = FSlateColor(TintColor);
			DynamicStyle.CheckedHoveredImage.TintColor = FSlateColor(TintColor);
			DynamicStyle.CheckedPressedImage.TintColor = FSlateColor(TintColor);
			DynamicStyle.UncheckedHoveredImage.TintColor = FSlateColor(TintColor);
			DynamicStyle.UncheckedPressedImage.TintColor = FSlateColor(TintColor);
			
			ChildSlot
				[
					SNew(SBox)
						.Visibility(EVisibility::Visible)
						.HAlign(HAlign_Right)
						.WidthOverride(28)
						.HeightOverride(20)
						.Padding(4, 0)
						[
							SAssignNew(CheckBoxPtr, SCheckBox)
								.Style(&DynamicStyle)
								.IsChecked_Lambda([this]()
									{
										return bIsChecked ? ECheckBoxState::Checked  : ECheckBoxState::Unchecked;
										
									})

								.Visibility_Lambda([this]()
									{
										return CheckBoxPtr.IsValid() ? EVisibility::Visible : IsHovered() ? EVisibility::Visible : EVisibility::Hidden;
									})
									.ToolTipText(NSLOCTEXT("FDeadlineJobPresetLibraryCustomization", "VisibleInMoveRenderQueueToolTip", "If true this property will be visible for overriding from Movie Render Queue."))
										.OnCheckStateChanged(this, &SEyeCheckBox::HandleCheckStateChanged)
						]
				];
		}

		DECLARE_DELEGATE_OneParam(FOnCheckStateChangedDelegate, FName);
		
	
	void SetOnCheckStateChangedDelegate(FOnCheckStateChangedDelegate InDelegate)
	{
		OnCheckStateChangedDelegate = InDelegate;
	}
		TSharedPtr<SCheckBox> CheckBoxPtr;
		FCheckBoxStyle DynamicStyle;

	private:
		FOnCheckStateChangedDelegate OnCheckStateChangedDelegate;
		void HandleCheckStateChanged(ECheckBoxState NewState)
		{
			if (CheckBoxPtr.IsValid())
			{
				ECheckBoxState exp = CheckBoxPtr.Get()->GetCheckedState();
			}

			if (OnCheckStateChangedDelegate.IsBound())
			{
				OnCheckStateChangedDelegate.Execute(InPropertyPath);
			}
		}
		FName InPropertyPath;
		bool bIsChecked;
		bool bIsChangedByUser = false;

	};
	static TSharedRef<SWidget> CreateEyeUpdateWidget();
	
	/** Get the MoviePipelineDeadlineCloudExecutorJob from a property handle */
	static UMoviePipelineDeadlineCloudExecutorJob* GetMrqJob(TSharedRef<IPropertyHandle> Handle);
	
private:

	static TSharedRef<SWidget> CreatePathWidget(TSharedPtr<IPropertyHandle> ParameterHandle, FOnVerifyTextChanged Validation);
	static TSharedRef<SWidget> CreateIntWidget(TSharedPtr<IPropertyHandle> ParameterHandle);
	static TSharedRef<SWidget> CreateFloatWidget(TSharedPtr<IPropertyHandle> ParameterHandle);
	static TSharedRef<SWidget> CreateStringWidget(TSharedPtr<IPropertyHandle> ParameterHandle, FOnVerifyTextChanged Validation);
};