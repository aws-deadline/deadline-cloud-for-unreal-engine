// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#include "MovieRenderPipeline/DeadlineExecutorImplementationLibrary.h"

#include "Engine/Engine.h"
#include "HAL/IConsoleManager.h"
#include "ProfilingDebugging/CsvProfiler.h"

#define LOCTEXT_NAMESPACE "DeadlineExecutor"

namespace
{
    bool GIsDeadlineMemReportComplete = true;

    void MarkDeadlineMemReportComplete()
    {
        GIsDeadlineMemReportComplete = true;
    }

    FAutoConsoleCommand MarkDeadlineMemReportCompleteCommand(
        TEXT("DeadlineCloud.MarkMemReportComplete"),
        TEXT("Marks a Deadline Cloud MemReport request complete."),
        FConsoleCommandDelegate::CreateStatic(&MarkDeadlineMemReportComplete));
}

TSubclassOf<UMoviePipelineExecutorBase> UDeadlineExecutorImplementationLibrary::GetDefaultDeadlineExecutor()
{
    UMoviePipelineQueueSubsystem* Subsystem = GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>();
    check(Subsystem);

    const UMovieRenderPipelineProjectSettings* ProjectSettings = GetDefault<UMovieRenderPipelineProjectSettings>();
    TSubclassOf<UMoviePipelineExecutorBase> ExecutorClass = ProjectSettings->DefaultRemoteExecutor.TryLoadClass<UMoviePipelineExecutorBase>();
    return ExecutorClass;
}

void UDeadlineExecutorImplementationLibrary::StopCsvCapture()
{
#if CSV_PROFILER
    FCsvProfiler::Get()->EndCapture();
#endif
}

bool UDeadlineExecutorImplementationLibrary::IsCsvCaptureComplete()
{
#if CSV_PROFILER
    const FCsvProfiler* CsvProfiler = FCsvProfiler::Get();
    return !CsvProfiler->IsCapturing() && !CsvProfiler->IsWritingFile();
#else
    return true;
#endif
}

void UDeadlineExecutorImplementationLibrary::RequestMemReport()
{
    if (!GEngine)
    {
        GIsDeadlineMemReportComplete = true;
        return;
    }

    GIsDeadlineMemReportComplete = false;
    GEngine->DeferredCommands.Add(TEXT("MemReportDeferred -full"));
    GEngine->DeferredCommands.Add(TEXT("DeadlineCloud.MarkMemReportComplete"));
}

bool UDeadlineExecutorImplementationLibrary::IsMemReportComplete()
{
    return GIsDeadlineMemReportComplete;
}

#undef LOCTEXT_NAMESPACE
