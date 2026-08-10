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
#include "DeadlineCloudJobSettings/DeadlineCloudHostRequirements.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "PythonAPILibraries/DeadlineCloudJobBundleLibrary.h"
#include "PythonAPILibraries/PythonParametersConsistencyChecker.h"

BEGIN_DEFINE_SPEC(FDeadlinePluginHostRequirementsSpec, "DeadlineCloud.Offline",
    EAutomationTestFlags::ProductFilter | EAutomationTestFlags::EditorContext);

UDeadlineCloudHostRequirements* CreatedHostRequirmenetsDataAsset;
FParametersConsistencyCheckResult result;

FString PathToHostRequirmenetsTemplate;
FString DefaultTemplate = "/Source/UnrealDeadlineCloudService/Private/Tests/openjd_templates/host_requirements.yml";
FString ChangedTemplate = "/Test/";

inline void TestAmountContainsAndValues(TMap<FString, FDeadlineCloudAmountRequirement>& CustomAmountRequirements, const FString& Key, FFloatRange ExpectedRange)
{
    bool Contains = CustomAmountRequirements.Contains(Key);
    TestTrue(FString::Printf(TEXT("Contains %s"), *Key), Contains);
    if (Contains)
    {
        FFloatRange ActualRange = CustomAmountRequirements[Key].AmountRequirement;
        bool IsMinTypeValid = ActualRange.GetLowerBound().IsOpen() == ExpectedRange.GetLowerBound().IsOpen()
            || ActualRange.GetLowerBound().IsInclusive() == ExpectedRange.GetLowerBound().IsInclusive()
            || ActualRange.GetLowerBound().IsExclusive() == ExpectedRange.GetLowerBound().IsExclusive();
        TestTrue(FString::Printf(TEXT("Min type valid for %s"), *Key), IsMinTypeValid);
        if (IsMinTypeValid && !ActualRange.GetLowerBound().IsOpen())
        {
            TestTrue(FString::Printf(TEXT("Min value valid for %s"), *Key),
                ActualRange.GetLowerBound().GetValue() == ExpectedRange.GetLowerBound().GetValue());
        }

        bool IsMaxTypeValid = ActualRange.GetUpperBound().IsOpen() == ExpectedRange.GetUpperBound().IsOpen()
            || ActualRange.GetUpperBound().IsInclusive() == ExpectedRange.GetUpperBound().IsInclusive()
            || ActualRange.GetUpperBound().IsExclusive() == ExpectedRange.GetUpperBound().IsExclusive();
        TestTrue(FString::Printf(TEXT("Max type valid for %s"), *Key), IsMaxTypeValid);
        if (IsMaxTypeValid && !ActualRange.GetUpperBound().IsOpen())
        {
            TestTrue(FString::Printf(TEXT("Max value valid for %s"), *Key),
                ActualRange.GetUpperBound().GetValue() == ExpectedRange.GetUpperBound().GetValue());
        }
    };
}

END_DEFINE_SPEC(FDeadlinePluginHostRequirementsSpec);

void FDeadlinePluginHostRequirementsSpec::Define()
{

    Describe("FDeadlineHostRequirements", [this]()
        {

            BeforeEach([this]()
                {
                    FString  PluginContentDir = IPluginManager::Get().FindPlugin(TEXT("UnrealDeadlineCloudService"))->GetBaseDir();
                    PluginContentDir = FPaths::ConvertRelativePathToFull(PluginContentDir);
                    PathToHostRequirmenetsTemplate = FPaths::Combine(PluginContentDir, DefaultTemplate);
                    FPaths::NormalizeDirectoryName(PathToHostRequirmenetsTemplate);

                    CreatedHostRequirmenetsDataAsset = NewObject<UDeadlineCloudHostRequirements>();
                    CreatedHostRequirmenetsDataAsset->PathToTemplate.FilePath = PathToHostRequirmenetsTemplate;
                });

            It("Read DeadlineHostRequirements from template", [this]()
                {
                    if (CreatedHostRequirmenetsDataAsset)
                    {
                        CreatedHostRequirmenetsDataAsset->OpenHostRequirementsFile(CreatedHostRequirmenetsDataAsset->PathToTemplate.FilePath);
                        if (!CreatedHostRequirmenetsDataAsset->HostRequirements.Amounts.IsEmpty()
                            && !CreatedHostRequirmenetsDataAsset->HostRequirements.Attributes.IsEmpty())
                        {
                            TestTrue("Parameters read from .yaml", true);

                            auto& CustomAmountRequirements = CreatedHostRequirmenetsDataAsset->HostRequirements.Amounts;
                            auto& CustomAttributeRequirements = CreatedHostRequirmenetsDataAsset->HostRequirements.Attributes;
                            TestTrue("Amounts contains 5 elements", CustomAmountRequirements.Num() == 5);
                            TestTrue("Attributes contains 2 elements", CustomAttributeRequirements.Num() == 2);

                            bool Contains = CustomAmountRequirements.Contains("amount.test.invalid");
                            TestFalse("Contains amount.test.invalid", Contains);

                            TestAmountContainsAndValues(CustomAmountRequirements, "amount.worker.vcpu",
                                FFloatRange(FFloatRangeBound::Inclusive(32.0f), FFloatRangeBound::Open()));
                            TestAmountContainsAndValues(CustomAmountRequirements, "amount.worker.memory",
                                FFloatRange(FFloatRangeBound::Inclusive(8.0f), FFloatRangeBound::Open()));
                            TestAmountContainsAndValues(CustomAmountRequirements, "amount.worker.gpu",
                                FFloatRange(FFloatRangeBound::Inclusive(1.0f), FFloatRangeBound::Open()));
                            TestAmountContainsAndValues(CustomAmountRequirements, "amount.worker.gpu.memory",
                                FFloatRange(FFloatRangeBound::Inclusive(8.0f), FFloatRangeBound::Inclusive(24.0f)));
                            TestAmountContainsAndValues(CustomAmountRequirements, "amount.worker.disk.scratch",
                                FFloatRange(FFloatRangeBound::Open(), FFloatRangeBound::Inclusive(16.0f)));

                            Contains = CustomAttributeRequirements.Contains("attr.test.invalid");
                            TestFalse("Contains attr.test.invalid", Contains);
                            Contains = CustomAttributeRequirements.Contains("attr.worker.os.family");
                            TestTrue("Contains attr.worker.os.family", Contains);
                            if (Contains)
                            {
                                TArray<FString> ExpectedAnyOf = { "windows" };
                                TArray<FString> ActualAnyOf = CustomAttributeRequirements["attr.worker.os.family"].AnyOf;
                                bool AreEqual = ExpectedAnyOf.Num() == ActualAnyOf.Num()
                                    && ExpectedAnyOf.ContainsByPredicate([&](const FString& Item) { return ActualAnyOf.Contains(Item); });
                                TestTrue("attr.worker.os.family AnyOf values are correct", AreEqual);
                            }
                            Contains = CustomAttributeRequirements.Contains("attr.worker.cpu.arch");
                            TestTrue("Contains attr.worker.cpu.arch", Contains);
                            if (Contains)
                            {
                                TArray<FString> ExpectedAnyOf = { "x86_64" };
                                TArray<FString> ActualAnyOf = CustomAttributeRequirements["attr.worker.cpu.arch"].AnyOf;
                                bool AreEqual = ExpectedAnyOf.Num() == ActualAnyOf.Num()
                                    && ExpectedAnyOf.ContainsByPredicate([&](const FString& Item) { return ActualAnyOf.Contains(Item); });
                                TestTrue("attr.worker.cpu.arch AllOf values are correct", AreEqual);
                            }
                        }

                        else
                        {
                            TestFalse("Error reading from .yaml", false);
                        }
                    }
                    else
                    {
                        TestFalse("Error creating asset", (CreatedHostRequirmenetsDataAsset == nullptr));
                    }
                });

            AfterEach([this]()
                {
                    CreatedHostRequirmenetsDataAsset = nullptr;
                });
        });
}
