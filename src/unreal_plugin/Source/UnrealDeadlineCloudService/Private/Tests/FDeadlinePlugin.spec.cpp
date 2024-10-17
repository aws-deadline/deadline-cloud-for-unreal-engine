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


BEGIN_DEFINE_SPEC(FDeadlinePluginSpec, "Deadline",
    EAutomationTestFlags::ProductFilter | EAutomationTestFlags::EditorContext);


UDeadlineCloudJob* CreatedJobDataAsset;
FParametersConsistencyCheckResult result;

//Asset parameters
FString PackageName = TEXT("/Game/Test/TestDeadlineJob");
FString AssetName = TEXT("TestDeadlineJob");
UPackage* Package;// = CreatePackage(*PackageName);

//All filepaths
FString PluginContentDir;
FString PathToJobTemplate;

FString DefaultTemplate = "/Content/Python/openjd_templates/job_template.yml";
FString ChangedTemplate = "/Test/";


END_DEFINE_SPEC(FDeadlinePluginSpec);

void FDeadlinePluginSpec::Define()
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

                        IAssetTools& AssetTools = FModuleManager::LoadModuleChecked<FAssetToolsModule>("AssetTools").Get();
                        Package = CreatePackage(*PackageName);

                        //Create asset
                        CreatedJobDataAsset = NewObject<UDeadlineCloudJob>(Package, UDeadlineCloudJob::StaticClass(), *AssetName, RF_Public | RF_Standalone);
                        FAssetRegistryModule::AssetCreated(CreatedJobDataAsset);

                        //Set template path
                        CreatedJobDataAsset->PathToTemplate.FilePath = PathToJobTemplate;

                    }
                });

            It("Read DeadlineCloudJob from template", [this]()
                {

                    FString PackageFileName = FPackageName::LongPackageNameToFilename(PackageName, FPackageName::GetAssetPackageExtension());
                    bool bSaved = UPackage::SavePackage(Package, CreatedJobDataAsset, RF_Public | RF_Standalone, *PackageFileName);
                    ////
                    if (CreatedJobDataAsset)
                    {
                        CreatedJobDataAsset->OpenJobFile(CreatedJobDataAsset->PathToTemplate.FilePath);
                        if (CreatedJobDataAsset->GetJobParameters().Num() > 0)
                        {
                            TestTrue("Parameters ok", true);
                            UE_LOG(LogTemp, Log, TEXT("TestDeadlineJob parameters uploaded from .yaml file"));
                            //If passed - delete data asset

                            {
                                TArray<UObject*> ObjectsToDelete;
                                ObjectsToDelete.Add(CreatedJobDataAsset);
                                ObjectTools::ForceDeleteObjects(ObjectsToDelete, false);
                                Package->MarkAsGarbage();
                            }
                        }

                        else
                        {
                            TestFalse("Error reading from .yaml", false);
                            UE_LOG(LogTemp, Error, TEXT("Error readimg from .yaml"));
                        }
                    }
                    else
                    {
                        TestFalse("Error creating asset", !(CreatedJobDataAsset != nullptr));
                        UE_LOG(LogTemp, Error, TEXT("Error creating asset"));
                    }
                });

            It("Check DeadlineCloudJob consistency", [this]()
                {
                    CreatedJobDataAsset->OpenJobFile(CreatedJobDataAsset->PathToTemplate.FilePath);
                    result = CreatedJobDataAsset->CheckJobParametersConsistency(CreatedJobDataAsset);
                    if (result.Passed == true) {
                        TestTrue("Parameters are consistent", true);
                        UE_LOG(LogTemp, Log, TEXT("%s"), *result.Reason);
                    }
                    else
                    {
                        TestFalse(result.Reason, (result.Passed == false));
                        UE_LOG(LogTemp, Error, TEXT("%s"), *result.Reason);
                    }
                });

            It("Change template file DeadlineCloudJob check", [this]()
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
                                        UE_LOG(LogTemp, Log, TEXT("Text replaced and file saved successfully."));

                                        CreatedJobDataAsset->OpenJobFile(CreatedJobDataAsset->PathToTemplate.FilePath);
                                        CreatedJobDataAsset->PathToTemplate.FilePath = DestinationFilePath;
                                        result = CreatedJobDataAsset->CheckJobParametersConsistency(CreatedJobDataAsset);
                                        if (result.Passed == false) {
                                            TestTrue("Parameters are non-consistent", true);
                                            UE_LOG(LogTemp, Log, TEXT("Parameters are non-consistent %s"), *result.Reason);
                                        }
                                        else
                                        {
                                            TestFalse(result.Reason, (result.Passed == false));
                                            UE_LOG(LogTemp, Error, TEXT("Check failed %s"), *result.Reason);
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

            //
        });


}

//#endif