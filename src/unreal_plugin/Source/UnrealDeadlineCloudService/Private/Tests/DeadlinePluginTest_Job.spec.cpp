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
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "PythonAPILibraries/DeadlineCloudJobBundleLibrary.h"
#include "PythonAPILibraries/PythonParametersConsistencyChecker.h"


BEGIN_DEFINE_SPEC(FDeadlinePluginJobSpec, "Deadline",
    EAutomationTestFlags::ProductFilter | EAutomationTestFlags::EditorContext);

UDeadlineCloudJob* CreatedJobDataAsset;
FParametersConsistencyCheckResult result;


FString PathToJobTemplate;
FString DefaultTemplate = "/Source/UnrealDeadlineCloudService/Private/Tests/openjd_templates/render_job.yml";
FString ChangedTemplate = "/Test/";


END_DEFINE_SPEC(FDeadlinePluginJobSpec);

void FDeadlinePluginJobSpec::Define()
{

    Describe("FOpenDeadlineJob", [this]()
        {

            BeforeEach([this]()
                {
                    FString  PluginContentDir = IPluginManager::Get().FindPlugin(TEXT("UnrealDeadlineCloudService"))->GetBaseDir();
                    PluginContentDir = FPaths::ConvertRelativePathToFull(PluginContentDir);
                    PathToJobTemplate = FPaths::Combine(PluginContentDir, DefaultTemplate);
                    FPaths::NormalizeDirectoryName(PathToJobTemplate);

                    CreatedJobDataAsset = NewObject<UDeadlineCloudJob>();
                    CreatedJobDataAsset->PathToTemplate.FilePath = PathToJobTemplate;
                });
            AfterEach([this]()
                {
                    CreatedJobDataAsset = nullptr;
                });
            It("Read DeadlineCloudJob from template", [this]()
                {
                    if (CreatedJobDataAsset)
                    {
                        CreatedJobDataAsset->OpenJobFile(CreatedJobDataAsset->PathToTemplate.FilePath);
                        if (CreatedJobDataAsset->GetJobParameters().Num() > 0)
                        {
                            TestTrue("Parameters read from .yaml", true);
                        }

                        else
                        {
                            TestFalse("Error reading from .yaml", false);
                        }
                    }
                    else
                    {
                        TestFalse("Error creating asset", (CreatedJobDataAsset == nullptr));
                    }
                });

            It("Check DeadlineCloudJob parameters consistency", [this]()
                {
                    if (CreatedJobDataAsset) {
                        CreatedJobDataAsset->OpenJobFile(CreatedJobDataAsset->PathToTemplate.FilePath);
                        result = CreatedJobDataAsset->CheckJobParametersConsistency(CreatedJobDataAsset);
                        if (result.Passed == true) {
                            TestTrue("Parameters are consistent", true);
                        }
                        else
                        {
                            TestFalse(result.Reason, (result.Passed == false));
                        }
                    }
                    else
                    {
                        TestFalse("Error creating DataAsset", (!CreatedJobDataAsset));
                    }
                });

            It("Change DeadlineCloudJob parameters in template", [this]()
                {
                    /*  Create changed .yaml job template in /Tests/ */
                    FString DestinationDirectory = FPaths::Combine(FPaths::ProjectContentDir(), ChangedTemplate);
                    DestinationDirectory = FPaths::ConvertRelativePathToFull(DestinationDirectory);
                    FPaths::NormalizeDirectoryName(DestinationDirectory);
                    IFileManager& FileManager = IFileManager::Get();
                    if (FileManager.FileExists(*PathToJobTemplate))
                    {
                        /*  Directory of changed template */
                        if (!FileManager.DirectoryExists(*DestinationDirectory))
                        {
                            FileManager.MakeDirectory(*DestinationDirectory);
                        }

                        FString FileName = FPaths::GetCleanFilename(PathToJobTemplate);
                        FString DestinationFilePath = FPaths::Combine(DestinationDirectory, FileName);

                        if (FileManager.Copy(*DestinationFilePath, *PathToJobTemplate) == COPY_OK)
                        {
                            FString TemplateContent;
                            if (FFileHelper::LoadFileToString(TemplateContent, *DestinationFilePath))
                            {
                                FString str0 = "ProjectFilePath"; FString str1 = "Path";
                                if (TemplateContent.Contains("ProjectFilePath"))
                                {
                                    /*  Change job template  */
                                    TemplateContent.ReplaceInline(*str0, *str1);
                                    if (FFileHelper::SaveStringToFile(TemplateContent, *DestinationFilePath))
                                    {
                                        /*   Load default job parameters from file    */
                                        CreatedJobDataAsset->OpenJobFile(CreatedJobDataAsset->PathToTemplate.FilePath);

                                        /*   Change job parameters file  in job DataAsset  */
                                        CreatedJobDataAsset->PathToTemplate.FilePath = DestinationFilePath;
                                        result = CreatedJobDataAsset->CheckJobParametersConsistency(CreatedJobDataAsset);
                                        if (result.Passed == false) {
                                            TestTrue("Parameters are non-consistent as expected", true);
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
                                TestFalse("Failed to load file", true);
                                FileManager.DeleteDirectory(*DestinationDirectory);
                            }
                        }

                    }
                });

            It("Change DeadlineCloudJob parameters in data asset", [this]()
                {
                    CreatedJobDataAsset->PathToTemplate.FilePath = PathToJobTemplate;
                    CreatedJobDataAsset->OpenJobFile(CreatedJobDataAsset->PathToTemplate.FilePath);
                    TArray <FParameterDefinition> Parameters = CreatedJobDataAsset->GetJobParameters();
                    if (Parameters.Num() > 0)
                    {
                        Parameters.RemoveAt(0);
                        CreatedJobDataAsset->SetJobParameters(Parameters);

                        result = CreatedJobDataAsset->CheckJobParametersConsistency(CreatedJobDataAsset);
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

            It("Fix DeadlineCloudJob consistency", [this]()
                {
                    TArray<FParameterDefinition> EmptyArray;
                    CreatedJobDataAsset->SetJobParameters(EmptyArray);
                    result = CreatedJobDataAsset->CheckJobParametersConsistency(CreatedJobDataAsset);
                    if (result.Passed == false) {

                        CreatedJobDataAsset->FixJobParametersConsistency(CreatedJobDataAsset);
                        result = CreatedJobDataAsset->CheckJobParametersConsistency(CreatedJobDataAsset);
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
