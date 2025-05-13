// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "DeadlineCloudJobSettings/DeadlineCloudInputValidationHelper.h"

#define LOCTEXT_NAMESPACE "DeadlineWidgets"


//TODO: Refactor this class to use OpenJD validators
//The best approach to validation is to create a wrapper around the OpenJD validators to avoid 
//code duplication and reduce the chance of errors. However, for now, private functions are used internally

static FOnVerifyTextChanged MakeValidator(FValidatorFunc Func)
{
    return FOnVerifyTextChanged::CreateLambda(
        [Func](const FText& Input, FText& Error) -> bool
        {
            const FString InputString = Input.ToString();
            return Func(InputString, Error);
        });
}

FValidatorFunc FDeadlineCloudInputValidationHelper::CreateLengthValidator(int32 Min, int32 Max)
{
    return [Min, Max](const FString& Str, FText& Error)
    {
        return IsValidLength(Str, Min, Max, Error);
    };
}

FValidatorFunc FDeadlineCloudInputValidationHelper::CreateLengthAndIdentifierValidator(int32 Min, int32 Max)
{
    return [Min, Max](const FString& Str, FText& Error)
    {
        return IsValidLength(Str, Min, Max, Error)
            && IsValidIdentifier(Str, Error);
    };
}

FValidatorFunc FDeadlineCloudInputValidationHelper::CreateLengthAndControlValidator(int32 Min, int32 Max, TSet<TCHAR> ExcludeList)
{
    return [Min, Max, ExcludeList](const FString& Str, FText& Error)
    {
        return IsValidLength(Str, Min, Max, Error)
            && ContainsNoControlCharacters(Str, Error, ExcludeList);
    };
}

FOnVerifyTextChanged FDeadlineCloudInputValidationHelper::GetStringValidationFunction(EValueValidationType ValidationType)
{
    using enum EValueValidationType;

    switch (ValidationType)
    {
    case JobName:
        return MakeValidator(CreateLengthAndIdentifierValidator(1, 64));

    case JobDescription:
        return MakeValidator(CreateLengthAndControlValidator(0, 2048, { '\n', '\r', '\t' }));

    case JobParameterValue:
        return MakeValidator(CreateLengthValidator(0, 1024));

    case StepParameterValue:
        return MakeValidator(CreateLengthValidator(1, 1024));

    case EnvParameterValue:
        return MakeValidator(CreateLengthValidator(0, 2048));

    default:
        return FOnVerifyTextChanged();
    }
}

FOnVerifyTextChanged FDeadlineCloudInputValidationHelper::GetPathValidationFunction(EValueValidationType ValidationType)
{
    using enum EValueValidationType;

    switch (ValidationType)
    {
    case JobParameterValue:
        return MakeValidator(CreateLengthValidator(0, 1024));

    case StepParameterValue:
        return MakeValidator(CreateLengthValidator(1, 1024));

    default:
        return FOnVerifyTextChanged();
    }
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
        if (FChar::IsControl(Ch) && !ExcludeList.Contains(Ch))
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