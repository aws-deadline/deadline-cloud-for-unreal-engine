// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once
#include "CoreMinimal.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJobPresetDetailsCustomization.h"

class DeadlineCloudJobPresetDetailsCustomization;

class FDeadlineCloudDetailsWidgetsHelper
{
public:

	static TSharedRef<SWidget> CreatePropertyWidgetByType(TSharedPtr<IPropertyHandle> ParameterHandle, EValueType Type);
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
			: _bShowHidden_() {}
			SLATE_ARGUMENT(bool, bShowHidden_)
			SLATE_EVENT(FSimpleDelegate, OnEyeUpdateButtonClicked)
		SLATE_END_ARGS()
		
		void Construct(const FArguments& InArgs);
	
	private:
		FText ButtonText;
		bool bShowHidden;
		FSimpleDelegate OnEyeUpdateButtonClicked;

		
		FReply HandleButtonClicked()
		{
			bShowHidden = !bShowHidden;

			if (OnEyeUpdateButtonClicked.IsBound())
			{
				OnEyeUpdateButtonClicked.Execute();
			}

			return FReply::Handled();
		}
		FText GetButtonText() const
		{
			return (bShowHidden) ? FText::FromString("Hide") : FText::FromString("Show");

		}

	
	};

	class SEyeCheckBox : public SCompoundWidget
	{
	public:

		SLATE_BEGIN_ARGS(SEyeCheckBox) {}
		SLATE_END_ARGS()
	public:


		void Construct(const FArguments& InArgs, const FName& InPropertyPath_, const bool bIsChecked_)
	
		{

			InPropertyPath = InPropertyPath_;
			bIsChecked = bIsChecked_;
			
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
								.Style(&FAppStyle::Get().GetWidgetStyle<FCheckBoxStyle>("ToggleButtonCheckbox"))
								.IsChecked_Lambda([this]()
									{
										return bIsChecked ? ECheckBoxState::Checked  : ECheckBoxState::Unchecked;
										
									})
								.Visibility_Lambda([this]()
									{
										return CheckBoxPtr.IsValid() ? EVisibility::Visible : IsHovered() ? EVisibility::Visible : EVisibility::Hidden;
									})
								.CheckedImage(FAppStyle::Get().GetBrush("Icons.Visible"))
										.CheckedHoveredImage(FAppStyle::Get().GetBrush("Icons.Hidden"))
										.CheckedPressedImage(FAppStyle::Get().GetBrush("Icons.Hidden"))
										.UncheckedImage(FAppStyle::Get().GetBrush("Icons.Hidden"))
										.UncheckedHoveredImage(FAppStyle::Get().GetBrush("Icons.Visible"))
										.UncheckedPressedImage(FAppStyle::Get().GetBrush("Icons.Visible"))
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

	};
	static TSharedRef<SWidget> CreateEyeUpdateWidget();
	
private:

	static TSharedRef<SWidget> CreatePathWidget(TSharedPtr<IPropertyHandle> ParameterHandle);
	static TSharedRef<SWidget> CreateIntWidget(TSharedPtr<IPropertyHandle> ParameterHandle);
	static TSharedRef<SWidget> CreateFloatWidget(TSharedPtr<IPropertyHandle> ParameterHandle);
	static TSharedRef<SWidget> CreateStringWidget(TSharedPtr<IPropertyHandle> ParameterHandle);
};