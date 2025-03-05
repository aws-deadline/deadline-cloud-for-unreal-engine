Create Unreal OpenJob from Python
=================================


OpenJob Python classes
**********************

Package ``deadline.deadline.unreal_submitter.unreal_open_job.unreal_open_job``
contains next OpenJob implementations:

#. ``UnrealOpenJob`` - Base class of OpenJob for Unreal Engine
#. ``RenderUnrealOpenJob`` - **Predefined\*** class for Render OpenJobs
#. ``UgsRenderUnrealJob`` - **Predefined\*** class for Render OpenJobs in UGS pipeline

OpenJob Step Python classes
***************************

Package ``deadline.deadline.unreal_submitter.unreal_open_job.unreal_open_job_step``
contains next OpenJobStep implementations:

#. ``UnrealOpenJobStep`` - Base class of OpenJob Step for Unreal Engine
#. ``RenderUnrealOpenJobStep`` - **Predefined\*** class for Render OpenJob Steps
#. ``UgsRenderUnrealJobStep`` - **Predefined\*** class for Render OpenJob Steps in UGS pipeline

OpenJob Environment Python classes
**********************************

Package ``deadline.deadline.unreal_submitter.unreal_open_job.unreal_open_job_environment``
contains next OpenJob implementations:

#. ``UnrealOpenJobEnvironment`` - Base class of OpenJob Environment for Unreal Engine
#. ``LaunchEditorUnrealOpenJobEnvironment`` - **Predefined\*** class for OpenJob Environment that launches Unreal Engine on Env enter
#. ``UgsSyncCmfUnrealOpenJobEnvironment`` - **Predefined\*** class for OpenJob Environment in UGS pipeline
   that executes syncing UGS workspace. Should be used on Customer-Managed Fleets
#. ``UgsSyncSmfUnrealOpenJobEnvironment`` - **Predefined\*** class for OpenJob Environment in UGS pipeline
   that executes syncing UGS workspace. Should be used on Service-Managed Fleets

.. note::
   All classes marked as **Predefined\*** has class variable ``default_template_path``
   that points to the path to YAML template relative to path set in environment variable ``OPENJD_TEMPLATES_DIRECTORY``.
   By default ``OPENJD_TEMPLATE_DIRECTORY`` points to **Content/Python/openjd_templates** subfolder of the Plugin.

   That means it is not necessary to select YAML templates for each predefined entities and submit as is.

OpenJob Submitter Python classes
********************************

Package ``deadline.deadline.unreal_submitter.submitter``
contains next submitters to execute OpenJob submission:

#. ``UnrealSubmitter`` - base class that implement the main submission logic
#. ``UnrealOpenJobDataAssetSubmitter`` - implement submission of OpenJob from ``unreal.DeadlineCloudJob`` data assets
#. ``UnrealMrqJobSubmitter`` - implement submission of OpenJob from ``unreal.MoviePipelineDeadlineCloudExecutorJob`` which have OpenJob preset
#. ``UnrealOpenJobSubmitter`` - implement submission of OpenJob from python ``UnrealOpenJob`` instance
#. ``UnrealRenderOpenJobSubmitter`` - implement submission of OpenJob from python ``UnrealRenderOpenJob`` instance

Unreal OpenJob structure
************************

.. code-block:: python

   job = UnrealOpenJob(
       steps=[
           UnrealOpenJobStep(
               extra_parameters=[
                   UnrealOpenJobStepParameterDefinition("ParamName", "INT", [10])
               ],
               environments=[
                   UnrealOpenJobEnvironment({"VAR_NAME": "var_value"})
               ],
               step_dependencies=["OtherStepName"]
           )
       ],
       environments=[
           UnrealOpenJobEnvironment({"VAR_NAME": "var_value"})
       ],
       extra_parameters=[
           UnrealOpenJobParameterDefinition("ParamName", "STRING", "foo")
       ]
   )

.. note::
   This is general structure and may be configured according to dev goals.
   For more information about Unreal OpenJob entities and their fields please read the docstrings

You can find more information about creating and submitting Unreal Open Jobs from Python
on relevant pages in this section.