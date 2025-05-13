// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once
#include "CoreMinimal.h"
#include "DeadlineCloudJobSettings/DeadlineCloudDetailsWidgetsHelper.h"

using FValidatorFunc = TFunction<bool(const FString&, FText&)>;

class FDeadlineCloudInputValidationHelper
{
public:

    static FOnVerifyTextChanged GetStringValidationFunction(EValueValidationType ValidationType);
    static FOnVerifyTextChanged GetPathValidationFunction(EValueValidationType ValidationType);

    /** Basic length validation */
    static bool IsValidLength(const FString& InStr, int32 Min, int32 Max);

    /** Length validation with error reporting */
    static bool IsValidLength(const FString& InStr, int32 Min, int32 Max, FText& OutError, const FText& FieldName = FText::FromString(TEXT("Value")));

    /** Disallows Cc (control) characters (C0/C1 Unicode ranges) */
    static bool ContainsNoControlCharacters(const FString& InStr, const TSet<TCHAR>& ExcludeList);

    /** Disallows control characters and provides error message */
    static bool ContainsNoControlCharacters(const FString& InStr, FText& OutError,
        const TSet<TCHAR>& ExcludeList, const FText& FieldName = FText::FromString(TEXT("Value")));

    /** Validates identifier: starts with [A-Za-z_] and contains only [A-Za-z0-9_] */
    static bool IsValidIdentifier(const FString& InStr);

    /** Identifier with error message */
    static bool IsValidIdentifier(const FString& InStr, FText& OutError, const FText& FieldName = FText::FromString(TEXT("Identifier")));

private:

    static FValidatorFunc CreateLengthValidator(int32 Min, int32 Max);
    static FValidatorFunc CreateLengthAndIdentifierValidator(int32 Min, int32 Max);
    static FValidatorFunc CreateLengthAndControlValidator(int32 Min, int32 Max, TSet<TCHAR> ExcludeList);

};