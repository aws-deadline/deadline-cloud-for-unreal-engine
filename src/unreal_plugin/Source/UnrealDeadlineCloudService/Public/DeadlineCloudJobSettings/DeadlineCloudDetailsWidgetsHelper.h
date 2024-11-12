// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once
#include "CoreMinimal.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"

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
		SLATE_BEGIN_ARGS(SEyeUpdateWidget) {}
		//	SLATE_ARGUMENT(FString, Result)
			SLATE_EVENT(FSimpleDelegate, OnEyeUpdateButtonClicked)
		SLATE_END_ARGS()

		/** Construct */
		void Construct(const FArguments& InArgs);

	private:
		FSimpleDelegate OnEyeUpdateButtonClicked;
		FReply HandleButtonClicked()
		{
			if (OnEyeUpdateButtonClicked.IsBound())
			{
				OnEyeUpdateButtonClicked.Execute();  // 
			}

			return FReply::Handled();
		}
	};
	class SEyeCheckBox : public SCompoundWidget
	{
	public:
		SLATE_BEGIN_ARGS(SEyeCheckBox)
			: _InPropertyPath("DefaultName") {}
			SLATE_ARGUMENT(FName, InPropertyPath)
		//	SLATE_EVENT(FSimpleDelegate, OnCheckStateChangedDelegate)
		SLATE_END_ARGS()

		void Construct(const FArguments& InArgs)
		{
		//	OnCheckStateChangedDelegate = InArgs._OnCheckStateChangedDelegate;

			InPropertyPath = InArgs._InPropertyPath;
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
								.Visibility_Lambda([this]()
									{
										//return CheckBoxPtr.IsValid() && !CheckBoxPtr->IsChecked() ? EVisibility::Visible : IsHovered() ? EVisibility::Visible : EVisibility::Hidden;
										return CheckBoxPtr.IsValid() && IsHovered() ? EVisibility::Visible : EVisibility::Hidden;
									})
								.CheckedImage(FAppStyle::Get().GetBrush("Icons.Visible"))
										.CheckedHoveredImage(FAppStyle::Get().GetBrush("Icons.Visible"))
										.CheckedPressedImage(FAppStyle::Get().GetBrush("Icons.Visible"))
										.UncheckedImage(FAppStyle::Get().GetBrush("Icons.Hidden"))
										.UncheckedHoveredImage(FAppStyle::Get().GetBrush("Icons.Hidden"))
										.UncheckedPressedImage(FAppStyle::Get().GetBrush("Icons.Hidden"))
										.ToolTipText(NSLOCTEXT("FDeadlineJobPresetLibraryCustomization", "VisibleInMoveRenderQueueToolTip", "If true this property will be visible for overriding from Movie Render Queue."))

										.OnCheckStateChanged(this, &SEyeCheckBox::HandleCheckStateChanged)
										.IsChecked(ECheckBoxState::Unchecked) 
						]
				];
		}
		void SetOnCheckStateChangedDelegate(FSimpleDelegate InDelegate)
		{
			OnCheckStateChangedDelegate = InDelegate;
	}
		TSharedPtr<SCheckBox> CheckBoxPtr;
		FSimpleDelegate OnCheckStateChangedDelegate;
	private:

		void HandleCheckStateChanged(ECheckBoxState NewState)
		{
			// call to set state
			if (OnCheckStateChangedDelegate.IsBound())
			{
				OnCheckStateChangedDelegate.Execute();
			}
		}
		FName InPropertyPath;
	};


	static TSharedRef<SWidget> CreateEyeCheckBoxWidget(FName RsultString);
	static TSharedRef<SWidget> CreateEyeUpdateWidget();
	
private:

	static TSharedRef<SWidget> CreatePathWidget(TSharedPtr<IPropertyHandle> ParameterHandle);
	static TSharedRef<SWidget> CreateIntWidget(TSharedPtr<IPropertyHandle> ParameterHandle);
	static TSharedRef<SWidget> CreateFloatWidget(TSharedPtr<IPropertyHandle> ParameterHandle);
	static TSharedRef<SWidget> CreateStringWidget(TSharedPtr<IPropertyHandle> ParameterHandle);
};