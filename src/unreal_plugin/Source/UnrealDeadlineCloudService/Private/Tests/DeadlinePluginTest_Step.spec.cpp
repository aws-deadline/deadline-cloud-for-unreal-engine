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
#include "DeadlineCloudJobSettings/DeadlineCloudStep.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "PythonAPILibraries/DeadlineCloudJobBundleLibrary.h"
#include "PythonAPILibraries/PythonParametersConsistencyChecker.h"


BEGIN_DEFINE_SPEC(FDeadlinePluginStepSpec, "Deadline",
    EAutomationTestFlags::ProductFilter | EAutomationTestFlags::EditorContext);


UDeadlineCloudStep* CreatedStepDataAsset;
FParametersConsistencyCheckResult result;

FString PathToStepTemplate;
FString DefaultTemplate = "/Source/UnrealDeadlineCloudService/Private/Tests/openjd_templates/render_step.yml";
FString ChangedTemplate = "/Test/";

END_DEFINE_SPEC(FDeadlinePluginStepSpec);

void FDeadlinePluginStepSpec::Define()
{

    Describe("FOpenDeadlineStep", [this]()
        {

            BeforeEach([this]()
                {
                    if (!CreatedStepDataAsset)
                    {
                        FString PluginContentDir = IPluginManager::Get().FindPlugin(TEXT("UnrealDeadlineCloudService"))->GetBaseDir();
                        PluginContentDir = FPaths::ConvertRelativePathToFull(PluginContentDir);
                        PathToStepTemplate = FPaths::Combine(PluginContentDir, DefaultTemplate);
                        FPaths::NormalizeDirectoryName(PathToStepTemplate);

                        CreatedStepDataAsset = NewObject<UDeadlineCloudStep>();
                        CreatedStepDataAsset->PathToTemplate.FilePath = PathToStepTemplate;

                    }
                });

            AfterEach([this]()
                {
                    CreatedStepDataAsset = nullptr;
                });

            It("Read DeadlineCloudStep from template", [this]()
                {
                    if (CreatedStepDataAsset)
                    {
                        CreatedStepDataAsset->OpenStepFile(CreatedStepDataAsset->PathToTemplate.FilePath);
                        if (CreatedStepDataAsset->GetStepParameters().Num() > 0)
                        {
                            TestTrue("Read DeadlineCloudStep from template", true);
                        }

                        else
                        {
                            TestFalse("Error reading from .yaml", false);
                        }
                    }
                    else
                    {
                        TestFalse("Error creating asset", !(CreatedStepDataAsset != nullptr));
                    }
                });

            It("Check DeadlineCloudStep parameters consistency", [this]()
                {
                    CreatedStepDataAsset->OpenStepFile(CreatedStepDataAsset->PathToTemplate.FilePath);
                    result = CreatedStepDataAsset->CheckStepParametersConsistency(CreatedStepDataAsset);
                    if (result.Passed == true) {
                        TestTrue("Parameters are consistent", true);
                    }
                    else
                    {
                        TestFalse(result.Reason, (result.Passed == false));
                    }
                });

            It("Change DeadlineCloudStep parameters in template", [this]()
                {
                    /*  Create changed .yaml step template in /Tests/ */
                    FString DestinationDirectory = FPaths::Combine(FPaths::ProjectContentDir(), ChangedTemplate);
                    DestinationDirectory = FPaths::ConvertRelativePathToFull(DestinationDirectory);
                    FPaths::NormalizeDirectoryName(DestinationDirectory);

                    IFileManager& FileManager = IFileManager::Get();

                    if (FileManager.FileExists(*PathToStepTemplate))
                    {
                        /*  Directory of changed template */
                        if (!FileManager.DirectoryExists(*DestinationDirectory))
                        {
                            FileManager.MakeDirectory(*DestinationDirectory);
                        }


                        FString FileName = FPaths::GetCleanFilename(PathToStepTemplate);
                        FString DestinationFilePath = FPaths::Combine(DestinationDirectory, FileName);

                        if (FileManager.Copy(*DestinationFilePath, *PathToStepTemplate) == COPY_OK)
                        {
                            FString TemplateContent;
                            if (FFileHelper::LoadFileToString(TemplateContent, *DestinationFilePath))
                            {
                                FString str0 = "QueueManifestPath"; FString str1 = "Path";
                                if (TemplateContent.Contains("QueueManifestPath"))
                                {
                                    /*    Change step template  */
                                    TemplateContent.ReplaceInline(*str0, *str1);
                                    if (FFileHelper::SaveStringToFile(TemplateContent, *DestinationFilePath))
                                    {
                                        /*   Load default step parameters from file    */
                                        CreatedStepDataAsset->OpenStepFile(CreatedStepDataAsset->PathToTemplate.FilePath);
                                        /*   Change step parameters file  in step DataAsset  */
                                        CreatedStepDataAsset->PathToTemplate.FilePath = DestinationFilePath;
                                        result = CreatedStepDataAsset->CheckStepParametersConsistency(CreatedStepDataAsset);
                                        if (result.Passed == false) {
                                            TestTrue("Parameters are non-consistent as expected", true);
                                            FileManager.DeleteDirectory(*DestinationDirectory);
                                        }
                                        else
                                        {
                                            TestFalse(result.Reason, (result.Passed == false));
                                            FileManager.DeleteDirectory(*DestinationDirectory);
                                        }
                                    }
                                }

                            }
                            else
                            {
                                TestFalse(result.Reason, (result.Passed == false));
                                FileManager.DeleteDirectory(*DestinationDirectory);
                            }
                        }

                    }
                });

            It("Change DeadlineCloudStep parameters in data asset", [this]()
                {
                    CreatedStepDataAsset->OpenStepFile(CreatedStepDataAsset->PathToTemplate.FilePath);
                    TArray <FStepTaskParameterDefinition> Parameters = CreatedStepDataAsset->GetStepParameters();
                    if (Parameters.Num() > 0)
                    {
                        Parameters.RemoveAt(0);
                        CreatedStepDataAsset->SetStepParameters(Parameters);

                        result = CreatedStepDataAsset->CheckStepParametersConsistency(CreatedStepDataAsset);
                        if (result.Passed == false) {
                            TestTrue("Parameters are non-consistent as expected", true);
                        }
                        else
                        {
                            TestFalse(result.Reason, (result.Passed == false));
                        }
                    }
                    else
                    {
                        TestFalse("Error loading parameters", true);
                    }
                });

            It("Fix DeadlineCloudStep consistency", [this]()
                {
                    if (CreatedStepDataAsset) {
                        TArray<FStepTaskParameterDefinition> EmptyArray;
                        CreatedStepDataAsset->SetStepParameters(EmptyArray);
                        result = CreatedStepDataAsset->CheckStepParametersConsistency(CreatedStepDataAsset);
                        if (result.Passed == false) {

                            CreatedStepDataAsset->FixStepParametersConsistency(CreatedStepDataAsset);
                            result = CreatedStepDataAsset->CheckStepParametersConsistency(CreatedStepDataAsset);
                            if (result.Passed == true)
                            {
                                TestTrue("Parameters consistency fixed", true);
                            }
                        }
                        else
                        {
                            TestFalse(result.Reason, (result.Passed == false));
                        }

                    }
                    else
                    {
                        TestFalse("Error creating asset", !(CreatedStepDataAsset != nullptr));
                    }
                });
        });


}

