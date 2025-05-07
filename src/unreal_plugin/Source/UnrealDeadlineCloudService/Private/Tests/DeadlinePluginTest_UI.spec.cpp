// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once
#include "Misc/AutomationTest.h"
#include "CoreMinimal.h"
#include "Engine/Engine.h"
#include "UObject/UObjectGlobals.h"
#include "AssetToolsModule.h"
#include "Runtime/Core/Public/Modules/ModuleManager.h"
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

#include "Misc/AutomationTest.h"
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

static void OpenEditorForAsset(UObject* Asset)
{
	UAssetEditorSubsystem* AssetEditor = GEditor->GetEditorSubsystem<UAssetEditorSubsystem>();
	AssetEditor->CloseAllAssetEditors();
	AssetEditor->OpenEditorForAsset(Asset);
}

static void ExpandAllProperties(FAutomationDriverPtr Driver)
{
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

BEGIN_DEFINE_SPEC(FDeadlinePluginUISpec, "DeadlineCloud",
    EAutomationTestFlags::ProductFilter | EAutomationTestFlags::EditorContext);

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

            BeforeEach([this]()
                {
                    if (!CreatedStepDataAsset)
                    {
						PathToJobTemplate = ConvertLocalPathToFull(JobTemplate);

                        CreatedJobDataAsset = NewObject<UDeadlineCloudJob>();
                        CreatedJobDataAsset->PathToTemplate.FilePath = PathToJobTemplate;
                        CreatedJobDataAsset->OpenJobFile(PathToJobTemplate);
                    }
                });

			BeforeEach([this]() {
					OpenEditorForAsset(CreatedJobDataAsset);
				});

			It("JobUI", EAsyncExecution::ThreadPool, [this]() {
				    FString DetailsPath = "<SStandaloneAssetEditorToolkitHost>//<SDetailsView>";
					FString ListPath = DetailsPath + "//<SListPanel>";
					FString ScrollBarPath = DetailsPath + "//<SScrollBar>";

				    FDriverElementRef Details = Driver->FindElement(By::Path(DetailsPath));
				    Driver->Wait(Until::ElementExists(Details, FWaitTimeout::InSeconds(2.f)));
				    Details->Focus();
					TEST_TRUE(Details->Exists());
					
					FDriverElementRef List = Driver->FindElement(By::Path(ListPath));
					TEST_TRUE(List->Exists());

					FDriverElementRef ScrollBar = Driver->FindElement(By::Path(ScrollBarPath));

					FString PathToTemplate = DetailsPath + "//#Job.PathToTemplate//<SEditableTextBox>";
					FDriverElementRef PathToTemplateWidget = Driver->FindElement(By::Path(PathToTemplate));
					FString CategoryPath = DetailsPath + "//<SDetailCategoryTableRow>";

					FString MainCategoryExpanderArrowPath = DetailsPath + "//<SDetailCategoryTableRow>//<SDetailExpanderArrow>";
					FDriverElementCollectionRef ParametersCategory = Driver->FindElements(By::Path(MainCategoryExpanderArrowPath));
					ParametersCategory->GetElements()[0]->Click(EMouseButtons::Type::Right);
					Driver->Wait(FTimespan::FromSeconds(1));

					ExpandAllProperties(Driver);

					Driver->Wait(Until::ElementExists(PathToTemplateWidget, FWaitTimeout::InSeconds(1.f)));

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
					ScrollToElement(Driver, List, ScrollBar, JobNameWidget, 50);
					TEST_TRUE(JobNameWidget->Exists()); //Indentifier
					FString OldValue = CreatedJobDataAsset->JobPresetStruct.JobSharedSettings.Name;
					FString InvalidJobName = "123 Invalid";
					JobNameWidget->TypeChord(EKeys::LeftControl, EKeys::A);
					JobNameWidget->Type(EKeys::Delete);
					JobNameWidget->Type(InvalidJobName);
					JobNameWidget->Type(EKeys::Enter);
					TEST_EQUAL(OldValue, CreatedJobDataAsset->JobPresetStruct.JobSharedSettings.Name);

					JobNameWidget->TypeChord(EKeys::LeftControl, EKeys::A);
					JobNameWidget->Type(EKeys::Delete);
					JobNameWidget->Type(EKeys::Enter);
					TEST_EQUAL(OldValue, CreatedJobDataAsset->JobPresetStruct.JobSharedSettings.Name);

					FString ValidJobName = "ValidJob123";
					JobNameWidget->TypeChord(EKeys::LeftControl, EKeys::A);
					JobNameWidget->Type(ValidJobName);
					JobNameWidget->Type(EKeys::Enter);
					TEST_EQUAL(ValidJobName, CreatedJobDataAsset->JobPresetStruct.JobSharedSettings.Name);

					//Description
					ScrollToElement(Driver, List, ScrollBar, DescriptionWidget, 50);

					FString LongString;
					for (int i = 0; i < 2045; ++i) LongString += TEXT("A");

					CreatedJobDataAsset->JobPresetStruct.JobSharedSettings.Description = LongString;
					FString String = "LongString";
					DescriptionWidget->Type(String);
					DescriptionWidget->Type(EKeys::Enter);
					TEST_EQUAL(LongString, CreatedJobDataAsset->JobPresetStruct.JobSharedSettings.Description);

					FString ValidDescription = TEXT("This is a job description.");
					DescriptionWidget->TypeChord(EKeys::LeftControl, EKeys::A);
					DescriptionWidget->Type(ValidDescription);
					DescriptionWidget->Type(EKeys::Enter);
					TEST_EQUAL(ValidDescription, CreatedJobDataAsset->JobPresetStruct.JobSharedSettings.Description);				

					//PathParameter
					ScrollToElement(Driver, List, ScrollBar, StringParametersWidget, 50);
					TEST_TRUE(PathParametersPathWidget->Exists());
					FString PathParametersText = "ThisInputIsWayTooLongForValidation";
					FString PathParameterOldValue = CreatedJobDataAsset->ParameterDefinition.Parameters[0].Value;
					//Click on the widget to make it editable and remove text selection
					PathParametersPathWidget->Click(EMouseButtons::Type::Left);
					PathParametersPathWidget->Type(EKeys::Left);
					PathParametersPathWidget->Type(PathParametersText);
					PathParametersPathWidget->Type(EKeys::Enter);
					TEST_EQUAL(PathParameterOldValue, CreatedJobDataAsset->ParameterDefinition.Parameters[0].Value);
					FString Empty;
					PathParametersPathWidget->TypeChord(EKeys::LeftControl, EKeys::A);
					PathParametersPathWidget->Type(EKeys::Delete);
					PathParametersPathWidget->Type(EKeys::Enter);
					TEST_EQUAL(Empty, CreatedJobDataAsset->ParameterDefinition.Parameters[0].Value);

					FString PathParametersTextValid = "ValidString";
					PathParametersPathWidget->TypeChord(EKeys::LeftControl, EKeys::A);
					PathParametersPathWidget->Type(PathParametersTextValid);
					PathParametersPathWidget->Type(EKeys::Enter);
					TEST_EQUAL(PathParametersTextValid, CreatedJobDataAsset->ParameterDefinition.Parameters[0].Value);

					//StringParameter
					ScrollToElement(Driver, List, ScrollBar, StringParametersWidget, 50);
					TEST_TRUE(StringParametersWidget->Exists());
					FString StringParametersText = "ThisInputIsWayTooLongForValidation";
					FString StringParameterOldValue = CreatedJobDataAsset->ParameterDefinition.Parameters[1].Value;
					TEST_TRUE(StringParametersWidget->Exists());
					StringParametersWidget->Type(StringParametersText);
					StringParametersWidget->Type(EKeys::Enter);
					TEST_EQUAL(StringParameterOldValue, CreatedJobDataAsset->ParameterDefinition.Parameters[1].Value);

					StringParametersWidget->TypeChord(EKeys::LeftControl, EKeys::A);
					StringParametersWidget->Type(EKeys::Delete);
					StringParametersWidget->Type(EKeys::Enter);
					TEST_EQUAL("", CreatedJobDataAsset->ParameterDefinition.Parameters[1].Value);

					FString StringParametersTextValid = "ValidString";
					StringParametersWidget->TypeChord(EKeys::LeftControl, EKeys::A);
					StringParametersWidget->Type(StringParametersTextValid);
					StringParametersWidget->Type(EKeys::Enter);
					TEST_EQUAL(StringParametersTextValid, CreatedJobDataAsset->ParameterDefinition.Parameters[1].Value);

					//FloatParameter
					ScrollToElement(Driver, List, ScrollBar, FloatParametersWidget, 50);
					TEST_TRUE(FloatParametersWidget->Exists());
					FString FloatParametersText = "InvalidValue";
					FString FloatParametersOldValue = CreatedJobDataAsset->ParameterDefinition.Parameters[2].Value;
					FloatParametersWidget->Type(FloatParametersText);
					FloatParametersWidget->Type(EKeys::Enter);
					TEST_EQUAL(FloatParametersOldValue, CreatedJobDataAsset->ParameterDefinition.Parameters[2].Value);

					FloatParametersWidget->TypeChord(EKeys::LeftControl, EKeys::A);
					FloatParametersWidget->Type(EKeys::Delete);
					FloatParametersWidget->Type(EKeys::Enter);
					TEST_EQUAL(FloatParametersOldValue, CreatedJobDataAsset->ParameterDefinition.Parameters[2].Value);

					FString FloatParametersTextValid = "123.456";
					FloatParametersWidget->Type(FloatParametersTextValid);
					FloatParametersWidget->Type(EKeys::Enter);
					TEST_EQUAL(FloatParametersTextValid, CreatedJobDataAsset->ParameterDefinition.Parameters[2].Value);

					//IntParameter
					ScrollToElement(Driver, List, ScrollBar, IntParametersWidget, 50);
					TEST_TRUE(IntParametersWidget->Exists());
					FString IntParametersText = "InvalidValue";
					FString IntParametersOldValue = CreatedJobDataAsset->ParameterDefinition.Parameters[3].Value;
					IntParametersWidget->Type(IntParametersText);
					IntParametersWidget->Type(EKeys::Enter);
					TEST_EQUAL(IntParametersOldValue, CreatedJobDataAsset->ParameterDefinition.Parameters[3].Value);

					IntParametersWidget->TypeChord(EKeys::LeftControl, EKeys::A);
					IntParametersWidget->Type(EKeys::Delete);
					IntParametersWidget->Type(EKeys::Enter);
					TEST_EQUAL(IntParametersOldValue, CreatedJobDataAsset->ParameterDefinition.Parameters[3].Value);

					FString IntParametersTextValid = "123";
					IntParametersWidget->TypeChord(EKeys::LeftControl, EKeys::A);
					IntParametersWidget->Type(EKeys::Delete);
					IntParametersWidget->Type(IntParametersTextValid);
					IntParametersWidget->Type(EKeys::Enter);
					TEST_EQUAL(IntParametersTextValid, CreatedJobDataAsset->ParameterDefinition.Parameters[3].Value);

					FString IntParametersTextInvalid = "123.456";
					IntParametersWidget->TypeChord(EKeys::LeftControl, EKeys::A);
					IntParametersWidget->Type(EKeys::Delete);
					IntParametersWidget->Type(IntParametersTextInvalid);
					IntParametersWidget->Type(EKeys::Enter);
					TEST_EQUAL(IntParametersTextValid, CreatedJobDataAsset->ParameterDefinition.Parameters[3].Value);
				});

            AfterEach([this]()
                {
                    CreatedStepDataAsset = nullptr;
                });
        });

    Describe("DeadlineCloudStepUI", [this]()
        {

            BeforeEach([this]()
                {
                    if (!CreatedStepDataAsset)
                    {
						PathToStepTemplate = ConvertLocalPathToFull(StepTemplate);

                        CreatedStepDataAsset = NewObject<UDeadlineCloudStep>();
                        CreatedStepDataAsset->PathToTemplate.FilePath = PathToStepTemplate;
                        CreatedStepDataAsset->OpenStepFile(PathToStepTemplate);
                    }
                });

			BeforeEach([this]() {
					OpenEditorForAsset(CreatedStepDataAsset);
				});

			It("StepUI", EAsyncExecution::ThreadPool, [this]() {
				    FString DetailsPath = "<SStandaloneAssetEditorToolkitHost>//<SDetailsView>";
					FString ListPath = DetailsPath + "//<SListPanel>";
					FString ScrollBarPath = DetailsPath + "//<SScrollBar>";

				    FDriverElementRef Details = Driver->FindElement(By::Path(DetailsPath));
				    Driver->Wait(Until::ElementExists(Details, FWaitTimeout::InSeconds(2.f)));
				    Details->Focus();
					TEST_TRUE(Details->Exists());
					
					FDriverElementRef List = Driver->FindElement(By::Path(ListPath));
					TEST_TRUE(List->Exists());

					FDriverElementRef ScrollBar = Driver->FindElement(By::Path(ScrollBarPath));

					FString PathToTemplate = DetailsPath + "//#Step.PathToTemplate//<SEditableTextBox>";
					FDriverElementRef PathToTemplateWidget = Driver->FindElement(By::Path(PathToTemplate));
					FString CategoryPath = DetailsPath + "//<SDetailCategoryTableRow>";

					FString MainCategoryExpanderArrowPath = DetailsPath + "//<SDetailCategoryTableRow>//<SDetailExpanderArrow>";
					FDriverElementCollectionRef ParametersCategory = Driver->FindElements(By::Path(MainCategoryExpanderArrowPath));
					ParametersCategory->GetElements()[0]->Click(EMouseButtons::Type::Right);
					Driver->Wait(FTimespan::FromSeconds(1));

					ExpandAllProperties(Driver);

					Driver->Wait(Until::ElementExists(PathToTemplateWidget, FWaitTimeout::InSeconds(1.f)));

					FString StringParametersPath = DetailsPath + "//#StepParameter.StringParameters//<SEditableTextBox>";
					FString PathParametersPath = DetailsPath + "//#StepParameter.PathParameters//<SEditableTextBox>";
					FString FloatParametersPath = DetailsPath + "//#StepParameter.FloatParameters//<SEditableText>";
					FString IntParametersPath = DetailsPath + "//#StepParameter.IntParameters//<SEditableText>";

					FDriverElementRef StringParametersWidget = Driver->FindElement(By::Path(StringParametersPath));
					FDriverElementRef PathParametersPathWidget = Driver->FindElement(By::Path(PathParametersPath));
					FDriverElementRef FloatParametersWidget = Driver->FindElement(By::Path(FloatParametersPath));
					FDriverElementRef IntParametersWidget = Driver->FindElement(By::Path(IntParametersPath));

					//StringParameter
					ScrollToElement(Driver, List, ScrollBar, StringParametersWidget, 50);
					TEST_TRUE(StringParametersWidget->Exists());

					FStepTaskParameterDefinition StringParameter = CreatedStepDataAsset->TaskParameterDefinitions.Parameters[0];
					TEST_TRUE(StringParameter.Type == EValueType::STRING)
					FString StringParameterOldValue = StringParameter.Range[0];
					TEST_TRUE(StringParametersWidget->Exists());
					FString StringParametersText = "ThisInputIsWayTooLongForValidation";
					StringParametersWidget->Type(StringParametersText);	
					StringParametersWidget->Type(EKeys::Enter);
					TEST_EQUAL(StringParameterOldValue, CreatedStepDataAsset->TaskParameterDefinitions.Parameters[0].Range[0]);

					StringParametersWidget->TypeChord(EKeys::LeftControl, EKeys::A);
					StringParametersWidget->Type(EKeys::Delete);
					StringParametersWidget->Type(EKeys::Enter);

					TEST_EQUAL(StringParameterOldValue, CreatedStepDataAsset->TaskParameterDefinitions.Parameters[0].Range[0]);

					FString StringParametersTextValid = "ValidString";
					StringParametersWidget->TypeChord(EKeys::LeftControl, EKeys::A);
					StringParametersWidget->Type(EKeys::Delete);
					StringParametersWidget->Type(StringParametersTextValid);
					StringParametersWidget->Type(EKeys::Enter);
					TEST_EQUAL(StringParametersTextValid, CreatedStepDataAsset->TaskParameterDefinitions.Parameters[0].Range[0]);

					//PathParameter
					ScrollToElement(Driver, List, ScrollBar, PathParametersPathWidget, 50);

					TEST_TRUE(PathParametersPathWidget->Exists());
					FString PathParametersText = "ThisInputIsWayTooLongForValidation";
					FString PathParametersOldValue = CreatedStepDataAsset->TaskParameterDefinitions.Parameters[1].Range[0];
					TEST_TRUE(PathParametersPathWidget->Exists());
					//Click on the widget to make it editable and remove text selection
					PathParametersPathWidget->Click(EMouseButtons::Type::Left);
					PathParametersPathWidget->Type(EKeys::Left);
					PathParametersPathWidget->Type(PathParametersText);
					PathParametersPathWidget->Type(EKeys::Enter);
					TEST_EQUAL(PathParametersOldValue, CreatedStepDataAsset->TaskParameterDefinitions.Parameters[1].Range[0]);

					PathParametersPathWidget->TypeChord(EKeys::LeftControl, EKeys::A);
					PathParametersPathWidget->Type(EKeys::Delete);
					PathParametersPathWidget->Type(EKeys::Enter);
					TEST_EQUAL(PathParametersOldValue, CreatedStepDataAsset->TaskParameterDefinitions.Parameters[1].Range[0]);

					FString PathParametersTextValid = "ValidString";
					PathParametersPathWidget->TypeChord(EKeys::LeftControl, EKeys::A);
					PathParametersPathWidget->Type(PathParametersTextValid);
					PathParametersPathWidget->Type(EKeys::Enter);
					TEST_EQUAL(PathParametersTextValid, CreatedStepDataAsset->TaskParameterDefinitions.Parameters[1].Range[0]);

					//FloatParameter
					ScrollToElement(Driver, List, ScrollBar, FloatParametersWidget, 50);

					TEST_TRUE(FloatParametersWidget->Exists());
					FString FloatParametersText = "InvalidValue";
					FString FloatParametersOldValue = CreatedStepDataAsset->TaskParameterDefinitions.Parameters[2].Range[0];
					TEST_TRUE(FloatParametersWidget->Exists());
					FloatParametersWidget->Type(FloatParametersText);
					FloatParametersWidget->Type(EKeys::Enter);
					TEST_EQUAL(FloatParametersOldValue, CreatedStepDataAsset->TaskParameterDefinitions.Parameters[2].Range[0]);

					FloatParametersWidget->TypeChord(EKeys::LeftControl, EKeys::A);
					FloatParametersWidget->Type(EKeys::Delete);
					FloatParametersWidget->Type(EKeys::Enter);
					TEST_EQUAL(FloatParametersOldValue, CreatedStepDataAsset->TaskParameterDefinitions.Parameters[2].Range[0]);

					FString FloatParametersTextValid = "123.456";
					FloatParametersWidget->Type(FloatParametersTextValid);
					FloatParametersWidget->Type(EKeys::Enter);
					TEST_EQUAL(FloatParametersTextValid, CreatedStepDataAsset->TaskParameterDefinitions.Parameters[2].Range[0]);

					//IntParameter
					ScrollToElement(Driver, List, ScrollBar, IntParametersWidget, 50);

					TEST_TRUE(IntParametersWidget->Exists());
					FString IntParametersText = "InvalidValue";
					FString IntParametersOldValue = CreatedStepDataAsset->TaskParameterDefinitions.Parameters[3].Range[0];
					IntParametersWidget->Type(IntParametersText);
					IntParametersWidget->Type(EKeys::Enter);
					TEST_EQUAL(IntParametersOldValue, CreatedStepDataAsset->TaskParameterDefinitions.Parameters[3].Range[0]);

					IntParametersWidget->TypeChord(EKeys::LeftControl, EKeys::A);
					IntParametersWidget->Type(EKeys::Delete);
					IntParametersWidget->Type(EKeys::Enter);
					TEST_EQUAL(IntParametersOldValue, CreatedStepDataAsset->TaskParameterDefinitions.Parameters[3].Range[0]);

					FString IntParametersTextValid = "123";
					IntParametersWidget->TypeChord(EKeys::LeftControl, EKeys::A);
					IntParametersWidget->Type(EKeys::Delete);
					IntParametersWidget->Type(IntParametersTextValid);
					IntParametersWidget->Type(EKeys::Enter);
					TEST_EQUAL(IntParametersTextValid, CreatedStepDataAsset->TaskParameterDefinitions.Parameters[3].Range[0]);
					
					FString IntParametersTextInvalid = "123.456";
					IntParametersWidget->TypeChord(EKeys::LeftControl, EKeys::A);
					IntParametersWidget->Type(EKeys::Delete);
					IntParametersWidget->Type(IntParametersTextInvalid);
					IntParametersWidget->Type(EKeys::Enter);
					TEST_EQUAL(IntParametersTextValid, CreatedStepDataAsset->TaskParameterDefinitions.Parameters[3].Range[0]);

				});

            AfterEach([this]()
                {
                    CreatedStepDataAsset = nullptr;
                });
        });


    Describe("DeadlineCloudEnvironmentUI", [this]()
        {

            BeforeEach([this]()
                {
                    if (!CreatedStepDataAsset)
                    {
						PathToEnvironmentTemplate = ConvertLocalPathToFull(EnvTemplate);

                        CreatedEnvironmentDataAsset = NewObject<UDeadlineCloudEnvironment>();
						CreatedEnvironmentDataAsset->PathToTemplate.FilePath = PathToEnvironmentTemplate;
						CreatedEnvironmentDataAsset->OpenEnvFile(CreatedEnvironmentDataAsset->PathToTemplate.FilePath);
                    }
                });

			BeforeEach([this]() {
					OpenEditorForAsset(CreatedEnvironmentDataAsset);
				});

			It("EnvironmentUI", EAsyncExecution::ThreadPool, [this]() {
				    FString DetailsPath = "<SStandaloneAssetEditorToolkitHost>//<SDetailsView>";
					FString ListPath = DetailsPath + "//<SListPanel>";
					FString ScrollBarPath = DetailsPath + "//<SScrollBar>";

				    FDriverElementRef Details = Driver->FindElement(By::Path(DetailsPath));
				    Driver->Wait(Until::ElementExists(Details, FWaitTimeout::InSeconds(2.f)));
				    Details->Focus();
					TEST_TRUE(Details->Exists());
					
					FDriverElementRef List = Driver->FindElement(By::Path(ListPath));
					TEST_TRUE(List->Exists());

					FDriverElementRef ScrollBar = Driver->FindElement(By::Path(ScrollBarPath));

					FString PathToTemplate = DetailsPath + "//#Environment.PathToTemplate//<SEditableTextBox>";
					FDriverElementRef PathToTemplateWidget = Driver->FindElement(By::Path(PathToTemplate));
					FString CategoryPath = DetailsPath + "//<SDetailCategoryTableRow>";

					FString MainCategoryExpanderArrowPath = DetailsPath + "//<SDetailCategoryTableRow>//<SDetailExpanderArrow>";
					FDriverElementCollectionRef ParametersCategory = Driver->FindElements(By::Path(MainCategoryExpanderArrowPath));
					ParametersCategory->GetElements()[0]->Click(EMouseButtons::Type::Right);
					Driver->Wait(FTimespan::FromSeconds(1));

					ExpandAllProperties(Driver);

					Driver->Wait(Until::ElementExists(PathToTemplateWidget, FWaitTimeout::InSeconds(1.f)));

					TEST_TRUE(PathToTemplateWidget->Exists());
					TEST_TRUE(PathToTemplateWidget->IsVisible());

					ParametersCategory->GetElements()[0]->Click(EMouseButtons::Type::Right);
					Driver->Wait(FTimespan::FromSeconds(1));

					ExpandAllProperties(Driver);

					FString Variable1Path = DetailsPath + "//#EnvironmentParameter.Variable1//<SEditableTextBox>";
					FString Variable2Path = DetailsPath + "//#EnvironmentParameter.Variable2//<SEditableTextBox>";
					FString Variable3Path = DetailsPath + "//#EnvironmentParameter.Variable3//<SEditableTextBox>";

					FString Variable2ErrorPath = Variable2Path + "//<SPopupErrorText>";

					FDriverElementRef Variable1Widget = Driver->FindElement(By::Path(Variable1Path));
					FDriverElementRef Variable2Widget = Driver->FindElement(By::Path(Variable2Path));
					FDriverElementRef Variable3Widget = Driver->FindElement(By::Path(Variable3Path));

					FDriverElementRef Variable2ErrorWidget = Driver->FindElement(By::Path(Variable2ErrorPath));

					ScrollToElement(Driver, List, ScrollBar, Variable1Widget, 50);

					TEST_TRUE(Variable1Widget->Exists());
					FString Variable1Text = "ValidString";
					Variable1Widget->TypeChord(EKeys::LeftControl, EKeys::A);
					Variable1Widget->Type(Variable1Text);
					Variable1Widget->Type(EKeys::Enter);
					TEST_EQUAL(Variable1Text, CreatedEnvironmentDataAsset->Variables.Variables["Variable1"]);

					ScrollToElement(Driver, List, ScrollBar, Variable2Widget, 50);

					FString Variable2OldValue = CreatedEnvironmentDataAsset->Variables.Variables["Variable2"];
					TEST_TRUE(Variable2Widget->Exists());
					FString Variable2Text = "ThisInputIsWayTooLongForValidation";
					Variable2Widget->Type(Variable2Text);
					TEST_TRUE(Variable2ErrorWidget->IsVisible());		
					Variable2Widget->Type(EKeys::Enter);

					TEST_EQUAL(Variable2OldValue, CreatedEnvironmentDataAsset->Variables.Variables["Variable2"]);
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

