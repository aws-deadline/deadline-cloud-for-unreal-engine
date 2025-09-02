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
#include "DeadlineCloudJobSettings/DeadlineCloudRenderJob.h"
#include "DeadlineCloudJobSettings/DeadlineCloudStep.h"
#include "DeadlineCloudJobSettings/DeadlineCloudEnvironment.h"
#include "MovieRenderPipeline/MoviePipelineDeadlineCloudExecutorJob.h"
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

#include "MoviePipelineQueueSubsystem.h"

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
AssetType* CreateAsset(
	const FString& RelativeTemplatePath,
	FString& OutFullTemplatePath
	)
{
    OutFullTemplatePath = ConvertLocalPathToFull(RelativeTemplatePath);
    AssetType* Asset = NewObject<AssetType>();
    Asset->PathToTemplate.FilePath = OutFullTemplatePath;

    if constexpr (std::is_same_v<AssetType, UDeadlineCloudRenderJob>)
    {
        Asset->OpenJobFile(OutFullTemplatePath);
    }
    else if constexpr (std::is_same_v<AssetType, UDeadlineCloudJob>)
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
	return Asset;
}

template<typename AssetType>
AssetType* CreateAndOpenAsset(
    const FString& RelativeTemplatePath,
    FString& OutFullTemplatePath)
{
	AssetType* Asset = CreateAsset<AssetType>(RelativeTemplatePath, OutFullTemplatePath);

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
UDeadlineCloudRenderJob* CreatedRenderJobDataAsset;
UMoviePipelineDeadlineCloudExecutorJob* MRQJob;
FParametersConsistencyCheckResult result;

UDeadlineCloudStep* CreatedEmptyStepDataAsset;
UDeadlineCloudEnvironment* CreatedEmptyEnvironmentDataAsset;

FString PathToStepTemplate;
FString StepTemplate = "/Source/UnrealDeadlineCloudService/Private/Tests/openjd_templates/render_step_UI.yml";
FString PathToEnvironmentTemplate;
FString EnvTemplate = "/Source/UnrealDeadlineCloudService/Private/Tests/openjd_templates/launch_ue_environment_UI.yml";
FString PathToEmptyStepTemplate;
FString EmptyStepTemplate = "/Source/UnrealDeadlineCloudService/Private/Tests/openjd_templates/render_step_UI_empty.yml";
FString PathToEmptyEnvironmentTemplate;
FString EmptyEnvTemplate = "/Source/UnrealDeadlineCloudService/Private/Tests/openjd_templates/launch_ue_environment_UI_empty.yml";
FString PathToJobTemplate;
FString JobTemplate = "/Source/UnrealDeadlineCloudService/Private/Tests/openjd_templates/render_job_UI.yml";

const FString DetailsPath = "<SStandaloneAssetEditorToolkitHost>//<SDetailsView>";
const FString ListPath = DetailsPath + "//<SListPanel>";
const FString ScrollBarPath = DetailsPath + "//<SScrollBar>";

const FString MRQDetailsPath = "<SMoviePipelineQueuePanel>//<SDetailsView>";
const FString MRQListPath = MRQDetailsPath + "//<SListPanel>";
const FString MRQScrollBarPath = MRQDetailsPath + "//<SScrollBar>";

const FString MRQEditorPath = "<SStandaloneAssetEditorToolkitHost>//<SMoviePipelineQueueEditor>";

const FString StringParametersPath = "#JobParameter.StringParameter//<SEditableTextBox>";
const FString PathParametersPath = "#JobParameter.PathParameter//<SEditableTextBox>";
const FString FloatParametersPath = "#JobParameter.FloatParameter//<SEditableText>";
const FString IntParametersPath = "#JobParameter.IntParameter//<SEditableText>";
const FString HiddenParametersPath = "#JobParameter.HiddenParameter//<SEditableText>";

const FString Variable1Path = "#EnvironmentParameter.Variable1//<SEditableTextBox>";
const FString Variable2Path = "#EnvironmentParameter.Variable2//<SEditableTextBox>";
const FString Variable3Path = "#EnvironmentParameter.Variable3//<SEditableTextBox>";
const FString HiddenVariablePath = "#EnvironmentParameter.HiddenVariable//<SEditableTextBox>";

const FString StepStringParametersPath = "#StepParameter.StringParameters//<SEditableTextBox>";
const FString StepPathParametersPath = "#StepParameter.PathParameters//<SEditableTextBox>";
const FString StepFloatParametersPath = "#StepParameter.FloatParameters//<SEditableText>";
const FString StepIntParametersPath = "#StepParameter.IntParameters//<SEditableText>";
const FString StepHiddenParametersPath = "#StepParameter.HiddenParameters//<SEditableText>";

FDriverElementPtr Details;
FDriverElementPtr List;
FDriverElementPtr ScrollBar;


inline bool InitForDataAsset(UObject* Asset)
{
	return Init(Asset, DetailsPath, ListPath, ScrollBarPath);
}

inline bool InitForMRQ(UObject* Asset)
{
	return Init(Asset, MRQDetailsPath, MRQListPath, MRQScrollBarPath);
}

inline bool Init(UObject* Asset, const FString& InDetailsPath, const FString& InListPath, const FString& InScrollBarPath)
{
    if (!IsValid(Asset))
    {
        TestTrue(TEXT("Asset should exist"), false);
        return false;
    }
    // Locate Details View
    Details = Driver->FindElement(By::Path(InDetailsPath));
    Driver->Wait(Until::ElementExists(Details.ToSharedRef(), FWaitTimeout::InSeconds(2.f)));
    if (!Details->Exists())
    {
        TestTrue(TEXT("Details view should exist"), false);
        return false;
    }
    Details->Focus();

    // Locate List and ScrollBar
    List = Driver->FindElement(By::Path(InListPath));
    if (!List->Exists())
    {
        TestTrue(TEXT("List widget should exist"), false);
        return false;
    }
    ScrollBar = Driver->FindElement(By::Path(InScrollBarPath));
    return true;
}

inline void ShowTestStepParameters()
{
	CreatedStepDataAsset->RemoveHiddenParameters("StringParameters");
	CreatedStepDataAsset->RemoveHiddenParameters("PathParameters");
	CreatedStepDataAsset->RemoveHiddenParameters("FloatParameters");
	CreatedStepDataAsset->RemoveHiddenParameters("IntParameters");
}

inline void ShowTestEnvironmentParameters()
{
	CreatedEnvironmentDataAsset->RemoveHiddenParameter("Variable1");
	CreatedEnvironmentDataAsset->RemoveHiddenParameter("Variable2");
	CreatedEnvironmentDataAsset->RemoveHiddenParameter("Variable3");
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

	Describe("DeadlineCloudMRQJobUI", [this]()
	{
		BeforeEach([this]() {
			CreatedRenderJobDataAsset = CreateAsset<UDeadlineCloudRenderJob>(JobTemplate, PathToJobTemplate);
			CreatedRenderJobDataAsset->AddToRoot();
			CreatedStepDataAsset = CreateAsset<UDeadlineCloudStep>(StepTemplate, PathToStepTemplate);
			CreatedStepDataAsset->AddToRoot();
			CreatedEnvironmentDataAsset = CreateAsset<UDeadlineCloudEnvironment>(EnvTemplate, PathToEnvironmentTemplate);
			CreatedEnvironmentDataAsset->AddToRoot();

			CreatedEmptyStepDataAsset = CreateAsset<UDeadlineCloudStep>(EmptyStepTemplate, PathToEmptyStepTemplate);
			CreatedEmptyStepDataAsset->AddToRoot();
			
			CreatedEmptyEnvironmentDataAsset = CreateAsset<UDeadlineCloudEnvironment>(EmptyEnvTemplate, PathToEmptyEnvironmentTemplate);
			CreatedEmptyEnvironmentDataAsset->AddToRoot();

			CreatedStepDataAsset->Environments.Add(CreatedEmptyEnvironmentDataAsset);

			CreatedRenderJobDataAsset->Steps.Add(CreatedStepDataAsset);
			CreatedRenderJobDataAsset->Steps.Add(CreatedEmptyStepDataAsset);
			CreatedRenderJobDataAsset->Environments.Add(CreatedEnvironmentDataAsset);

			ShowTestEnvironmentParameters();
			ShowTestStepParameters();

			FModuleManager::LoadModuleChecked<IModuleInterface>("MovieRenderPipelineEditor");

			const FName MRQTabName("MoviePipelineQueue");
			FGlobalTabmanager::Get()->TryInvokeTab(MRQTabName);

			UMoviePipelineQueueSubsystem* QueueSubsystem = GEditor
				? GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>()
				: nullptr;
		

			if (!QueueSubsystem)
			{
				TestTrue(TEXT("QueueSubsystem should exist"), false);
				return;
			}

			UMoviePipelineQueue* Queue = QueueSubsystem->GetQueue();
			if (!Queue)
			{
				TestTrue(TEXT("Queue should exist"), false);
				return;
			}

			Queue->DeleteAllJobs();
			MRQJob = CastChecked<UMoviePipelineDeadlineCloudExecutorJob>(Queue->AllocateNewJob(UMoviePipelineDeadlineCloudExecutorJob::StaticClass()));

			if (!MRQJob)
			{
				TestTrue(TEXT("Cant create UMoviePipelineDeadlineCloudExecutorJob instance"), false);
				return;
			}

			MRQJob->JobPreset = CreatedRenderJobDataAsset;
			MRQJob->JobName = "TestMRQJob";
			MRQJob->JobPresetChanged();
			MRQJob->OnRequestDetailsRefresh.ExecuteIfBound();
			});

		It("MRQJobUI", EAsyncExecution::ThreadPool, FTimespan::FromSeconds(120), [this]() {
			Driver->Wait(FTimespan::FromSeconds(1));
			FDriverElementPtr MrqJobWidget = Driver->FindElement(By::Path("<SMoviePipelineQueueEditor>//<SQueueJobListRow>//<SExpanderArrow>"));
			Driver->Wait(Until::ElementExists(MrqJobWidget.ToSharedRef(), FWaitTimeout::InSeconds(2.f)));

			if (!MrqJobWidget->Exists())
			{
				TestTrue(TEXT("MRQ Job widget should exist"), false);
				return;
			}
			MrqJobWidget->Focus();
			MrqJobWidget->Click(EMouseButtons::Type::Left);

			if (!InitForMRQ(MRQJob))
			{
				return;
			}

			ExpandAllProperties(MRQDetailsPath, Driver);

			FDriverElementRef StringParametersWidget = Driver->FindElement(By::Path(StringParametersPath));
			FDriverElementRef PathParametersWidget = Driver->FindElement(By::Path(PathParametersPath));
			FDriverElementRef FloatParametersWidget = Driver->FindElement(By::Path(FloatParametersPath));
			FDriverElementRef IntParametersWidget = Driver->FindElement(By::Path(IntParametersPath));
			FDriverElementRef HiddenParametersWidget = Driver->FindElement(By::Path(HiddenParametersPath));

			FDriverElementRef StepStringParametersWidget = Driver->FindElement(By::Path(StepStringParametersPath));
			FDriverElementRef StepPathParametersWidget = Driver->FindElement(By::Path(StepPathParametersPath));
			FDriverElementRef StepFloatParametersWidget = Driver->FindElement(By::Path(StepFloatParametersPath));
			FDriverElementRef StepIntParametersWidget = Driver->FindElement(By::Path(StepIntParametersPath));
			FDriverElementRef StepHiddenParametersWidget = Driver->FindElement(By::Path(StepHiddenParametersPath));

			FDriverElementRef Variable1Widget = Driver->FindElement(By::Path(Variable1Path));
			FDriverElementRef Variable2Widget = Driver->FindElement(By::Path(Variable2Path));
			FDriverElementRef Variable3Widget = Driver->FindElement(By::Path(Variable3Path));
			FDriverElementRef HiddenVariableWidget = Driver->FindElement(By::Path(HiddenVariablePath));

			FDriverElementRef DefaultStepCategory = Driver->FindElement(By::Path("#MRQStepHeader.Render"));
			FDriverElementRef EmptyStepCategory = Driver->FindElement(By::Path("#MRQStepHeader.Empty"));
			FDriverElementRef DefaultEnvCategory = Driver->FindElement(By::Path("#MRQEnvHeader.LaunchUnrealEditor"));
			FDriverElementRef EmptyStepEnvCategory = Driver->FindElement(By::Path("#MRQStepEnvHeader.Empty"));

			auto VisibilityTest = [this](const FString& ParameterName, FDriverElementRef Widget, bool bShouldBeVisible)
				{
					ScrollToElement(Driver, List.ToSharedRef(), ScrollBar.ToSharedRef(), Widget, 50);
					bool bIsVisible = Widget->IsVisible();
					if (bShouldBeVisible)
					{
						TestTrue(ParameterName + " widget should be visible", bIsVisible);
					}
					else
					{
						TestFalse(ParameterName + " widget should be hidden", bIsVisible);
					}
				};

			VisibilityTest("StringParameters", StringParametersWidget, true);
			VisibilityTest("PathParameters", PathParametersWidget, true);
			VisibilityTest("FloatParameters", FloatParametersWidget, true);
			VisibilityTest("IntParameters", IntParametersWidget, true);
			VisibilityTest("HiddenParameters", HiddenParametersWidget, false);

			VisibilityTest("StepStringParameters", StepStringParametersWidget, true);
			VisibilityTest("StepPathParameters", StepPathParametersWidget, true);
			VisibilityTest("StepFloatParameters", StepFloatParametersWidget, true);
			VisibilityTest("StepIntParameters", StepIntParametersWidget, true);
			VisibilityTest("StepHiddenParameters", StepHiddenParametersWidget, false);

			VisibilityTest("Variable1", Variable1Widget, true);
			VisibilityTest("Variable2", Variable2Widget, true);
			VisibilityTest("Variable3", Variable3Widget, true);
			VisibilityTest("HiddenVariable", HiddenVariableWidget, false);

			VisibilityTest("Default Step category", DefaultStepCategory, true);
			VisibilityTest("Empty Step category", EmptyStepCategory, false);
			VisibilityTest("Default Environment category", DefaultEnvCategory, true);
			VisibilityTest("Empty Step Environment category", EmptyStepEnvCategory, false);

			});

		AfterEach([this]()
			{
				CreatedRenderJobDataAsset->RemoveFromRoot();
				CreatedRenderJobDataAsset = nullptr;
				CreatedStepDataAsset->RemoveFromRoot();
				CreatedStepDataAsset = nullptr;
				CreatedEnvironmentDataAsset->RemoveFromRoot();
				CreatedEnvironmentDataAsset = nullptr;

				CreatedEmptyStepDataAsset->RemoveFromRoot();
				CreatedEmptyStepDataAsset = nullptr;
				CreatedEmptyEnvironmentDataAsset->RemoveFromRoot();
				CreatedEmptyEnvironmentDataAsset = nullptr;

				FModuleManager::LoadModuleChecked<IModuleInterface>("MovieRenderPipelineEditor");

				UMoviePipelineQueueSubsystem* QueueSubsystem = GEditor
					? GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>()
					: nullptr;

				if (QueueSubsystem)
				{
					UMoviePipelineQueue* Queue = QueueSubsystem->GetQueue();
					if (Queue)
					{
						Queue->DeleteAllJobs();
					}
				}

				const FName MRQTabName("MoviePipelineQueue");
				TSharedPtr<SDockTab> Tab = FGlobalTabmanager::Get()->FindExistingLiveTab(MRQTabName);
				if (Tab.IsValid())
				{
					Tab->RequestCloseTab();
				}
			});
	});


    Describe("DeadlineCloudJobUI", [this]()
    {
		BeforeEach([this]() {
			CreatedJobDataAsset = CreateAndOpenAsset<UDeadlineCloudJob>(JobTemplate, PathToJobTemplate);
			CreatedJobDataAsset->AddToRoot();

			TestTrue("HiddenParameters should contains in hidden parameters array by default", CreatedJobDataAsset->ContainsHiddenParameters("HiddenParameter"));
			TestFalse("PathParameter should not contains in hidden parameters array by default", CreatedJobDataAsset->ContainsHiddenParameters("PathParameter"));
			TestFalse("IntParameter should not contains in hidden parameters array by default", CreatedJobDataAsset->ContainsHiddenParameters("IntParameter"));
			TestFalse("StringParameter should not contains in hidden parameters array by default", CreatedJobDataAsset->ContainsHiddenParameters("StringParameter"));
			TestFalse("FloatParameter should not contains in hidden parameters array by default", CreatedJobDataAsset->ContainsHiddenParameters("FloatParameter"));

			});

		It("JobUI", EAsyncExecution::ThreadPool, FTimespan::FromSeconds(120), [this]() {
			if (!InitForDataAsset(CreatedJobDataAsset))
			{
				return;
			}

			ExpandAllProperties(DetailsPath, Driver);

			FString JobNamePath = DetailsPath + "//#JobPreset.Name//<SEditableTextBox>";
			FString DescriptionPath = DetailsPath + "//#JobPreset.Description//<SEditableTextBox>";

			FDriverElementRef JobNameWidget = Driver->FindElement(By::Path(JobNamePath));
			FDriverElementRef DescriptionWidget = Driver->FindElement(By::Path(DescriptionPath));

			FDriverElementRef StringParametersWidget = Driver->FindElement(By::Path(StringParametersPath));
			FDriverElementRef PathParametersPathWidget = Driver->FindElement(By::Path(PathParametersPath));
			FDriverElementRef FloatParametersWidget = Driver->FindElement(By::Path(FloatParametersPath));
			FDriverElementRef IntParametersWidget = Driver->FindElement(By::Path(IntParametersPath));
			FDriverElementRef HiddenParametersWidget = Driver->FindElement(By::Path(HiddenParametersPath));

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

			ScrollToElement(Driver, List.ToSharedRef(), ScrollBar.ToSharedRef(), HiddenParametersWidget, 50);
			bool bHiddenParametersWidgetExists = HiddenParametersWidget->Exists();
			bool bHiddenParametersWidgetVisible = HiddenParametersWidget->IsVisible();
			TestTrue("HiddenParameters widget should exist", bHiddenParametersWidgetExists);
			TestTrue("HiddenParameters widget should be visible", bHiddenParametersWidgetVisible);

			});

        AfterEach([this]()
            {
				auto* Editor = GEditor->GetEditorSubsystem<UAssetEditorSubsystem>();
				Editor->CloseAllAssetEditors();

				CreatedJobDataAsset->RemoveFromRoot();
                CreatedJobDataAsset = nullptr;
            });
    });

    Describe("DeadlineCloudStepUI", [this]()
    {
		BeforeEach([this]() {
			CreatedStepDataAsset = CreateAndOpenAsset<UDeadlineCloudStep>(StepTemplate, PathToStepTemplate);
			CreatedStepDataAsset->AddToRoot();

			TestTrue("HiddenParameters should contains in hidden parameters array by default", CreatedStepDataAsset->ContainsHiddenParameters("HiddenParameters"));
			TestTrue("IntParameters should contains in hidden parameters array by default", CreatedStepDataAsset->ContainsHiddenParameters("IntParameters"));
			TestTrue("FloatParameters should contains in hidden parameters array by default", CreatedStepDataAsset->ContainsHiddenParameters("FloatParameters"));
			TestTrue("StringParameters should contains in hidden parameters array by default", CreatedStepDataAsset->ContainsHiddenParameters("StringParameters"));
			TestTrue("PathParameters should contains in hidden parameters array by default", CreatedStepDataAsset->ContainsHiddenParameters("PathParameters"));

			ShowTestStepParameters();
			});

		It("StepUI", EAsyncExecution::ThreadPool, FTimespan::FromSeconds(120), [this]() {
			if (!InitForDataAsset(CreatedStepDataAsset))
			{
				return;
			}

			ExpandAllProperties(DetailsPath, Driver);

			FDriverElementRef StringParametersWidget = Driver->FindElement(By::Path(StepStringParametersPath));
			FDriverElementRef PathParametersPathWidget = Driver->FindElement(By::Path(StepPathParametersPath));
			FDriverElementRef FloatParametersWidget = Driver->FindElement(By::Path(StepFloatParametersPath));
			FDriverElementRef IntParametersWidget = Driver->FindElement(By::Path(StepIntParametersPath));
			FDriverElementRef HiddenParametersWidget = Driver->FindElement(By::Path(StepHiddenParametersPath));

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

			//HiddenParameter
			ScrollToElement(Driver, List.ToSharedRef(), ScrollBar.ToSharedRef(), HiddenParametersWidget, 50);
			bool bHiddenParametersWidgetExists = HiddenParametersWidget->Exists();
			bool bHiddenParametersWidgetVisible = HiddenParametersWidget->IsVisible();
			TestTrue("HiddenParameters widget should exist", bHiddenParametersWidgetExists);
			TestTrue("HiddenParameters widget should be visibile", bHiddenParametersWidgetVisible);
		});

        AfterEach([this]()
            {
				auto* Editor = GEditor->GetEditorSubsystem<UAssetEditorSubsystem>();
				Editor->CloseAllAssetEditors();

				CreatedStepDataAsset->RemoveFromRoot();
                CreatedStepDataAsset = nullptr;
            });
    });

    Describe("DeadlineCloudEnvironmentUI", [this]()
    {
		BeforeEach([this]() {
			CreatedEnvironmentDataAsset = CreateAndOpenAsset<UDeadlineCloudEnvironment>(EnvTemplate, PathToEnvironmentTemplate);
			CreatedEnvironmentDataAsset->AddToRoot();

			TestTrue("HiddenVariable should contains in hidden parameters array by default", CreatedEnvironmentDataAsset->ContainsHiddenParameters("HiddenVariable"));
			TestTrue("Variable1 should contains in hidden parameters array by default", CreatedEnvironmentDataAsset->ContainsHiddenParameters("Variable1"));
			TestTrue("Variable2 should contains in hidden parameters array by default", CreatedEnvironmentDataAsset->ContainsHiddenParameters("Variable2"));
			TestTrue("Variable3 should contains in hidden parameters array by default", CreatedEnvironmentDataAsset->ContainsHiddenParameters("Variable3"));

			ShowTestEnvironmentParameters();
			});

		It("EnvironmentUI", EAsyncExecution::ThreadPool, FTimespan::FromSeconds(120), [this]() {
			if (!InitForDataAsset(CreatedEnvironmentDataAsset))
			{
				return;
			}

			ExpandAllProperties(DetailsPath, Driver);

			FDriverElementRef Variable1Widget = Driver->FindElement(By::Path(Variable1Path));
			FDriverElementRef Variable2Widget = Driver->FindElement(By::Path(Variable2Path));
			FDriverElementRef Variable3Widget = Driver->FindElement(By::Path(Variable3Path));
			FDriverElementRef HiddenVariableWidget = Driver->FindElement(By::Path(HiddenVariablePath));

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

			ScrollToElement(Driver, List.ToSharedRef(), ScrollBar.ToSharedRef(), HiddenVariableWidget, 50);
			bool bHiddenVariableWidgetExists = HiddenVariableWidget->Exists();
			bool bHiddenVariableWidgetVisible = HiddenVariableWidget->IsVisible();
			TestTrue("HiddenVariable widget should exist", bHiddenVariableWidgetExists);
			TestTrue("HiddenVariable widget should be visibile", bHiddenVariableWidgetVisible);
		});

        AfterEach([this]()
			{
				auto* Editor = GEditor->GetEditorSubsystem<UAssetEditorSubsystem>();
				Editor->CloseAllAssetEditors();

				CreatedEnvironmentDataAsset->RemoveFromRoot();
				CreatedEnvironmentDataAsset = nullptr;
		});
    });

	AfterEach([this]() {
		Driver.Reset();
		IAutomationDriverModule::Get().Disable();
		});
}

