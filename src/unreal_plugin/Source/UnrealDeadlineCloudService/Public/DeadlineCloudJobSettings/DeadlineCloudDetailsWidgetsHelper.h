#pragma once

#include "CoreMinimal.h"

#include "PythonAPILibraries/PythonYamlLibrary.h"

class FDeadlineCloudDetailsWidgetsHelper
{
public:

	static TSharedRef<SWidget> CreatePropertyWidgetByType(TSharedPtr<IPropertyHandle> ParameterHandle, EValueType Type);
	static TSharedRef<SWidget> CreateNameWidget(FString Parameter);

	static TSharedRef<SWidget> CreateConsistencyWidget(FString ResultString);
	//class  SConsistencyWidget : public SCompoundWidget(FString f);
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
private:

	static TSharedRef<SWidget> CreatePathWidget(TSharedPtr<IPropertyHandle> ParameterHandle);
	static TSharedRef<SWidget> CreateIntWidget(TSharedPtr<IPropertyHandle> ParameterHandle);
	static TSharedRef<SWidget> CreateFloatWidget(TSharedPtr<IPropertyHandle> ParameterHandle);
	static TSharedRef<SWidget> CreateStringWidget(TSharedPtr<IPropertyHandle> ParameterHandle);
};