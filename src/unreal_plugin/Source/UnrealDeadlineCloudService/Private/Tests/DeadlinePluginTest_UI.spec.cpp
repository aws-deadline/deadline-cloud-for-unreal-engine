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
#include "DeadlineCloudJobSettings/DeadlineCloudDetailsWidgetsHelper.h"
#include "DeadlineCloudJobSettings/DeadlineCloudDeveloperSettings.h"

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
#include "PackageTools.h"
#include "AssetViewUtils.h"

#include "MoviePipelineQueueSubsystem.h"

#define TEST_TRUE(expression) \
	EPIC_TEST_BOOLEAN_(TEXT(#expression), expression, true)

#define TEST_FALSE(expression) \
	EPIC_TEST_BOOLEAN_(TEXT(#expression), expression, false)

#define TEST_EQUAL(expression, expected) \
	EPIC_TEST_BOOLEAN_(TEXT(#expression), expression, expected)

#define EPIC_TEST_BOOLEAN_(text, expression, expected) \
	TestEqual(text, expression, expected);

static void BuildMinimalPreset(UMoviePipelineDeadlineCloudExecutorJob* ExecJob)
{
    const FString Path = TEXT("/UnrealDeadlineCloudService/OpenJD_DataAssets/Default/OpenJD_Default_RenderJob.OpenJD_Default_RenderJob");
    
    UDeadlineCloudRenderJob* DefaultJob = LoadObject<UDeadlineCloudRenderJob>(nullptr, *Path);
    check(DefaultJob);

    ExecJob->JobPreset = DefaultJob;
	ExecJob->ReloadDataFromJobPreset();
}

static void CleanupCreatedAssets(const FString& FolderPath, FAutomationTestBase* Test)
{
    FAssetRegistryModule& AssetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");

    TArray<FAssetData> Assets;
    AssetRegistryModule.Get().GetAssetsByPath(*FolderPath, Assets, true);

    if (Assets.Num() == 0)
    {
        return;
    }

	TArray<UObject*> ObjectsToDelete;
    for (const FAssetData& Asset : Assets)
    {
        UObject* AssetObj = Asset.GetAsset();
        if (AssetObj)
        {
            ObjectsToDelete.Add(AssetObj);
        }
    }

    ObjectTools::DeleteObjects(ObjectsToDelete, false);
	AssetViewUtils::DeleteFolders({ FolderPath });
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSaveAsJobPreset_BasicCreation,
	"DeadlineCloud.SaveAsJobPreset.BasicCreation",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FSaveAsJobPreset_BasicCreation::RunTest(const FString& Parameters)
{
	UMoviePipelineDeadlineCloudExecutorJob* ExecJob = NewObject<UMoviePipelineDeadlineCloudExecutorJob>();
	TestNotNull(TEXT("ExecutorJob must be created"), ExecJob);

	BuildMinimalPreset(ExecJob);

	const FString FolderPath = TEXT("/Game/Automated/DeadlineCloud/") + FGuid::NewGuid().ToString(EGuidFormats::Digits);
	FString BaseName         = TEXT("Preset_") + FGuid::NewGuid().ToString(EGuidFormats::Digits);

	FString FolderCopy = FolderPath;
	FString BaseCopy   = BaseName;
	ExecJob->SaveAsJobPreset(FolderCopy, BaseCopy, false);

	FAssetRegistryModule& ARM = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	FARFilter Filter;
	Filter.PackagePaths.Add(*FolderPath);
	Filter.bRecursivePaths = true;

	TArray<FAssetData> FoundAssets;
	ARM.Get().GetAssets(Filter, FoundAssets);
	TestTrue(*FString::Printf(TEXT("Assets should be created in %s"), *FolderPath), FoundAssets.Num() > 0);

	bool bAnyHasFlags = false;
	for (const FAssetData& AD : FoundAssets)
	{
		if (const UObject* Obj = AD.GetAsset())
		{
			const EObjectFlags Flags = Obj->GetFlags();
			if ((Flags & RF_Public) && (Flags & RF_Standalone))
			{
				bAnyHasFlags = true;
				break;
			}
		}
	}
	TestTrue(TEXT("At least one created asset should have RF_Public | RF_Standalone"), bAnyHasFlags);

	CleanupCreatedAssets(FolderPath, this);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSaveAsJobPreset_OverwritesExisting,
	"DeadlineCloud.SaveAsJobPreset.OverwritesExisting",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FSaveAsJobPreset_OverwritesExisting::RunTest(const FString& Parameters)
{
	UMoviePipelineDeadlineCloudExecutorJob* ExecJob = NewObject<UMoviePipelineDeadlineCloudExecutorJob>();
	ExecJob->AddToRoot();
	TestNotNull(TEXT("ExecutorJob created"), ExecJob);

	BuildMinimalPreset(ExecJob);
	TestNotNull(TEXT("Precondition: JobPreset prepared"), ExecJob->JobPreset.Get());

	const FString FolderPath = TEXT("/Game/Automated/DeadlineCloud/") + FGuid::NewGuid().ToString(EGuidFormats::Digits);
	FString BaseName         = TEXT("PresetOverwrite_") + FGuid::NewGuid().ToString(EGuidFormats::Digits);

	FString FolderCopy = FolderPath;
	FString BaseCopy   = BaseName;
	ExecJob->SaveAsJobPreset(FolderCopy, BaseCopy, false);

	TestNotNull(TEXT("JobPreset after first save"), ExecJob->JobPreset.Get());
	BuildMinimalPreset(ExecJob);
	ExecJob->SaveAsJobPreset(FolderCopy, BaseCopy, false);

	TestNotNull(TEXT("JobPreset after second save"), ExecJob->JobPreset.Get());
	ExecJob->RemoveFromRoot();
	CleanupCreatedAssets(FolderPath, this);
	return true;
}

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

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FIsValidAttributeName_Test,
	"DeadlineCloud.Validation.AttributeName.Integration",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter
)

bool FIsValidAttributeName_Test::RunTest(const FString& Parameters)
{
	FText Error;

	UDeadlineCloudJobBundleLibrary* Library = UDeadlineCloudJobBundleLibrary::Get();
	if (!Library)
	{
		const bool bOk = FDeadlineCloudInputValidationHelper::IsValidAttributeName(TEXT("AnyName"), Error);

		TestFalse("Should fail when library is unavailable", bOk);
		TestTrue("Should return user-friendly error",
			Error.ToString().Contains(TEXT("Cannot validate the name")));

		return true;
	}

	const bool bValidTest = FDeadlineCloudInputValidationHelper::IsValidAttributeName(TEXT("attr.test"), Error);
	TestTrue("Valid attribute name should pass", bValidTest);
	TestTrue("Error should be empty on success", Error.IsEmpty());
	const bool bInvalidTest = FDeadlineCloudInputValidationHelper::IsValidAttributeName(TEXT("attrtest"), Error);
	TestFalse("Invalid attribute name should not pass", bInvalidTest);
	TestTrue("Error should contain an error message", !Error.IsEmpty());
	const bool bPredefinedTest = FDeadlineCloudInputValidationHelper::IsValidAttributeName(TEXT("attr.worker.os.family"), Error);
	TestFalse("Predefined attribute name should not pass", bInvalidTest);
	TestTrue("Error should contain an error message", !Error.IsEmpty());

	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FIsValidAmountName_Test,
	"DeadlineCloud.Validation.AmountName.Integration",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter
)

bool FIsValidAmountName_Test::RunTest(const FString& Parameters)
{
	FText Error;

	UDeadlineCloudJobBundleLibrary* Library = UDeadlineCloudJobBundleLibrary::Get();
	if (!Library)
	{
		const bool bOk = FDeadlineCloudInputValidationHelper::IsValidAmountName(TEXT("AnyName"), Error);

		TestFalse("Should fail when library is unavailable", bOk);
		TestTrue("Should return user-friendly error",
			Error.ToString().Contains(TEXT("Cannot validate the name")));

		return true;
	}

	const bool bValidTest = FDeadlineCloudInputValidationHelper::IsValidAmountName(TEXT("amount.test"), Error);
	TestTrue("Valid amount name should pass", bValidTest);
	TestTrue("Error should be empty on success", Error.IsEmpty());
	const bool bInvalidTest = FDeadlineCloudInputValidationHelper::IsValidAmountName(TEXT("amounttest"), Error);
	TestFalse("Invalid amount name should not pass", bInvalidTest);
	TestTrue("Error should contain an error message", !Error.IsEmpty());
	const bool bPredefinedTest = FDeadlineCloudInputValidationHelper::IsValidAmountName(TEXT("amount.worker.vcpu"), Error);
	TestFalse("Predefined amount name should not pass", bInvalidTest);
	TestTrue("Error should contain an error message", !Error.IsEmpty());

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

// Hover and retry to avoid intermittent "Element found but not located under the cursor" failures
// when the synthetic cursor has not settled over the target yet.
static bool RobustClick(FAutomationDriverPtr Driver, FDriverElementRef Element, EMouseButtons::Type MouseButton, int32 MaxAttempts = 3)
{
	for (int32 Attempt = 0; Attempt < MaxAttempts; ++Attempt)
	{
		Element->Hover();
		Driver->Wait(FTimespan::FromMilliseconds(50));
		if (Element->Click(MouseButton))
		{
			return true;
		}
		Driver->Wait(FTimespan::FromMilliseconds(100));
	}
	return false;
}

static void ExpandAllProperties(const FString DetailsPath, FAutomationDriverPtr Driver)
{
	FString MainCategoryExpanderArrowPath = DetailsPath + "//<SDetailCategoryTableRow>//<SDetailExpanderArrow>";
	FDriverElementCollectionRef ParametersCategory = Driver->FindElements(By::Path(MainCategoryExpanderArrowPath));
	RobustClick(Driver, ParametersCategory->GetElements()[0], EMouseButtons::Type::Right);
	Driver->Wait(FTimespan::FromSeconds(1));

	FString PopupElementsPath = "<SWindow>//<SPopup>//<SMultiBoxWidget>//<SBorder>//<SVerticalBox>//<SScrollBox>//<SHorizontalBox>//<SOverlay>//<SScrollPanel>//<SVerticalBox>//<SHorizontalBox>//<SMenuEntryButton>";

	FDriverElementCollectionRef PopupElements = Driver->FindElements(By::Path(PopupElementsPath));
	if (!PopupElements->GetElements().IsEmpty())
	{
		PopupElements->GetElements()[2]->Focus();
		RobustClick(Driver, PopupElements->GetElements()[2], EMouseButtons::Type::Left);
	}
}

static void ScrollToElement(FAutomationDriverPtr Driver, FDriverElementRef List, FDriverElementRef ScrollBar, FDriverElementRef TargetElement, uint32 AttemptsLimit)
{
	if (TargetElement->Exists() && TargetElement->IsVisible())
	{
		return;
	}

	if (!List->Exists() || !ScrollBar->Exists())
	{
		return;
	}

	// Start from the top so the target is reachable regardless of the prior scroll offset.
	List->ScrollToBeginning();
	Driver->Wait(FTimespan::FromMilliseconds(100));

	uint32 CurrentAttempts = 0;
	while ((!TargetElement->Exists() || !TargetElement->IsVisible()) && CurrentAttempts < AttemptsLimit)
	{
		if (ScrollBar->IsScrolledToEnd())
		{
			// Let tall, still-laying-out rows settle and re-check before giving up at the bottom.
			Driver->Wait(FTimespan::FromMilliseconds(150));
			return;
		}

		List->ScrollBy(-1);
		Driver->Wait(FTimespan::FromMilliseconds(50));
		CurrentAttempts++;
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
	else if constexpr (std::is_same_v<AssetType, UDeadlineCloudHostRequirements>)
	{
		Asset->OpenHostRequirementsFile(OutFullTemplatePath);
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

static void InputText(FDriverElementRef Widget, const FString& Text, bool bRemoveTextBeforeInput, FAutomationDriverPtr Driver = nullptr)
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

	// Enter commits asynchronously; wait so callers don't read back the stale pre-commit value.
	if (Driver.IsValid())
	{
		Driver->Wait(FTimespan::FromMilliseconds(150));
	}
}



BEGIN_DEFINE_SPEC(FDeadlinePluginUISpec, "DeadlineCloud",
    EAutomationTestFlags::ProductFilter | EAutomationTestFlags::EditorContext | EAutomationTestFlags::NonNullRHI);

FAutomationDriverPtr Driver;
UDeadlineCloudStep* CreatedStepDataAsset;
UDeadlineCloudEnvironment* CreatedEnvironmentDataAsset;
UDeadlineCloudJob* CreatedJobDataAsset;
UDeadlineCloudRenderJob* CreatedRenderJobDataAsset;
UDeadlineCloudHostRequirements* CreatedHostRequirements;
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
FString PathToHostReqTemplate;
FString HostReqTemplate = "/Source/UnrealDeadlineCloudService/Private/Tests/openjd_templates/host_requirements_UI.yml";

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
	CreatedStepDataAsset->GetHiddenManager().Remove("StringParameters");
	CreatedStepDataAsset->GetHiddenManager().Remove("PathParameters");
	CreatedStepDataAsset->GetHiddenManager().Remove("FloatParameters");
	CreatedStepDataAsset->GetHiddenManager().Remove("IntParameters");
}

inline void ShowTestEnvironmentParameters()
{
	CreatedEnvironmentDataAsset->GetHiddenManager().Remove("Variable1");
	CreatedEnvironmentDataAsset->GetHiddenManager().Remove("Variable2");
	CreatedEnvironmentDataAsset->GetHiddenManager().Remove("Variable3");
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

			CreatedRenderJobDataAsset->JobPresetStruct.JobAttachments.InputFiles.Files.Paths.Add(FFilePath("C:/Temp/InputFile1.txt"));
			CreatedRenderJobDataAsset->JobPresetStruct.JobAttachments.InputDirectories.Directories.Paths.Add(FDirectoryPath("C:/Temp/InputDir1"));

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
			RobustClick(Driver, MrqJobWidget.ToSharedRef(), EMouseButtons::Type::Left);

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

			FDriverElementRef SavePresetButton = Driver->FindElement(By::Path("#MRQJobSavePresetButton"));
			FDriverElementRef FileArrayElementText = Driver->FindElement(By::Path("#AttachmentArrayElement.Value//<SFilePathPicker>//<SEditableTextBox>"));
			FDriverElementRef DirArrayElementText = Driver->FindElement(By::Path("#AttachmentArrayElement.Value//<SPropertyEditorText>//<SEditableTextBox>"));

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

			auto EditableTextTest = [this](const FString& ParameterName, FDriverElementRef Widget, const FString& ExpectedValue)
				{
					ScrollToElement(Driver, List.ToSharedRef(), ScrollBar.ToSharedRef(), Widget, 50);
					if (Widget->IsVisible() && Widget->IsInteractable())
					{
						InputText(Widget, "Test", true);
						TestTrue(ParameterName + " should be editable", "Test" == ExpectedValue);
					}
					else
					{
						TestTrue(ParameterName + " widget should be visible and interactable", false);
					}
				};

			VisibilityTest("SavePresetButton", SavePresetButton, true);

			EditableTextTest("File Array Element Text", FileArrayElementText, MRQJob->PresetOverrides.JobAttachments.InputFiles.Files.Paths[0].FilePath);
			EditableTextTest("Dir Array Element Text", DirArrayElementText, MRQJob->PresetOverrides.JobAttachments.InputDirectories.Directories.Paths[0].Path);

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
			
			// always visible with host reqs
			//VisibilityTest("Default Step category", DefaultStepCategory, true);
			//VisibilityTest("Empty Step category", EmptyStepCategory, false);
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

			TestTrue("HiddenParameters should contains in hidden parameters array by default", CreatedJobDataAsset->GetHiddenManager().Contains("HiddenParameter"));
			TestFalse("PathParameter should not contains in hidden parameters array by default", CreatedJobDataAsset->GetHiddenManager().Contains("PathParameter"));
			TestFalse("IntParameter should not contains in hidden parameters array by default", CreatedJobDataAsset->GetHiddenManager().Contains("IntParameter"));
			TestFalse("StringParameter should not contains in hidden parameters array by default", CreatedJobDataAsset->GetHiddenManager().Contains("StringParameter"));
			TestFalse("FloatParameter should not contains in hidden parameters array by default", CreatedJobDataAsset->GetHiddenManager().Contains("FloatParameter"));

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

			TestTrue("HiddenParameters should contains in hidden parameters array by default", CreatedStepDataAsset->GetHiddenManager().Contains("HiddenParameters"));
			TestTrue("IntParameters should contains in hidden parameters array by default", CreatedStepDataAsset->GetHiddenManager().Contains("IntParameters"));
			TestTrue("FloatParameters should contains in hidden parameters array by default", CreatedStepDataAsset->GetHiddenManager().Contains("FloatParameters"));
			TestTrue("StringParameters should contains in hidden parameters array by default", CreatedStepDataAsset->GetHiddenManager().Contains("StringParameters"));
			TestTrue("PathParameters should contains in hidden parameters array by default", CreatedStepDataAsset->GetHiddenManager().Contains("PathParameters"));

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

			TestTrue("HiddenVariable should contains in hidden parameters array by default", CreatedEnvironmentDataAsset->GetHiddenManager().Contains("HiddenVariable"));
			TestTrue("Variable1 should contains in hidden parameters array by default", CreatedEnvironmentDataAsset->GetHiddenManager().Contains("Variable1"));
			TestTrue("Variable2 should contains in hidden parameters array by default", CreatedEnvironmentDataAsset->GetHiddenManager().Contains("Variable2"));
			TestTrue("Variable3 should contains in hidden parameters array by default", CreatedEnvironmentDataAsset->GetHiddenManager().Contains("Variable3"));

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
				InputText(Variable1Widget, "", true, Driver);
				TEST_EQUAL(CreatedEnvironmentDataAsset->Variables.Variables["Variable1"], "");

				FString Variable1TextValid = "ValidString";
				InputText(Variable1Widget, Variable1TextValid, true, Driver);
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

	Describe("DeadlineCloudHostRequirementsUI", [this]()
		{
			BeforeEach([this]() {
				CreatedHostRequirements = CreateAndOpenAsset<UDeadlineCloudHostRequirements>(HostReqTemplate, PathToHostReqTemplate);
				CreatedHostRequirements->AddToRoot();
				});

			It("HostRequirementsUI", EAsyncExecution::ThreadPool, FTimespan::FromSeconds(120), [this]() {
				if (!InitForDataAsset(CreatedHostRequirements))
				{
					return;
				}

				ExpandAllProperties(DetailsPath, Driver);

				FDriverElementRef CustomAmountNameWidget = Driver->FindElement(By::Path("#HostReq.Amount.Custom.Name//<SEditableTextBox>"));
				FDriverElementRef CustomAttrNameWidget = Driver->FindElement(By::Path("#HostReq.Attr.Custom.Name//<SEditableTextBox>"));

				auto FindStringKeyRef =
					[](auto& Map, const FString& KeyToFind) -> FString*
					{
						for (auto It = Map.CreateIterator(); It; ++It)
						{
							if (It.Key() == KeyToFind)
							{
								return &It.Key();
							}
						}

						return nullptr;
					};

				ScrollToElement(Driver, List.ToSharedRef(), ScrollBar.ToSharedRef(), CustomAmountNameWidget, 50);
				bool bCustomAmountNameWidgetExists = CustomAmountNameWidget->Exists();
				TestTrue("CustomAmountNameWidget widget should exist", bCustomAmountNameWidgetExists);

				if (bCustomAmountNameWidgetExists)
				{
					FString* AmountKey = FindStringKeyRef(CreatedHostRequirements->HostRequirements.Amounts, "amount.test");
					if (AmountKey == nullptr)
					{
						TestTrue("Amount Custom Key should exist", false);
					}
					else
					{
						FString OldValue = *AmountKey;
						InputText(CustomAmountNameWidget, "InvalidNameTest", true);
						TestTrue("New key should not exist", FindStringKeyRef(CreatedHostRequirements->HostRequirements.Amounts, "amount.test") != nullptr);

						InputText(CustomAmountNameWidget, "amount.custom", true);
						TestTrue("New key should exist", FindStringKeyRef(CreatedHostRequirements->HostRequirements.Amounts, "amount.custom") != nullptr);
					}
				}

				ScrollToElement(Driver, List.ToSharedRef(), ScrollBar.ToSharedRef(), CustomAttrNameWidget, 50);
				bool bCustomAttrNameWidgetExists = CustomAttrNameWidget->Exists();
				TestTrue("CustomAmountNameWidget widget should exist", bCustomAttrNameWidgetExists);

				if (bCustomAttrNameWidgetExists)
				{
					FString* AttrKey = FindStringKeyRef(CreatedHostRequirements->HostRequirements.Attributes, "attr.test");
					if (AttrKey == nullptr)
					{
						TestTrue("Attr Custom Key should exist", false);
					}
					else
					{
						FString OldValue = *AttrKey;
						InputText(CustomAttrNameWidget, "InvalidNameTest", true);
						TestTrue("New key should not exist", FindStringKeyRef(CreatedHostRequirements->HostRequirements.Attributes, "attr.test") != nullptr);

						InputText(CustomAttrNameWidget, "attr.custom", true);
						TestTrue("New key should exist", FindStringKeyRef(CreatedHostRequirements->HostRequirements.Attributes, "attr.custom") != nullptr);
					}
				}

				});

			AfterEach([this]()
				{
					auto* Editor = GEditor->GetEditorSubsystem<UAssetEditorSubsystem>();
					Editor->CloseAllAssetEditors();

					CreatedHostRequirements->RemoveFromRoot();
					CreatedHostRequirements = nullptr;
				});
		});

	Describe("DeadlineCloudSavePresetWidget", [this]()
    {
		BeforeEach([this]() {
			MRQJob = NewObject<UMoviePipelineDeadlineCloudExecutorJob>();
			MRQJob->AddToRoot();

			FDeadlineCloudDetailsWidgetsHelper::CreateSavePresetDialogWidget(MRQJob, false);
		});

		It("DeadlineCloudSavePresetWidget", EAsyncExecution::ThreadPool, FTimespan::FromSeconds(120), [this]() {
			FDriverElementRef DialogWidget = Driver->FindElement(By::Path("#DeadlineCloudSavePresetWidget"));
			FDriverElementRef ErrorWidget = Driver->FindElement(By::Path("#DeadlineCloudSavePresetWidget.ErrorBox"));
			FDriverElementRef NameWidget = Driver->FindElement(By::Path("#DeadlineCloudSavePresetWidget.NameEditBox"));
			FDriverElementRef CreateButton = Driver->FindElement(By::Path("#DeadlineCloudSavePresetWidget.CreateButton"));
			FDriverElementRef CancelButton = Driver->FindElement(By::Path("#DeadlineCloudSavePresetWidget.CancelButton"));

			Driver->Wait(Until::ElementExists(DialogWidget, FWaitTimeout::InSeconds(2.f)));
			if (!DialogWidget->Exists())
			{
				TestTrue(TEXT("Dialog widget should exist"), false);
				return;
			}

			DialogWidget->Focus();

			if (!NameWidget->Exists())
			{
				TestTrue(TEXT("Name widget should exist"), false);
				return;
			}

			if (!CreateButton->Exists())
			{
				TestTrue(TEXT("CreateButton widget should exist"), false);
				return;
			}

			InputText(NameWidget, "", true);
			Driver->Wait(FTimespan::FromSeconds(0.5f));
			TestTrue("Error widget should be visible when name is empty", ErrorWidget->IsVisible());
			TestFalse("Create button widget should be disabled when name is empty", CreateButton->IsInteractable());

			InputText(NameWidget, "Invalid/", true);
			Driver->Wait(FTimespan::FromSeconds(0.5f));
			TestTrue("Error widget should be visible when name contains invalid characters", ErrorWidget->IsVisible());
			TestFalse("Create button widget should be disabled when name contains invalid characters", CreateButton->IsInteractable());

			InputText(NameWidget, "ValidName", true);
			Driver->Wait(FTimespan::FromSeconds(0.5f));
			TestFalse("Error widget should be hidden when name is valid", ErrorWidget->IsVisible());
			TestTrue("Create button widget should be enabled when name is valid", CreateButton->IsInteractable());

			if (!CancelButton->Exists())
			{
				TestTrue(TEXT("CancelButton widget should exist"), false);
				return;
			}

			CancelButton->Click(EMouseButtons::Type::Left);
			Driver->Wait(FTimespan::FromSeconds(1));
			TestFalse("Dialog widget should be closed after CancelButton click", DialogWidget->Exists());
		});

        AfterEach([this]() {
			MRQJob->RemoveFromRoot();
			MRQJob = nullptr;
		});
    });



	AfterEach([this]() {
		Driver.Reset();
		IAutomationDriverModule::Get().Disable();
		});
}

