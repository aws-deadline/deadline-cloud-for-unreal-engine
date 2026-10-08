// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "Misc/AutomationTest.h"
#include "DeadlineCloudJobSettings/DeadlineCloudDetailsWidgetsHelper.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJob.h"
#include "DeadlineCloudJobSettings/DeadlineCloudRenderJob.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJobDetails.h"
#include "MovieRenderPipeline/MoviePipelineDeadlineCloudExecutorJob.h"
#include "PropertyEditorModule.h"
#include "ISinglePropertyView.h"
#include "PropertyHandle.h"
#include "IPropertyRowGenerator.h"
#include "IDetailTreeNode.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "Widgets/Input/SComboBox.h"
#include "Widgets/SNullWidget.h"
#include "Widgets/Text/STextBlock.h"
#include "InputCoreTypes.h"

namespace
{
	class FDropdownTestDetails : public IDetailCustomization
	{
	public:
		virtual void CustomizeDetails(IDetailLayoutBuilder& DetailBuilder) override {}
	};

	TSharedRef<IPropertyRowGenerator> CreateDropdownTestRows(const TArray<UObject*>& Objects)
	{
		auto Generator = FModuleManager::LoadModuleChecked<FPropertyEditorModule>("PropertyEditor")
			.CreatePropertyRowGenerator(FPropertyRowGeneratorArgs());
		// Exercise the production parameter builders without unrelated account,
		// environment or consistency-panel customizations.
		const auto Details = FOnGetDetailCustomizationInstance::CreateLambda([]()
		{
			return MakeShared<FDropdownTestDetails>();
		});
		Generator->RegisterInstancedCustomPropertyLayout(UDeadlineCloudJob::StaticClass(), Details);
		Generator->RegisterInstancedCustomPropertyLayout(UDeadlineCloudRenderJob::StaticClass(), Details);
		Generator->RegisterInstancedCustomPropertyLayout(UMoviePipelineDeadlineCloudExecutorJob::StaticClass(), Details);
		Generator->RegisterInstancedCustomPropertyTypeLayout(
			FDeadlineCloudJobParametersArray::StaticStruct()->GetFName(),
			FOnGetPropertyTypeCustomizationInstance::CreateStatic(&FDeadlineCloudJobParametersArrayCustomization::MakeInstance));
		Generator->RegisterInstancedCustomPropertyTypeLayout(
			FJobTemplateOverrides::StaticStruct()->GetFName(),
			FOnGetPropertyTypeCustomizationInstance::CreateStatic(&FJobTemplateOverridesCustomization::MakeInstance));
		Generator->SetObjects(Objects);
		return Generator;
	}

	TSharedPtr<IDetailTreeNode> FindDropdownTestRow(const TArray<TSharedRef<IDetailTreeNode>>& Nodes)
	{
		for (const auto& Node : Nodes)
		{
			auto Handle = Node->CreatePropertyHandle();
			if (Handle.IsValid() && Handle->GetProperty() && Handle->GetProperty()->GetFName() == TEXT("Value"))
			{
				auto Parent = Handle->GetParentHandle();
				auto Name = Parent.IsValid() ? Parent->GetChildHandle("Name") : nullptr;
				FString ParameterName;
				if (Name.IsValid() && Name->GetValue(ParameterName) == FPropertyAccess::Success &&
					ParameterName == TEXT("IgnorePlugins"))
				{
					return Node;
				}
			}
			TArray<TSharedRef<IDetailTreeNode>> Children;
			Node->GetChildren(Children, true);
			if (auto Found = FindDropdownTestRow(Children))
			{
				return Found;
			}
		}
		return nullptr;
	}

	TSharedPtr<SWidget> FindDropdownTestWidget(TSharedRef<SWidget> Widget, FName Type)
	{
		if (Widget->GetType() == Type ||
			Widget->GetTypeAsString().StartsWith(Type.ToString() + TEXT("<")))
		{
			return Widget;
		}
		FChildren* Children = Widget->GetChildren();
		for (int32 Index = 0; Index < Children->Num(); ++Index)
		{
			if (auto Found = FindDropdownTestWidget(Children->GetChildAt(Index), Type))
			{
				return Found;
			}
		}
		return nullptr;
	}
}

BEGIN_DEFINE_SPEC(FDeadlinePluginDropdownSpec, "DeadlineCloud.Offline.Dropdown",
	EAutomationTestFlags::ProductFilter | EAutomationTestFlags::EditorContext);
END_DEFINE_SPEC(FDeadlinePluginDropdownSpec);

void FDeadlinePluginDropdownSpec::Define()
{
	for (bool bMrq : {false, true})
	{
		Describe(bMrq ? "MRQ overrides" : "Job preset", [this, bMrq]()
		{
			It("Persists choices and reflects external value changes", [this, bMrq]()
			{
				FParameterDefinition Parameter;
				Parameter.Name = TEXT("IgnorePlugins");
				Parameter.UserInterfaceControl = EUserInterfaceControl::DROPDOWN_LIST;
				Parameter.AllowedValues = {TEXT("false"), TEXT("true"), TEXT("")};
				Parameter.Value = TEXT("false");

				UDeadlineCloudJob* Job = NewObject<UDeadlineCloudJob>();
				Job->ParameterDefinition.Parameters = {Parameter};
				UMoviePipelineDeadlineCloudExecutorJob* Mrq = NewObject<UMoviePipelineDeadlineCloudExecutorJob>();
				Mrq->JobTemplateOverrides.Parameters = {Parameter};
				UObject* Object = bMrq ? static_cast<UObject*>(Mrq) : static_cast<UObject*>(Job);
				FName PropertyName = bMrq
					? GET_MEMBER_NAME_CHECKED(UMoviePipelineDeadlineCloudExecutorJob, JobTemplateOverrides)
					: GET_MEMBER_NAME_CHECKED(UDeadlineCloudJob, ParameterDefinition);
				FSinglePropertyParams Params;
				auto View = FModuleManager::LoadModuleChecked<FPropertyEditorModule>("PropertyEditor")
					.CreateSingleProperty(Object, PropertyName, Params);
				if (!TestTrue(TEXT("Property view exists"), View.IsValid()))
				{
					return;
				}
				auto ValueHandle = View->GetPropertyHandle()->GetChildHandle("Parameters")->AsArray()
					->GetElement(0)->GetChildHandle("Value");
				if (!TestTrue(TEXT("Value handle exists"), ValueHandle.IsValid()))
				{
					return;
				}
				auto Widget = FDeadlineCloudDetailsWidgetsHelper::CreateJobParameterWidget(ValueHandle, Parameter);
				auto ComboWidget = FindDropdownTestWidget(Widget, TEXT("SComboBox"));
				if (!TestTrue(TEXT("Dropdown renders"), ComboWidget.IsValid()))
				{
					return;
				}
				auto Combo = StaticCastSharedPtr<SComboBox<TSharedPtr<FString>>>(ComboWidget);
				if (!TestTrue(TEXT("Saved value is selected"), Combo->GetSelectedItem().IsValid()))
				{
					return;
				}
				TestEqual(TEXT("Initial choice matches saved value"), *Combo->GetSelectedItem(), FString(TEXT("false")));
				const FKeyEvent Down(EKeys::Down, FModifierKeysState(), 0, false, 0, 0);
				ComboWidget->OnKeyDown(FGeometry(), Down);
				TestEqual(TEXT("Next template choice is selected"), *Combo->GetSelectedItem(), FString(TEXT("true")));
				const auto& StoredParameters = bMrq ? Mrq->JobTemplateOverrides.Parameters : Job->ParameterDefinition.Parameters;
				TestEqual(TEXT("Selection is stored on the owning object"), StoredParameters[0].Value, FString(TEXT("true")));

				auto Text = StaticCastSharedPtr<STextBlock>(FindDropdownTestWidget(Widget, TEXT("STextBlock")));
				if (!TestTrue(TEXT("Selection label exists"), Text.IsValid()))
				{
					return;
				}
				TestEqual(TEXT("Selected value is displayed"), Text->GetText().ToString(), FString(TEXT("true")));
				ValueHandle->SetValue(TEXT("false"));
				TestEqual(TEXT("External reset updates the display"), Text->GetText().ToString(), FString(TEXT("false")));
				TestEqual(TEXT("External reset updates the selected item"), *Combo->GetSelectedItem(), FString(TEXT("false")));
				ComboWidget->OnKeyDown(FGeometry(), Down);
				ComboWidget->OnKeyDown(FGeometry(), Down);
				TestEqual(TEXT("Empty choice is saved"), StoredParameters[0].Value, FString());
				ComboWidget->OnKeyDown(FGeometry(), Down);
				TestEqual(TEXT("Navigation stops at the last template choice"), *Combo->GetSelectedItem(), FString());

				ValueHandle->SetValue(TEXT("legacy"));
				auto LegacyWidget = FDeadlineCloudDetailsWidgetsHelper::CreateJobParameterWidget(ValueHandle, Parameter);
				TestEqual(TEXT("Construction preserves an unmatched saved value"), StoredParameters[0].Value, FString(TEXT("legacy")));
				auto LegacyCombo = StaticCastSharedPtr<SComboBox<TSharedPtr<FString>>>(
					FindDropdownTestWidget(LegacyWidget, TEXT("SComboBox")));
				TestFalse(TEXT("Unmatched value does not select a different choice"), LegacyCombo->GetSelectedItem().IsValid());

				Parameter.UserInterfaceControl = EUserInterfaceControl::LINE_EDIT;
				auto TextWidget = FDeadlineCloudDetailsWidgetsHelper::CreateJobParameterWidget(ValueHandle, Parameter);
				TestTrue(TEXT("Explicit line edit remains editable text"),
					FindDropdownTestWidget(TextWidget, TEXT("SEditableTextBox")).IsValid());
				Parameter.UserInterfaceControl = EUserInterfaceControl::DROPDOWN_LIST;
				Parameter.AllowedValues.Empty();
				auto NoChoicesWidget = FDeadlineCloudDetailsWidgetsHelper::CreateJobParameterWidget(ValueHandle, Parameter);
				TestTrue(TEXT("Missing choices retain the text editor"),
					FindDropdownTestWidget(NoChoicesWidget, TEXT("SEditableTextBox")).IsValid());
			});

			It("Recovers dropdown choices from the template for legacy parameters", [this, bMrq]()
			{
				const FString TemplatePath = FPaths::CreateTempFilename(*FPaths::ProjectSavedDir(), TEXT("Dropdown"), TEXT(".yml"));
				const FString Yaml = TEXT("parameterDefinitions:\n")
					TEXT("- name: IgnorePlugins\n  type: STRING\n  default: 'false'\n")
					TEXT("  allowedValues: ['false', 'true', '']\n");
				if (!TestTrue(TEXT("Template is saved"), FFileHelper::SaveStringToFile(Yaml, *TemplatePath)))
				{
					return;
				}
				UDeadlineCloudRenderJob* Job = NewObject<UDeadlineCloudRenderJob>();
				Job->PathToTemplate.FilePath = TemplatePath;
				FParameterDefinition Legacy;
				Legacy.Name = TEXT("IgnorePlugins");
				Legacy.Value = TEXT("true");
				Job->ParameterDefinition.Parameters = {Legacy};
				UMoviePipelineDeadlineCloudExecutorJob* Mrq = NewObject<UMoviePipelineDeadlineCloudExecutorJob>();
				Mrq->JobPreset = Job;
				Mrq->JobTemplateOverrides.Parameters = {Legacy};
				auto Rows = CreateDropdownTestRows({bMrq ? static_cast<UObject*>(Mrq) : static_cast<UObject*>(Job)});
				auto Row = FindDropdownTestRow(Rows->GetRootTreeNodes());
				IFileManager::Get().Delete(*TemplatePath);
				if (!TestTrue(TEXT("Production builder creates parameter row"), Row.IsValid()))
				{
					return;
				}
				auto ValueWidget = Row->CreateNodeWidgets().ValueWidget;
				if (!TestTrue(TEXT("Parameter widget exists"), ValueWidget.IsValid()))
				{
					return;
				}
				auto ComboWidget = FindDropdownTestWidget(ValueWidget.ToSharedRef(), TEXT("SComboBox"));
				if (!TestTrue(TEXT("Template restores dropdown rendering"), ComboWidget.IsValid()))
				{
					return;
				}
				auto Combo = StaticCastSharedPtr<SComboBox<TSharedPtr<FString>>>(ComboWidget);
				if (!TestTrue(TEXT("Saved choice is selected"), Combo->GetSelectedItem().IsValid()))
				{
					return;
				}
				TestEqual(TEXT("Template lookup preserves the saved override"), *Combo->GetSelectedItem(), FString(TEXT("true")));
				ComboWidget->OnKeyDown(FGeometry(), FKeyEvent(EKeys::Down, FModifierKeysState(), 0, false, 0, 0));
				FString Value;
				Row->CreatePropertyHandle()->GetValue(Value);
				TestEqual(TEXT("Template's empty choice saves through production row"), Value, FString());
			});
		});
	}

	It("Handles an invalid property handle without dereferencing it", [this]()
	{
		FParameterDefinition Parameter;
		Parameter.UserInterfaceControl = EUserInterfaceControl::DROPDOWN_LIST;
		Parameter.AllowedValues = {TEXT("false"), TEXT("true")};
		auto Widget = FDeadlineCloudDetailsWidgetsHelper::CreateJobParameterWidget(nullptr, Parameter);
		TestTrue(TEXT("Invalid handle renders no editor"), Widget == SNullWidget::NullWidget);
	});
}
