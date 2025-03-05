Create DeadlineCloud data assets
================================

#. In the content browser click RMB -> Miscellaneous -> Data Asset or type “data asset” in the search bar

   .. image:: /images/create_data_asset_0.png

#. Type “deadline”. Here you can see bunch of DeadlineCloud assets:

   .. image:: /images/create_data_asset_1.png

   a. Deadline Cloud Job - Basic implementation of OpenJob
   #. Deadline Cloud Render Job - OpenJob for submitting jobs from MRQ plugin
   #. Deadline Cloud Step  - Basic implementation of OpenJob Step
   #. Deadline Cloud Render Step - Specific class for Unreal Render actions script
   #. Deadline Cloud Environment - Basic implementation of OpenJob Environment
   #. Deadline Cloud Ugs Environment - Specific class for OpenJob Environment if you want to use Unreal Game Sync VCS

#. Each Data Asset (Job, Step, Environment) has a common field “Path to Template”.
   Prepared in advance templates located in **Plugins/UnrealDeadlineCloudService/Content/Python/openjd_templates**
   (**src/unreal_plugin/Content/Python/openjd_templates**)

   .. image:: /images/create_data_asset_2.png

   a. render_job.yml - Render Job template
   #. launch_ue_environment.yml - Environment that launch the UE on env enter and close it on env exit
   #. render_step.yml - Step with script that runs UE rendering
   #. ugs

       i. ugs_render_job.yml - Render Job template for UGS jobs
       #. ugs_sync_cmf_environment.yml - Environment that sync UGS workspace before render. Use for CMF render farm
       #. ugs_sync_smf_environment.yml - Environment that sync UGS workspace before render. Use for SMF render farm
       #. ugs_launch_ue_environment.yml - Environment that launch the UE for UGS jobs
       #. ugs_render_step.yml - Step with script that runs UE rendering for UGS jobs
   #. p4

       i. p4_render_job.yml - Render Job template for P4 jobs
       #. p4_sync_cmf_environment.yml - Environment that sync P4 workspace before render. Use for CMF render farm
       #. p4_sync_smf_environment.yml - Environment that sync P4 workspace before render. Use for SMF render farm
       #. p4_launch_ue_environment.yml - Environment that launch the UE for P4 jobs
       #. p4_render_step.yml - Step with script that runs UE rendering for P4 jobs
   #. custom

       i. custom_job.yml - Job template for executing custom actions
       #. custom_step.yml - Step template for executing custom python scripts with "custom" handler