Create Default Render Job
=========================

Render Step data asset
**********************

#. Select “Deadline Cloud Render Step”. Name an asset, for example “RenderStep” and open it for editing.

   .. image:: ../../images/create_render_job_0.png

#. Select **Content/Python/openjd_templates/render_step.yml**

   .. image:: ../../images/create_render_job_1.png

#. Task Parameter Definitions and Name from YAML will be loaded to data asset

   .. image:: ../../images/create_render_job_2.png

   a. Handler - specify which UnrealAdaptor’s handler will process the script commands. Handler "render" used for usual pipeline of MRQ  render **Filled automatically during the submission**
   #. QueueManifestPath - path to the serialized MRQ manifest where render job is described. **Filled automatically during the submission**
   #. TaskChunkSize - Number of shots of Level Sequence to render per OpenJob Task. Set this value according to what number of tasks you want Deadline Cloud to generate
      For example, if Level Sequence has 10 shots and TaskChunkSize = 3 that means 4 OpenJob Tasks will be introduced:

       i. Task 0 - shots 0, 1, 2
       #. Task 1 - shots 3, 4, 5
       #. Task 2 - shots 6, 7, 8
       #. Task 3 - shot 9

   #. TaskChunkId - list of chunk ids. This example will consist of 0, 1, 2, 3 (task ids). **Filled automatically during the submission**


Launch UE Environment data asset
********************************

#. Select "Deadline Cloud Environment". Name an asset, for example "LaunchUnrealEnvironment" and open it for editing.

   .. image:: ../../images/create_render_job_3.png

#. Select **Content/Python/openjd_templates/launch_ue_environment.yml**
#. Environment variables and Name from YAML will be loaded to data asset

   .. image:: ../../images/create_render_job_4.png

   a. REMOTE_EXECUTION=True - indicates that Unreal will be launched on the remote machine
      and plugin should do/don’t some specific operations


Render Job data asset
*********************

#. Select "Deadline Cloud Render Job". Name an asset, for example "RenderJob" and open it for editing.

   .. image:: ../../images/create_render_job_5.png

#. Select **Content/Python/openjd_templates/render_job.yml**
#. Parameter Definitions from YAML will be loaded to data asset

   .. image:: ../../images/create_render_job_6.png

   a. Executable - Unreal executable name to launch on render node
   #. FramesPerTask - Divide up the total number of frames to be rendered in the sequence by this value to
      determine the total number of Deadline Cloud tasks to create, with each task aiming to render this number
      of frames.

      .. note::
         When chunking a render across multiple tasks, MRQ writes one output file per task.
         For image sequences (PNG/EXR/etc.) the default ``FileNameFormat`` already includes
         ``{frame_number}``, so each task's output is unique. For video containers such as
         ``.mov`` the default format is just ``{sequence_name}`` and every task will write to
         the same filename, overwriting each other. To disambiguate, add the ``{task_index}``
         token to the MRQ Output Setting's ``FileNameFormat`` (for example
         ``{sequence_name}_{task_index}``). The submitter substitutes ``{task_index}`` at
         render time with a zero-padded per-task index.
   #. ExtraCmdArgs - Additional CMD arguments to launch Unreal executable with
   #. ExtraCmdArgsFile - Specific file parameter where **ExtraCmdArgs** will be stored.
      Need to avoid **1024 chars limit** on **STRING** parameter. **Filled automatically during the submission**
   #. ProjectFilePath - Local path of the current Unreal Project. **Filled automatically during the submission**

#. Configure Job Shared Settings, Host Requirements and Job Attachments if needed

   .. image:: ../../images/create_render_job_7.png

#. Add “RenderStep” and “LaunchUnrealEnvironment” assets in appropriate fields

   .. image:: ../../images/create_render_job_8.png
   .. image:: ../../images/create_render_job_9.png

#. Final state of the DeadlineCloud Render Job

   .. image:: ../../images/create_render_job_10.png
