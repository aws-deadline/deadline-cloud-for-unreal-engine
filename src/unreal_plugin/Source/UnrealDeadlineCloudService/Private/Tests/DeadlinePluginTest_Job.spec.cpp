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
#include "DeadlineCloudJobSettings/DeadlineCloudJob.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "PythonAPILibraries/DeadlineCloudJobBundleLibrary.h"
#include "PythonAPILibraries/PythonParametersConsistencyChecker.h"


BEGIN_DEFINE_SPEC(FDeadlinePluginJobSpec, "Deadline",
    EAutomationTestFlags::ProductFilter | EAutomationTestFlags::EditorContext);


UDeadlineCloudJob* CreatedJobDataAsset;
FParametersConsistencyCheckResult result;

//All filepaths
FString PluginContentDir;
FString PathToJobTemplate;

FString DefaultTemplate = "/Content/Python/openjd_templates/job_template.yml";
FString ChangedTemplate = "/Test/";


END_DEFINE_SPEC(FDeadlinePluginJobSpec);

void FDeadlinePluginJobSpec::Define()
{

    Describe("FOpenDeadlineJob", [this]()
        {
            // DataAsset for all tests
            BeforeEach([this]()
                {
                    if (!CreatedJobDataAsset)
                    {

                        PluginContentDir = IPluginManager::Get().FindPlugin(TEXT("UnrealDeadlineCloudService"))->GetBaseDir();
                        PluginContentDir = FPaths::ConvertRelativePathToFull(PluginContentDir);
                        PathToJobTemplate = FPaths::Combine(PluginContentDir, DefaultTemplate);
                        FPaths::NormalizeDirectoryName(PathToJobTemplate);

                        //Create asset
                          CreatedJobDataAsset = NewObject<UDeadlineCloudJob>();
                        CreatedJobDataAsset->PathToTemplate.FilePath = PathToJobTemplate;

                    }
                });

            It("Read DeadlineCloudJob from template", [this]()
                {
                    if (CreatedJobDataAsset)
                    {
                        CreatedJobDataAsset->OpenJobFile(CreatedJobDataAsset->PathToTemplate.FilePath);
                        if (CreatedJobDataAsset->GetJobParameters().Num() > 0)
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
                        TestFalse("Error creating asset", !(CreatedJobDataAsset != nullptr));
                    }
                });

            It("Check DeadlineCloudJob parameters consistency", [this]()
                {
                    CreatedJobDataAsset->OpenJobFile(CreatedJobDataAsset->PathToTemplate.FilePath);
                    result = CreatedJobDataAsset->CheckJobParametersConsistency(CreatedJobDataAsset);
                    if (result.Passed == true) {
                        TestTrue("Parameters are consistent", true);
                    }
                    else
                    {
                        TestFalse(result.Reason, (result.Passed == false));
                    }
                });

            It("Change DeadlineCloudJob parameters in template", [this]()
                {
                    FString DestinationDirectory = FPaths::Combine(FPaths::ProjectContentDir(), ChangedTemplate);
                    DestinationDirectory = FPaths::ConvertRelativePathToFull(DestinationDirectory);
                    FPaths::NormalizeDirectoryName(DestinationDirectory);

                    IFileManager& FileManager = IFileManager::Get();

                    if (FileManager.FileExists(*PathToJobTemplate))
                    {
                        //Destination dir
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
                                    //Change job template
                                    TemplateContent.ReplaceInline(*str0, *str1);
                                    if (FFileHelper::SaveStringToFile(TemplateContent, *DestinationFilePath))
                                    {

                                        CreatedJobDataAsset->OpenJobFile(CreatedJobDataAsset->PathToTemplate.FilePath);
                                        CreatedJobDataAsset->PathToTemplate.FilePath = DestinationFilePath;
                                        result = CreatedJobDataAsset->CheckJobParametersConsistency(CreatedJobDataAsset);
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

                    }
                });

            It("Change DeadlineCloudJob parameters in data asset", [this]()
                {
                    CreatedJobDataAsset->OpenJobFile(CreatedJobDataAsset->PathToTemplate.FilePath);
                    TArray <FParameterDefinition> Parameters = CreatedJobDataAsset->GetJobParameters();
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


//#endif