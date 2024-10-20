#pragma once

//#if WITH_AUTOMATION_TESTS

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
#include "DeadlineCloudJobSettings/DeadlineCloudEnvironment.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "PythonAPILibraries/DeadlineCloudJobBundleLibrary.h"
#include "PythonAPILibraries/PythonParametersConsistencyChecker.h"


BEGIN_DEFINE_SPEC(FDeadlinePluginEnvironmentSpec, "Deadline",
    EAutomationTestFlags::ProductFilter | EAutomationTestFlags::EditorContext);


UDeadlineCloudEnvironment* CreatedEnvironmentDataAsset;
FParametersConsistencyCheckResult result;

//All filepaths
FString PluginContentDir;
FString PathToEnvironmentTemplate;

FString DefaultTemplate = "/Content/Python/openjd_templates/launch_ue_environment_template.yml";
FString ChangedTemplate = "/Test/";


END_DEFINE_SPEC(FDeadlinePluginEnvironmentSpec);

void FDeadlinePluginEnvironmentSpec::Define()
{

    Describe("FOpenDeadlineEnvironment", [this]()
        {
            // DataAsset for all tests
            BeforeEach([this]()
                {
                    if (!CreatedEnvironmentDataAsset)
                    {

                        PluginContentDir = IPluginManager::Get().FindPlugin(TEXT("UnrealDeadlineCloudService"))->GetBaseDir();
                        PluginContentDir = FPaths::ConvertRelativePathToFull(PluginContentDir);
                        PathToEnvironmentTemplate = FPaths::Combine(PluginContentDir, DefaultTemplate);
                        FPaths::NormalizeDirectoryName(PathToEnvironmentTemplate);

                        //Create asset
                        CreatedEnvironmentDataAsset = NewObject<UDeadlineCloudEnvironment>();
                        CreatedEnvironmentDataAsset->PathToTemplate.FilePath = PathToEnvironmentTemplate;

                    }
                });

            It("Read DeadlineCloudEnvironment from template", [this]()
                {
                    if (CreatedEnvironmentDataAsset)
                    {
                        CreatedEnvironmentDataAsset->OpenEnvFile(CreatedEnvironmentDataAsset->PathToTemplate.FilePath);
                        if (CreatedEnvironmentDataAsset->Variables.Variables.Num() > 0)
                        {
                            TestTrue("Parameters ok", true);
                        }

                        else
                        {
                            TestFalse("Error reading from .yaml", false);
                        }
                    }
                    else
                    {
                        TestFalse("Error creating asset", !(CreatedEnvironmentDataAsset != nullptr));
                    }
                });

            It("Check DeadlineCloudEnvironment parameters consistency", [this]()
                {
                    CreatedEnvironmentDataAsset->OpenEnvFile(CreatedEnvironmentDataAsset->PathToTemplate.FilePath);
                    result = CreatedEnvironmentDataAsset->CheckEnvironmentVariablesConsistency(CreatedEnvironmentDataAsset);
                    if (result.Passed == true) {
                        TestTrue("Parameters are consistent", true);
                    }
                    else
                    {
                        TestFalse(result.Reason, (result.Passed == false));
                    }
                });

            It("Change DeadlineCloudEnvironment parameters in template", [this]()
                {
                    FString DestinationDirectory = FPaths::Combine(FPaths::ProjectContentDir(), ChangedTemplate);
                    DestinationDirectory = FPaths::ConvertRelativePathToFull(DestinationDirectory);
                    FPaths::NormalizeDirectoryName(DestinationDirectory);

                    IFileManager& FileManager = IFileManager::Get();

                    if (FileManager.FileExists(*PathToEnvironmentTemplate))
                    {
                        //Destination dir
                        if (!FileManager.DirectoryExists(*DestinationDirectory))
                        {
                            FileManager.MakeDirectory(*DestinationDirectory);
                        }


                        FString FileName = FPaths::GetCleanFilename(PathToEnvironmentTemplate);
                        FString DestinationFilePath = FPaths::Combine(DestinationDirectory, FileName);

                        if (FileManager.Copy(*DestinationFilePath, *PathToEnvironmentTemplate) == COPY_OK)
                        {
                            FString TemplateContent;
                            if (FFileHelper::LoadFileToString(TemplateContent, *DestinationFilePath))
                            {
                                FString str0 = "REMOTE_EXECUTION"; FString str1 = "Path";
                                if (TemplateContent.Contains("REMOTE_EXECUTION"))
                                {
                                    //Change job template
                                    TemplateContent.ReplaceInline(*str0, *str1);
                                    if (FFileHelper::SaveStringToFile(TemplateContent, *DestinationFilePath))
                                    {

                                        CreatedEnvironmentDataAsset->OpenEnvFile(CreatedEnvironmentDataAsset->PathToTemplate.FilePath);
                                        CreatedEnvironmentDataAsset->PathToTemplate.FilePath = DestinationFilePath;
                                        result = CreatedEnvironmentDataAsset->CheckEnvironmentVariablesConsistency(CreatedEnvironmentDataAsset);
                                        if (result.Passed == false) {
                                            TestTrue("Parameters are non-consistent as expected", true);
                                        }
                                        else
                                        {
                                            TestFalse(result.Reason, (result.Passed == false));
                                        }
                                    }
                                }

                            }
                            else
                            {
                                UE_LOG(LogTemp, Error, TEXT("Failed to load file: %s"), *DestinationFilePath);
                            }
                        }
                      /*  if (FPaths::FileExists(DestinationFilePath))
                        {

                            FileManager.Delete(*DestinationFilePath);
                        }*/
                    }
                });

            It("Change DeadlineCloudEnvironment parameters in data asset", [this]()
                {
                    CreatedEnvironmentDataAsset->OpenEnvFile(CreatedEnvironmentDataAsset->PathToTemplate.FilePath);
                    result = CreatedEnvironmentDataAsset->CheckEnvironmentVariablesConsistency(CreatedEnvironmentDataAsset);
                    if (result.Passed == false) {
                        TestTrue("Parameters are non-consistent as expected", true);
                    }
                    else
                    {
                        TestFalse(result.Reason, (result.Passed == false));
                    }
                });

            It("Fix DeadlineCloudEnvironment consistency", [this]()
                {
                    TMap<FString, FString> EmptyArray;
                    CreatedEnvironmentDataAsset->Variables.Variables = EmptyArray;
                    result = CreatedEnvironmentDataAsset->CheckEnvironmentVariablesConsistency(CreatedEnvironmentDataAsset);
                    if (result.Passed == false) {

                        CreatedEnvironmentDataAsset->FixEnvironmentVariablesConsistency(CreatedEnvironmentDataAsset);
                        result = CreatedEnvironmentDataAsset->CheckEnvironmentVariablesConsistency(CreatedEnvironmentDataAsset);
                        if (result.Passed == true)
                        {
                            TestTrue("Parameters consistency fixed", true);
                        }
                    }
                    else
                    {
                        TestFalse(result.Reason, (result.Passed == false));
                    }
                });
        });


}


//#endif