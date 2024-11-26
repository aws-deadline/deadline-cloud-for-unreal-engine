#pragma once
#include "DeadlineExecutorImplementationLibrary.h"

#define LOCTEXT_NAMESPACE "DeadlineExecutor"


 TSubclassOf<UMoviePipelineExecutorBase> UDeadlineExecutorImplementationLibrary::GetDefaultDeadlineExecutor()
{
	 UMoviePipelineQueueSubsystem* Subsystem = GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>();
	 check(Subsystem);

	 const UMovieRenderPipelineProjectSettings* ProjectSettings = GetDefault<UMovieRenderPipelineProjectSettings>();
	 TSubclassOf<UMoviePipelineExecutorBase> ExecutorClass = ProjectSettings->DefaultRemoteExecutor.TryLoadClass<UMoviePipelineExecutorBase>();
	 return ExecutorClass;
}
#undef LOCTEXT_NAMESPACE