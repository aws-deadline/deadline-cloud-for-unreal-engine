// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "DeadlineCloudJobSettings/DeadlineCloudInputValidationHelper.h"
//#include "Internationalization/Regex.h"

#define LOCTEXT_NAMESPACE "DeadlineWidgets"


//TODO: Refactor this class to use OpenJD validators
//The best approach to validation is to create a wrapper around the OpenJD validators to avoid 
//code duplication and reduce the chance of errors. However, for now, private functions are used internally

FOnVerifyTextChanged FDeadlineCloudInputValidationHelper::GetStringValidationFunction(EValueValidationType ValidationType)
{
    switch (ValidationType)
    {
        using enum EValueValidationType;

    case EValueValidationType::JobName:
    {
        return FOnVerifyTextChanged::CreateLambda(
            [](const FText Input, FText& Error) -> bool
            {
                FString InputString = Input.ToString();
                if (!IsValidLength(InputString, 1, 64, Error))
                {
                    return false;
                }

				if (!IsValidIdentifier(InputString, Error))
				{
					return false;
				}

                return true;
            });
    }

    case EValueValidationType::JobDescription:
    {
        return FOnVerifyTextChanged::CreateLambda(
            [](const FText Input, FText& Error) -> bool
            {
                FString InputString = Input.ToString();
				if (!IsValidLength(InputString, 0, 2048, Error))
				{
					return false;
				}

                TSet<TCHAR> AllowedControls = { '\n', '\r', '\t' };
				if (!ContainsNoControlCharacters(InputString, Error, AllowedControls))
				{
					return false;
				}

                return true;
            });
    }

    case EValueValidationType::JobParameterValue:
    {
        return FOnVerifyTextChanged::CreateLambda(
            [](const FText Input, FText& Error) -> bool
            {
                FString InputString = Input.ToString();
                if (!IsValidLength(InputString, 0, 1024, Error))
                {
                    return false;
                }
                return true;
            });
    }

    case EValueValidationType::StepParameterValue:
    {
        return FOnVerifyTextChanged::CreateLambda(
            [](const FText Input, FText& Error) -> bool
            {
                FString InputString = Input.ToString();
                if (!IsValidLength(InputString, 1, 1024, Error))
                {
                    return false;
                }
                return true;
            });
    }

    case EValueValidationType::EnvParameterValue:
    {
        return FOnVerifyTextChanged::CreateLambda(
            [](const FText Input, FText& Error) -> bool
            {
                FString InputString = Input.ToString();
                if (!IsValidLength(InputString, 0, 2048, Error))
                {
                    return false;
                }
                return true;
            });
    }
    }
    return FOnVerifyTextChanged();
}

FOnVerifyTextChanged FDeadlineCloudInputValidationHelper::GetPathValidationFunction(EValueValidationType ValidationType)
{
    switch (ValidationType)
    {
        using enum EValueValidationType;
    case EValueValidationType::JobParameterValue:
    {
        return FOnVerifyTextChanged::CreateLambda(
            [](const FText Input, FText& Error) -> bool
            {
                FString InputString = Input.ToString();
                if (!IsValidLength(InputString, 1, 1024, Error))
                {
                    return false;
                }
                return true;
            });
    }

    case EValueValidationType::StepParameterValue:
    {
        return FOnVerifyTextChanged::CreateLambda(
            [](const FText Input, FText& Error) -> bool
            {
                FString InputString = Input.ToString();
                if (!IsValidLength(InputString, 1, 1024, Error))
                {
                    return false;
                }
                return true;
            });
    }
    }
    return FOnVerifyTextChanged();
}

bool FDeadlineCloudInputValidationHelper::IsValidLength(const FString& InStr, int32 Min, int32 Max)
{
    const int32 Length = InStr.Len();
    return Length >= Min && Length <= Max;
}

bool FDeadlineCloudInputValidationHelper::IsValidLength(const FString& InStr, int32 Min, int32 Max, FText& OutError, const FText& FieldName)
{
    if (!IsValidLength(InStr, Min, Max))
    {
        OutError = FText::Format(
            LOCTEXT("InvalidLength", "{0} length must be between {1} and {2} characters."),
            FieldName,
            FText::AsNumber(Min),
            FText::AsNumber(Max)
        );
        return false;
    }
    return true;
}

bool FDeadlineCloudInputValidationHelper::ContainsNoControlCharacters(const FString& InStr, const TSet<TCHAR>& ExcludeList)
{
    for (const TCHAR Ch : InStr)
    {
        if (FChar::IsControl(Ch))
        {
            return false;
        }
    }
    return true;
}

bool FDeadlineCloudInputValidationHelper::ContainsNoControlCharacters(const FString& InStr, FText& OutError, const TSet<TCHAR>& ExcludeList, const FText& FieldName)
{
    if (!ContainsNoControlCharacters(InStr, ExcludeList))
    {
        OutError = FText::Format(
            LOCTEXT("InvalidControlChars", "{0} contains invalid control characters."),
            FieldName
        );
        return false;
    }
    return true;
}

bool FDeadlineCloudInputValidationHelper::IsValidIdentifier(const FString& InStr)
{
    if (InStr.IsEmpty())
    {
        return false;
    }

    if (!(FChar::IsAlpha(InStr[0]) || InStr[0] == TEXT('_')))
    {
        return false;
    }

    for (const TCHAR Ch : InStr)
    {
        if (!(FChar::IsAlpha(Ch) || FChar::IsDigit(Ch) || Ch == TEXT('_')))
        {
            return false;
        }
    }

    return true;
}

bool FDeadlineCloudInputValidationHelper::IsValidIdentifier(const FString& InStr, FText& OutError, const FText& FieldName)
{
    if (!IsValidIdentifier(InStr))
    {
        OutError = FText::Format(
            LOCTEXT("InvalidIdentifier", "{0} must start with a letter or underscore and contain only Latin letters, digits, or underscores."),
            FieldName
        );
        return false;
    }
    return true;
}

#undef LOCTEXT_NAMESPACE