#pragma once

#include "CoreMinimal.h"

#include "PythonAPILibraries/PythonYamlLibrary.h"

class FDeadlineCloudDetailsWidgetsHelper
{
public:

	static TSharedRef<SWidget> CreatePropertyWidgetByType(TSharedPtr<IPropertyHandle> ParameterHandle, EValueType Type);
	static TSharedRef<SWidget> CreateNameWidget(FString Parameter);
private:

	static TSharedRef<SWidget> CreatePathWidget(TSharedPtr<IPropertyHandle> ParameterHandle);
	static TSharedRef<SWidget> CreateIntWidget(TSharedPtr<IPropertyHandle> ParameterHandle);
	static TSharedRef<SWidget> CreateFloatWidget(TSharedPtr<IPropertyHandle> ParameterHandle);
	static TSharedRef<SWidget> CreateStringWidget(TSharedPtr<IPropertyHandle> ParameterHandle);
};