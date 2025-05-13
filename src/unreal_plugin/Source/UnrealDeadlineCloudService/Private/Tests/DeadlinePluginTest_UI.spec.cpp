// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once
#include "Misc/AutomationTest.h"
#include "CoreMinimal.h"
#include "Engine/Engine.h"
#include "UObject/UObjectGlobals.h"
#include "AssetToolsModule.h"
#include "Engine/AssetManager.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetRegistry/IAssetRegistry.h"
#include "Misc/Paths.h"
#include "Interfaces/IPluginManager.h"
#include "ObjectTools.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJob.h"
#include "DeadlineCloudJobSettings/DeadlineCloudStep.h"
#include "DeadlineCloudJobSettings/DeadlineCloudEnvironment.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "PythonAPILibraries/DeadlineCloudJobBundleLibrary.h"
#include "PythonAPILibraries/PythonParametersConsistencyChecker.h"
#include "DeadlineCloudJobSettings/DeadlineCloudInputValidationHelper.h"

#include "Tests/AutomationCommon.h"
#include "Subsystems/AssetEditorSubsystem.h"
#include "AutomationDriverTypeDefs.h"
#include "IAutomationDriver.h"
#include "IAutomationDriverModule.h"
#include "IDriverElement.h"
#include "IDriverSequence.h"
#include "LocateBy.h"

#include "PropertyEditorModule.h"
#include "IDetailsView.h"

#define TEST_TRUE(expression) \
	EPIC_TEST_BOOLEAN_(TEXT(#expression), expression, true)

#define TEST_FALSE(expression) \
	EPIC_TEST_BOOLEAN_(TEXT(#expression), expression, false)

#define TEST_EQUAL(expression, expected) \
	EPIC_TEST_BOOLEAN_(TEXT(#expression), expression, expected)

#define EPIC_TEST_BOOLEAN_(text, expression, expected) \
	TestEqual(text, expression, expected);


IMPLEMENT_SIMPLE_AUTOMATION_TEST(FIsValidLength_RangeOK, "DeadlineCloud.Validation.IsValidLength.RangeOK", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FIsValidLength_RangeOK::RunTest(const FString& Parameters)
{
    FText Error;
    FString Input = FString::ChrN(10, 'A');

    bool Result = FDeadlineCloudInputValidationHelper::IsValidLength(Input, 5, 15, Error);
    TestTrue("Length 10 in range 5-15", Result);
    TestTrue("Error should be empty", Error.IsEmpty());

    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FIsValidLength_TooShort, "DeadlineCloud.Validation.IsValidLength.TooShort", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FIsValidLength_TooShort::RunTest(const FString& Parameters)
{
    FText Error;
    FString Input = "Hi";

    bool Result = FDeadlineCloudInputValidationHelper::IsValidLength(Input, 3, 10, Error);
    TestFalse("Length 2 is too short", Result);
    TestFalse("Error should be set", Error.IsEmpty());

    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FContainsNoControlChars_Valid, "DeadlineCloud.Validation.ControlChars.Valid", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FContainsNoControlChars_Valid::RunTest(const FString& Parameters)
{
    FString Input = TEXT("Hello\nWorld\t!");
    TSet<TCHAR> Exclude = { '\n', '\t' };
    FText Error;

    bool Result = FDeadlineCloudInputValidationHelper::ContainsNoControlCharacters(Input, Error, Exclude);
    TestTrue("Allowed control characters", Result);
    TestTrue("Error should be empty", Error.IsEmpty());

    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FContainsNoControlChars_Invalid, "DeadlineCloud.Validation.ControlChars.Invalid", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FContainsNoControlChars_Invalid::RunTest(const FString& Parameters)
{
    FString Input;
    Input += TCHAR(1); // Control character
    FText Error;

    bool Result = FDeadlineCloudInputValidationHelper::ContainsNoControlCharacters(Input, Error, {});
    TestFalse("Disallowed control character", Result);
    TestFalse("Error should be set", Error.IsEmpty());

    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FValidIdentifier, "DeadlineCloud.Validation.Identifier.Valid", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FValidIdentifier::RunTest(const FString& Parameters)
{
    FText Error;
    FString Input = TEXT("_Valid123");

    bool Result = FDeadlineCloudInputValidationHelper::IsValidIdentifier(Input, Error);
    TestTrue("Valid identifier", Result);
    TestTrue("Error should be empty", Error.IsEmpty());

    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FInvalidIdentifier_StartsWithNumber, "DeadlineCloud.Validation.Identifier.InvalidStart", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FInvalidIdentifier_StartsWithNumber::RunTest(const FString& Parameters)
{
    FText Error;
    FString Input = TEXT("1Invalid");

    bool Result = FDeadlineCloudInputValidationHelper::IsValidIdentifier(Input, Error);
    TestFalse("Starts with number", Result);
    TestFalse("Error should be set", Error.IsEmpty());

    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FInvalidIdentifier_IllegalChar, "DeadlineCloud.Validation.Identifier.IllegalChar", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FInvalidIdentifier_IllegalChar::RunTest(const FString& Parameters)
{
    FText Error;
    FString Input = TEXT("Valid$Name");

    bool Result = FDeadlineCloudInputValidationHelper::IsValidIdentifier(Input, Error);
    TestFalse("Illegal character in identifier", Result);
    TestFalse("Error should be set", Error.IsEmpty());

    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FJobParameterValue_Valid, "DeadlineCloud.Validation.String.JobParam.Valid", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FJobParameterValue_Valid::RunTest(const FString& Parameters)
{
    const auto Validator = FDeadlineCloudInputValidationHelper::GetStringValidationFunction(EValueValidationType::JobParameterValue);

    FText Error;
    bool Result = Validator.Execute(FText::FromString("SomeValue"), Error);

    TestTrue("Valid JobParameterValue", Result);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FPathValidator_ValidStepParameter, "DeadlineCloud.Validation.Path.StepParam.Valid", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FPathValidator_ValidStepParameter::RunTest(const FString& Parameters)
{
    const auto Validator = FDeadlineCloudInputValidationHelper::GetPathValidationFunction(EValueValidationType::StepParameterValue);

    FText Error;
    bool Result = Validator.Execute(FText::FromString("C:/Temp/File.txt"), Error);

    TestTrue("Valid path", Result);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FInvalidLengthTest, "DeadlineCloud.Validation.InvalidLength", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FInvalidLengthTest::RunTest(const FString& Parameters)
{
    FText Error;
    // Too short (Min=1)
    TestFalse("Empty string should fail for Min=1", FDeadlineCloudInputValidationHelper::IsValidLength(TEXT(""), 1, 10, Error));
    
    // Too long
    TestFalse("Too long string should fail for Max=10", FDeadlineCloudInputValidationHelper::IsValidLength(TEXT("12345678901"), 1, 10, Error));

    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FInvalidIdentifierTest, "DeadlineCloud.Validation.InvalidIdentifier", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FInvalidIdentifierTest::RunTest(const FString& Parameters)
{
    FText Error;
    // Starts with a digit
    TestFalse("Identifier starting with digit should be invalid", FDeadlineCloudInputValidationHelper::IsValidIdentifier(TEXT("1abc"), Error));

    // Contains special characters
    TestFalse("Identifier with special chars should be invalid", FDeadlineCloudInputValidationHelper::IsValidIdentifier(TEXT("abc@def"), Error));

    // Empty
    TestFalse("Empty identifier should be invalid", FDeadlineCloudInputValidationHelper::IsValidIdentifier(TEXT(""), Error));

    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FControlCharacterTest, "DeadlineCloud.Validation.ControlCharacters", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FControlCharacterTest::RunTest(const FString& Parameters)
{
    FText Error;

    TSet<TCHAR> Allowed = { '\n', '\t' };

    // String with disallowed control char (e.g. ASCII 1)
    FString BadStr;
    BadStr.AppendChar(1); // SOH character

    TestFalse("String with disallowed control characters should fail", FDeadlineCloudInputValidationHelper::ContainsNoControlCharacters(BadStr, Error, Allowed));

    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FValidationFunction_JobName_Invalid, "DeadlineCloud.Validation.JobName.InvalidCases", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FValidationFunction_JobName_Invalid::RunTest(const FString& Parameters)
{
    FText Error;
    auto Validator = FDeadlineCloudInputValidationHelper::GetStringValidationFunction(EValueValidationType::JobName);

    // Too long
    FString TooLong = FString::ChrN(65, 'a');
    TestFalse("JobName too long", Validator.Execute(FText::FromString(TooLong), Error));

    // Invalid chars
    TestFalse("JobName with ! character should fail", Validator.Execute(FText::FromString("My!Job"), Error));

    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FValidationFunction_JobDescription_Invalid, "DeadlineCloud.Validation.JobDescription.ControlChar", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FValidationFunction_JobDescription_Invalid::RunTest(const FString& Parameters)
{
    FText Error;
    auto Validator = FDeadlineCloudInputValidationHelper::GetStringValidationFunction(EValueValidationType::JobDescription);

    FString BadDesc = TEXT("Hello");
    BadDesc.AppendChar(3); // ETX control character

    TestFalse("JobDescription with disallowed control character", Validator.Execute(FText::FromString(BadDesc), Error));

    return true;
}

static FString ConvertLocalPathToFull(const FString& Path)
{
	FString PluginContentDir = IPluginManager::Get().FindPlugin(TEXT("UnrealDeadlineCloudService"))->GetBaseDir();
	PluginContentDir = FPaths::ConvertRelativePathToFull(PluginContentDir);
	FString FullPath = FPaths::Combine(PluginContentDir, Path);
	FPaths::NormalizeDirectoryName(FullPath);
	return FullPath;
}

static void ExpandAllProperties(const FString DetailsPath, FAutomationDriverPtr Driver)
{
	FString MainCategoryExpanderArrowPath = DetailsPath + "//<SDetailCategoryTableRow>//<SDetailExpanderArrow>";
	FDriverElementCollectionRef ParametersCategory = Driver->FindElements(By::Path(MainCategoryExpanderArrowPath));
	ParametersCategory->GetElements()[0]->Click(EMouseButtons::Type::Right);
	Driver->Wait(FTimespan::FromSeconds(1));

	FString PopupElementsPath = "<SWindow>//<SPopup>//<SMultiBoxWidget>//<SBorder>//<SVerticalBox>//<SScrollBox>//<SHorizontalBox>//<SOverlay>//<SScrollPanel>//<SVerticalBox>//<SHorizontalBox>//<SMenuEntryButton>";

	FDriverElementCollectionRef PopupElements = Driver->FindElements(By::Path(PopupElementsPath));
	if (!PopupElements->GetElements().IsEmpty())
	{
		PopupElements->GetElements()[2]->Focus();
		PopupElements->GetElements()[2]->Click(EMouseButtons::Type::Left);
	}
}

static void ScrollToElement(FAutomationDriverPtr Driver, FDriverElementRef List, FDriverElementRef ScrollBar, FDriverElementRef TargetElement, uint32 AttemptsLimit)
{
	if (TargetElement->Exists() && TargetElement->IsVisible())
	{
		return;
	}

	if (List->Exists() && ScrollBar->Exists())
	{
		uint32 CurrentAttempts = 0;
		while ((!TargetElement->Exists() || !TargetElement->IsVisible()) && (!ScrollBar->IsScrolledToEnd() && CurrentAttempts < AttemptsLimit))
		{
			List->ScrollBy(-1);
			CurrentAttempts++;
		}
	}
}

template<typename AssetType>
AssetType* CreateAndOpenAsset(
    const FString& RelativeTemplatePath,
    FString& OutFullTemplatePath)
{
    OutFullTemplatePath = ConvertLocalPathToFull(RelativeTemplatePath);
    AssetType* Asset = NewObject<AssetType>();
    Asset->PathToTemplate.FilePath = OutFullTemplatePath;

    if constexpr (std::is_same_v<AssetType, UDeadlineCloudJob>)
    {
        Asset->OpenJobFile(OutFullTemplatePath);
    }
    else if constexpr (std::is_same_v<AssetType, UDeadlineCloudStep>)
    {
        Asset->OpenStepFile(OutFullTemplatePath);
    }
    else if constexpr (std::is_same_v<AssetType, UDeadlineCloudEnvironment>)
    {
        Asset->OpenEnvFile(OutFullTemplatePath);
    }

    auto* Editor = GEditor->GetEditorSubsystem<UAssetEditorSubsystem>();
    Editor->CloseAllAssetEditors();
    Editor->OpenEditorForAsset(Asset);
    return Asset;
}

static void InputText(FDriverElementRef Widget, const FString& Text, bool bRemoveTextBeforeInput)
{
	if (bRemoveTextBeforeInput)
	{
		Widget->TypeChord(EKeys::LeftControl, EKeys::A);
		Widget->Type(EKeys::Delete);
	}
	if (!Text.IsEmpty())
	{
		Widget->Type(Text);
	}
	Widget->Type(EKeys::Enter);
}



BEGIN_DEFINE_SPEC(FDeadlinePluginUISpec, "DeadlineCloud",
    EAutomationTestFlags::ProductFilter | EAutomationTestFlags::EditorContext | EAutomationTestFlags::NonNullRHI);

FAutomationDriverPtr Driver;
UDeadlineCloudStep* CreatedStepDataAsset;
UDeadlineCloudEnvironment* CreatedEnvironmentDataAsset;
UDeadlineCloudJob* CreatedJobDataAsset;
FParametersConsistencyCheckResult result;

FString PathToStepTemplate;
FString StepTemplate = "/Source/UnrealDeadlineCloudService/Private/Tests/openjd_templates/render_step_UI.yml";
FString PathToEnvironmentTemplate;
FString EnvTemplate = "/Source/UnrealDeadlineCloudService/Private/Tests/openjd_templates/launch_ue_environment_UI.yml";
FString PathToJobTemplate;
FString JobTemplate = "/Source/UnrealDeadlineCloudService/Private/Tests/openjd_templates/render_job_UI.yml";

const FString DetailsPath = "<SStandaloneAssetEditorToolkitHost>//<SDetailsView>";
const FString ListPath = DetailsPath + "//<SListPanel>";
const FString ScrollBarPath = DetailsPath + "//<SScrollBar>";

FDriverElementPtr Details;
FDriverElementPtr List;
FDriverElementPtr ScrollBar;

inline bool Init(UObject* Asset)
{
    if (!IsValid(Asset))
    {
        TestTrue(TEXT("Asset should exist"), false);
        return false;
    }
    // Locate Details View
    Details = Driver->FindElement(By::Path(DetailsPath));
    Driver->Wait(Until::ElementExists(Details.ToSharedRef(), FWaitTimeout::InSeconds(2.f)));
    if (!Details->Exists())
    {
        TestTrue(TEXT("Details view should exist"), false);
        return false;
    }
    Details->Focus();

    // Locate List and ScrollBar
    List = Driver->FindElement(By::Path(ListPath));
    if (!List->Exists())
    {
        TestTrue(TEXT("List widget should exist"), false);
        return false;
    }
    ScrollBar = Driver->FindElement(By::Path(ScrollBarPath));
    return true;
}

END_DEFINE_SPEC(FDeadlinePluginUISpec);

void FDeadlinePluginUISpec::Define()
{
	BeforeEach([this]() {
		if (IAutomationDriverModule::Get().IsEnabled())
		{
			IAutomationDriverModule::Get().Disable();
		}

		IAutomationDriverModule::Get().Enable();

		Driver = IAutomationDriverModule::Get().CreateDriver();
		});

    Describe("DeadlineCloudJobUI", [this]()
    {
		BeforeEach([this]() {
			CreatedJobDataAsset = CreateAndOpenAsset<UDeadlineCloudJob>(JobTemplate, PathToJobTemplate);
			});

		It("JobUI", EAsyncExecution::ThreadPool, [this]() {
			if (!Init(CreatedJobDataAsset))
			{
				return;
			}

			ExpandAllProperties(DetailsPath, Driver);

			FString JobNamePath = DetailsPath + "//#JobPreset.Name//<SEditableTextBox>";
			FString DescriptionPath = DetailsPath + "//#JobPreset.Description//<SEditableTextBox>";

			FString StringParametersPath = DetailsPath + "//#JobParameter.StringParameter//<SEditableTextBox>";
			FString PathParametersPath = DetailsPath + "//#JobParameter.PathParameter//<SEditableTextBox>";
			FString FloatParametersPath = DetailsPath + "//#JobParameter.FloatParameter//<SEditableText>";
			FString IntParametersPath = DetailsPath + "//#JobParameter.IntParameter//<SEditableText>";

			FDriverElementRef JobNameWidget = Driver->FindElement(By::Path(JobNamePath));
			FDriverElementRef DescriptionWidget = Driver->FindElement(By::Path(DescriptionPath));

			FDriverElementRef StringParametersWidget = Driver->FindElement(By::Path(StringParametersPath));
			FDriverElementRef PathParametersPathWidget = Driver->FindElement(By::Path(PathParametersPath));
			FDriverElementRef FloatParametersWidget = Driver->FindElement(By::Path(FloatParametersPath));
			FDriverElementRef IntParametersWidget = Driver->FindElement(By::Path(IntParametersPath));

			//JobName
			ScrollToElement(Driver, List.ToSharedRef(), ScrollBar.ToSharedRef(), JobNameWidget, 50);
			bool bJobNameWidgetExists = JobNameWidget->Exists();
			TestTrue("JobName widget should exist", bJobNameWidgetExists);
			if (bJobNameWidgetExists)
			{
				FString OldValue = CreatedJobDataAsset->JobPresetStruct.JobSharedSettings.Name;
				InputText(JobNameWidget, "123 Invalid", true);
				TEST_EQUAL(CreatedJobDataAsset->JobPresetStruct.JobSharedSettings.Name, OldValue);

				InputText(JobNameWidget, "", true);
				TEST_EQUAL(CreatedJobDataAsset->JobPresetStruct.JobSharedSettings.Name, OldValue);

				FString ValidJobName = "ValidJob123";
				InputText(JobNameWidget, ValidJobName, true);
				TEST_EQUAL(CreatedJobDataAsset->JobPresetStruct.JobSharedSettings.Name, ValidJobName);
			}

			//Description
			ScrollToElement(Driver, List.ToSharedRef(), ScrollBar.ToSharedRef(), DescriptionWidget, 50);
			bool bDescriptionWidgetExists = DescriptionWidget->Exists();
			TestTrue("Description widget should exist", bDescriptionWidgetExists);
			if (bDescriptionWidgetExists)
			{
				FString LongString;
				for (int i = 0; i < 2045; ++i) LongString += TEXT("A");

				CreatedJobDataAsset->JobPresetStruct.JobSharedSettings.Description = LongString;
				InputText(DescriptionWidget, "LongString", false);
				TEST_EQUAL(CreatedJobDataAsset->JobPresetStruct.JobSharedSettings.Description, LongString);

				FString ValidDescription = TEXT("This is a job description.");
				InputText(DescriptionWidget, ValidDescription, true);
				TEST_EQUAL(CreatedJobDataAsset->JobPresetStruct.JobSharedSettings.Description, ValidDescription);	
			}

			//PathParameter
			ScrollToElement(Driver, List.ToSharedRef(), ScrollBar.ToSharedRef(), StringParametersWidget, 50);
			bool bPathParametersWidgetExists = StringParametersWidget->Exists();
			TestTrue("StringParameters widget should exist", bPathParametersWidgetExists);
			if (bPathParametersWidgetExists)
			{
				FString PathParameterOldValue = CreatedJobDataAsset->ParameterDefinition.Parameters[0].Value;
				FString PathParametersText = "ThisInputIsWayTooLongForValidation";
				//Click on the widget to make it editable and remove text selection
				PathParametersPathWidget->Click(EMouseButtons::Type::Left);
				PathParametersPathWidget->Type(EKeys::Left);
				PathParametersPathWidget->Type(PathParametersText);
				PathParametersPathWidget->Type(EKeys::Enter);
				TEST_EQUAL(CreatedJobDataAsset->ParameterDefinition.Parameters[0].Value, PathParameterOldValue);

				InputText(PathParametersPathWidget, "", true);
				TEST_EQUAL(CreatedJobDataAsset->ParameterDefinition.Parameters[0].Value, "");

				FString PathParametersTextValid = "ValidString";
				InputText(PathParametersPathWidget, PathParametersTextValid, true);
				TEST_EQUAL(CreatedJobDataAsset->ParameterDefinition.Parameters[0].Value, PathParametersTextValid);							
			}

			//StringParameter
			ScrollToElement(Driver, List.ToSharedRef(), ScrollBar.ToSharedRef(), StringParametersWidget, 50);
			bool bStringParametersWidgetExists = StringParametersWidget->Exists();
			TestTrue("StringParameters widget should exist", bStringParametersWidgetExists);
			if (bStringParametersWidgetExists)
			{
				FString StringParameterOldValue = CreatedJobDataAsset->ParameterDefinition.Parameters[1].Value;
				InputText(StringParametersWidget, "ThisInputIsWayTooLongForValidation", false);
				TEST_EQUAL(CreatedJobDataAsset->ParameterDefinition.Parameters[1].Value, StringParameterOldValue);

				InputText(StringParametersWidget, "", true);
				TEST_EQUAL(CreatedJobDataAsset->ParameterDefinition.Parameters[1].Value, "");

				FString StringParametersTextValid = "ValidString";
				InputText(StringParametersWidget, StringParametersTextValid, true);
				TEST_EQUAL(CreatedJobDataAsset->ParameterDefinition.Parameters[1].Value, StringParametersTextValid);							
			}

			//FloatParameter
			ScrollToElement(Driver, List.ToSharedRef(), ScrollBar.ToSharedRef(), FloatParametersWidget, 50);
			bool bFloatParametersWidgetExists = FloatParametersWidget->Exists();
			TestTrue("FloatParameters widget should exist", bFloatParametersWidgetExists);
			if (bFloatParametersWidgetExists)
			{
				FString FloatParametersOldValue = CreatedJobDataAsset->ParameterDefinition.Parameters[2].Value;

				InputText(FloatParametersWidget, "InvalidValue", false);
				TEST_EQUAL(CreatedJobDataAsset->ParameterDefinition.Parameters[2].Value, FloatParametersOldValue);

				InputText(FloatParametersWidget, "", true);
				TEST_EQUAL(CreatedJobDataAsset->ParameterDefinition.Parameters[2].Value, FloatParametersOldValue);

				FString FloatParametersTextValid = "123.456";
				InputText(FloatParametersWidget, FloatParametersTextValid, true);
				TEST_EQUAL(CreatedJobDataAsset->ParameterDefinition.Parameters[2].Value, FloatParametersTextValid);							
			}

			//IntParameter
			ScrollToElement(Driver, List.ToSharedRef(), ScrollBar.ToSharedRef(), IntParametersWidget, 50);
			bool bIntParametersWidgetExists = IntParametersWidget->Exists();
			TestTrue("IntParameters widget should exist", bIntParametersWidgetExists);
			if (bIntParametersWidgetExists)
			{
				FString IntParametersOldValue = CreatedJobDataAsset->ParameterDefinition.Parameters[3].Value;

				InputText(IntParametersWidget, "InvalidValue", true);
				TEST_EQUAL(CreatedJobDataAsset->ParameterDefinition.Parameters[3].Value, IntParametersOldValue);

				InputText(IntParametersWidget, "", true);
				TEST_EQUAL(CreatedJobDataAsset->ParameterDefinition.Parameters[3].Value, IntParametersOldValue);

				FString IntParametersTextValid = "123";
				InputText(IntParametersWidget, IntParametersTextValid, true);
				TEST_EQUAL(CreatedJobDataAsset->ParameterDefinition.Parameters[3].Value, IntParametersTextValid);

				FString IntParametersTextInvalid = "123.456";
				InputText(IntParametersWidget, IntParametersTextInvalid, true);
				TEST_EQUAL(CreatedJobDataAsset->ParameterDefinition.Parameters[3].Value, IntParametersTextValid);							
			}		
			});

        AfterEach([this]()
            {
                CreatedJobDataAsset = nullptr;
            });
    });

    Describe("DeadlineCloudStepUI", [this]()
    {
		BeforeEach([this]() {
			CreatedStepDataAsset = CreateAndOpenAsset<UDeadlineCloudStep>(StepTemplate, PathToStepTemplate);
			});

		It("StepUI", EAsyncExecution::ThreadPool, [this]() {
			if (!Init(CreatedStepDataAsset))
			{
				return;
			}

			ExpandAllProperties(DetailsPath, Driver);

			FString StringParametersPath = DetailsPath + "//#StepParameter.StringParameters//<SEditableTextBox>";
			FString PathParametersPath = DetailsPath + "//#StepParameter.PathParameters//<SEditableTextBox>";
			FString FloatParametersPath = DetailsPath + "//#StepParameter.FloatParameters//<SEditableText>";
			FString IntParametersPath = DetailsPath + "//#StepParameter.IntParameters//<SEditableText>";

			FDriverElementRef StringParametersWidget = Driver->FindElement(By::Path(StringParametersPath));
			FDriverElementRef PathParametersPathWidget = Driver->FindElement(By::Path(PathParametersPath));
			FDriverElementRef FloatParametersWidget = Driver->FindElement(By::Path(FloatParametersPath));
			FDriverElementRef IntParametersWidget = Driver->FindElement(By::Path(IntParametersPath));

			//StringParameter
			ScrollToElement(Driver, List.ToSharedRef(), ScrollBar.ToSharedRef(), StringParametersWidget, 50);
			bool bStringParametersWidgetExists = StringParametersWidget->Exists();
			TestTrue("StringParameters widget should exist", bStringParametersWidgetExists);
			if (bStringParametersWidgetExists)
			{
				FStepTaskParameterDefinition StringParameter = CreatedStepDataAsset->TaskParameterDefinitions.Parameters[0];
				TEST_TRUE(StringParameter.Type == EValueType::STRING)
				FString StringParameterOldValue = StringParameter.Range[0];

				InputText(StringParametersWidget, "ThisInputIsWayTooLongForValidation", false);
				TEST_EQUAL(CreatedStepDataAsset->TaskParameterDefinitions.Parameters[0].Range[0], StringParameterOldValue);

				InputText(StringParametersWidget, "", true);
				TEST_EQUAL(CreatedStepDataAsset->TaskParameterDefinitions.Parameters[0].Range[0], StringParameterOldValue);

				FString StringParametersTextValid = "ValidString";
				InputText(StringParametersWidget, StringParametersTextValid, true);
				TEST_EQUAL(CreatedStepDataAsset->TaskParameterDefinitions.Parameters[0].Range[0], StringParametersTextValid);
			}

			//PathParameter
			ScrollToElement(Driver, List.ToSharedRef(), ScrollBar.ToSharedRef(), PathParametersPathWidget, 50);
			bool bPathParametersWidgetExists = PathParametersPathWidget->Exists();
			TestTrue("PathParameters widget should exist", bPathParametersWidgetExists);
			if (bPathParametersWidgetExists)
			{
				FStepTaskParameterDefinition PathParameter = CreatedStepDataAsset->TaskParameterDefinitions.Parameters[1];
				TEST_TRUE(PathParameter.Type == EValueType::PATH)

				FString PathParameterOldValue = PathParameter.Range[0];
				FString PathParametersText = "ThisInputIsWayTooLongForValidation";
				//Click on the widget to make it editable and remove text selection
				PathParametersPathWidget->Click(EMouseButtons::Type::Left);
				PathParametersPathWidget->Type(EKeys::Left);
				PathParametersPathWidget->Type(PathParametersText);
				PathParametersPathWidget->Type(EKeys::Enter);
				TEST_EQUAL(CreatedStepDataAsset->TaskParameterDefinitions.Parameters[1].Range[0], PathParameterOldValue);

				InputText(PathParametersPathWidget, "", true);
				TEST_EQUAL(CreatedStepDataAsset->TaskParameterDefinitions.Parameters[1].Range[0], PathParameterOldValue);

				FString PathParametersTextValid = "ValidString";
				InputText(PathParametersPathWidget, PathParametersTextValid, true);
				TEST_EQUAL(CreatedStepDataAsset->TaskParameterDefinitions.Parameters[1].Range[0], PathParametersTextValid);
			}

			//FloatParameter
			ScrollToElement(Driver, List.ToSharedRef(), ScrollBar.ToSharedRef(), FloatParametersWidget, 50);
			bool bFloatParametersWidgetExists = FloatParametersWidget->Exists();
			TestTrue("FloatParameters widget should exist", bFloatParametersWidgetExists);
			if (bFloatParametersWidgetExists)
			{
				FStepTaskParameterDefinition FloatParameter = CreatedStepDataAsset->TaskParameterDefinitions.Parameters[2];
				TEST_TRUE(FloatParameter.Type == EValueType::FLOAT)

				FString FloatParameterOldValue = FloatParameter.Range[0];
				InputText(FloatParametersWidget, "InvalidValue", false);
				TEST_EQUAL(CreatedStepDataAsset->TaskParameterDefinitions.Parameters[2].Range[0], FloatParameterOldValue);

				InputText(FloatParametersWidget, "", true);
				TEST_EQUAL(CreatedStepDataAsset->TaskParameterDefinitions.Parameters[2].Range[0], FloatParameterOldValue);

				FString FloatParametersTextValid = "123.456";
				InputText(FloatParametersWidget, FloatParametersTextValid, true);
				TEST_EQUAL(CreatedStepDataAsset->TaskParameterDefinitions.Parameters[2].Range[0], FloatParametersTextValid);
			}

			//IntParameter
			ScrollToElement(Driver, List.ToSharedRef(), ScrollBar.ToSharedRef(), IntParametersWidget, 50);
			bool bIntParametersWidgetExists = IntParametersWidget->Exists();
			TestTrue("IntParameters widget should exist", bIntParametersWidgetExists);
			if (bIntParametersWidgetExists)
			{
				FStepTaskParameterDefinition IntParameter = CreatedStepDataAsset->TaskParameterDefinitions.Parameters[3];
				TEST_TRUE(IntParameter.Type == EValueType::INT)

				FString IntParameterOldValue = IntParameter.Range[0];
				InputText(IntParametersWidget, "InvalidValue", false);
				TEST_EQUAL(CreatedStepDataAsset->TaskParameterDefinitions.Parameters[3].Range[0], IntParameterOldValue);

				InputText(IntParametersWidget, "", true);
				TEST_EQUAL(CreatedStepDataAsset->TaskParameterDefinitions.Parameters[3].Range[0], IntParameterOldValue);

				FString IntParametersTextValid = "123";
				InputText(IntParametersWidget, IntParametersTextValid, true);
				TEST_EQUAL(CreatedStepDataAsset->TaskParameterDefinitions.Parameters[3].Range[0], IntParametersTextValid);

				FString IntParametersTextInvalid = "123.456";
				InputText(IntParametersWidget, IntParametersTextInvalid, true);
				TEST_EQUAL(CreatedStepDataAsset->TaskParameterDefinitions.Parameters[3].Range[0], IntParametersTextValid);
			}
		});

        AfterEach([this]()
            {
                CreatedStepDataAsset = nullptr;
            });
    });

    Describe("DeadlineCloudEnvironmentUI", [this]()
    {
		BeforeEach([this]() {
			CreatedEnvironmentDataAsset = CreateAndOpenAsset<UDeadlineCloudEnvironment>(EnvTemplate, PathToEnvironmentTemplate);
			});

		It("EnvironmentUI", EAsyncExecution::ThreadPool, [this]() {
			if (!Init(CreatedEnvironmentDataAsset))
			{
				return;
			}

			ExpandAllProperties(DetailsPath, Driver);

			FString Variable1Path = DetailsPath + "//#EnvironmentParameter.Variable1//<SEditableTextBox>";
			FString Variable2Path = DetailsPath + "//#EnvironmentParameter.Variable2//<SEditableTextBox>";
			FString Variable3Path = DetailsPath + "//#EnvironmentParameter.Variable3//<SEditableTextBox>";

			FDriverElementRef Variable1Widget = Driver->FindElement(By::Path(Variable1Path));
			FDriverElementRef Variable2Widget = Driver->FindElement(By::Path(Variable2Path));
			FDriverElementRef Variable3Widget = Driver->FindElement(By::Path(Variable3Path));

			ScrollToElement(Driver, List.ToSharedRef(), ScrollBar.ToSharedRef(), Variable1Widget, 50);
			bool bVariable1WidgetExists = Variable1Widget->Exists();
			TestTrue("Variable1 widget should exist", bVariable1WidgetExists);
			if (bVariable1WidgetExists)
			{
				InputText(Variable1Widget, "", true);
				TEST_EQUAL(CreatedEnvironmentDataAsset->Variables.Variables["Variable1"], "");

				FString Variable1TextValid = "ValidString";
				InputText(Variable1Widget, Variable1TextValid, true);
				TEST_EQUAL(CreatedEnvironmentDataAsset->Variables.Variables["Variable1"], Variable1TextValid);
			}

			ScrollToElement(Driver, List.ToSharedRef(), ScrollBar.ToSharedRef(), Variable2Widget, 50);
			bool bVariable2WidgetExists = Variable2Widget->Exists();
			TestTrue("Variable2 widget should exist", bVariable2WidgetExists);
			if (bVariable2WidgetExists)
			{
				FString Variable2OldValue = CreatedEnvironmentDataAsset->Variables.Variables["Variable2"];
				InputText(Variable2Widget, "ThisInputIsWayTooLongForValidation", false);
				TEST_EQUAL(CreatedEnvironmentDataAsset->Variables.Variables["Variable2"], Variable2OldValue);
			}
		});

        AfterEach([this]()
			{
				CreatedEnvironmentDataAsset = nullptr;
		});
    });

	AfterEach([this]() {
		Driver.Reset();
		IAutomationDriverModule::Get().Disable();
		});
}

