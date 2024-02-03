###############################
Use Cases
###############################

******************************************
Login / Logout
******************************************

#. Go to "Edit" in the header -> "Project settings"

#. Type "deadline" in the search bar

#. Click "Login"

    .. image:: /images/user/2_login_logout.png

    a. Result

        .. image:: /images/user/3_login_clicked.png

#. Click "Logout"

    a. Result represented in Output Log ("Window" -> "Output Log" in the header)

        .. image:: /images/user/4_logout_clicked.png

******************************************
Change the WorkStation Configuration
******************************************

#. Go to "Edit" in the header -> "Project settings"

#. Type "deadline" in the search bar

#. Check AWS profile

    .. image:: /images/user/5_select_profile.png

#. Change Job History Dir

    a. By default it is ~/.deadline/job_history/<profile_name>

    #. Click on the "..." button, change the value

        .. image:: /images/user/6_history_dir.png

#. Change Default Farm

    .. image:: /images/user/7_select_farm.png

#. Change Default Queue

    .. image:: /images/user/8_select_queue.png

#. Change Default Storage Profile

    .. image:: /images/user/9_select_storage.png

#. Change Job Attachments Filesystem Options

    .. image:: /images/user/10_select_attachments_options.png

#. Change the General settings

    .. image:: /images/user/11_general_settings.png

******************************************
Create Job
******************************************

#. Go to "Window" in the header -> "Cinematics" -> "Movie Render Queue"

    .. image:: /images/user/12_open_mrq.png

#. Add render job

    .. image:: /images/user/13_add_job.png

#. Pick "TestLevelSequence"

    .. image:: /images/user/14_pick_sequence.png

#. Setup the config as "Config" (/Game/Test/Config)

    .. image:: /images/user/15_pick_config.png

#. In the config we describe "how" jobs will be processed by the Worker agent. By default, there is only "Render" step

    .. image:: /images/user/16_render_step.png

#. But you can add Custom Scripts by clicking "+ setting"

    .. image:: /images/user/17_custom_steps.png

#. And set up depends on all the steps. Test script can be found within project folder in DeadlineCloudScripts

    .. image:: /images/user/18_step_settings.png
    .. image:: /images/user/19_step_settings_2.png

#. Select Job Preset as "DeadlineCloudJobPreset"

    .. image:: /images/user/20_select_job_preset.png

#. After that step you will be able to change job settings and submit it. This case is described in the next section.

******************************************
Change Job's settings and submit the Job
******************************************

#. Job shared settings. These settings are muted by default and have default values, but should be editable by switching the state of the appropriate checkbox.

    .. image:: /images/user/21_shared_settings.png
#. Host requirements. These settings are muted by default and have default values, but should be editable by switching the state of the appropriate checkbox.

    .. image:: /images/user/22_host_reqs.png

#. Job Attachments. This section provides settings for files and directories that should be passed to render farms with the job.
   All these settings contain the common property "Show Auto-Detected" which means that predefined Unreal Assets should be in the list.
    .. image:: /images/user/23_job_attachments.png

   Should be expandable by clicking the "+" button. Should be removed by clicking the trash icon:

    a. Input Files. Additional assets to upload to the farm with the job.
    #. Input Directories. Additional folders to upload to the farm with the job.
    #. Output directories. If some directories are listed here, that means that after the job is complete, Farm workers should upload the files in these directories to the S3 bucket and we can get them after that. Usually, there is a render output folder.

#. Submit the job to the Deadline Cloud farm by clicking the "Render (Remote)" button.

    .. image:: /images/user/24_submit.png

#. Submission progress, here on any stage (start, hashing, uploading) you can cancel submission:

    .. image:: /images/user/25_submission_dialog.png

#. Submission possible results:

    a. Submission failed

        .. image:: /images/user/26_submission_failed.png

    #. Submission canceled

        .. image:: /images/user/27_submission_canceled.png

    #. Submission finished

        .. image:: /images/user/28_submission_results.png

#. After Deadline Job is created and submitted, the saved job bundle should be available at "Job History Dir" ("Edit" -> "Project settings…" -> "Deadline Cloud Workstation Configuration" -> "Profile")

******************************************
Create new Deadline Cloud job preset
******************************************

#. Right click in the Unreal "Content browser" window. And select "Miscellaneous" -> "Data Asset"

    .. image:: /images/user/29_create_new_preset.png

#. In the popup window in the search bar start typing: DeadlineCloudJobPreset. Press on the "DeadlineCloudJobPreset" row in the drop down list and click "Select".

    .. image:: /images/user/30_search_deadline_preset.png

#. Set the name of the newly created asset and double click on it

    .. image:: /images/user/31_name_and_open_preset.png

#. Here you can setup settings for the job which will be used for Deadline Cloud jobs after the asset is selected in MRQ (See "Create Job" item 8)

    .. image:: /images/user/32_edit_and_save_preset.png

#. For example, here's a new "DemoPreset" with Initial State "SUSPENDED", "Windows" OS, and "x86_64" architecture. After it's selected in MRQ for the job the settings will be applied to the submitted deadline cloud job.

    .. image:: /images/user/33_example_preset.png

#. The values of the settings can be overridden by marking them in check boxes:

    .. image:: /images/user/34_example_preset_2.png
