Create P4 Render Job
======================

To submit MRQ Job from Unreal Project under Perforce repository you need to meet next requirements:
   1. Unreal Project should lay under the P4 workspace
   #. Check that your current P4 connection is established and you’re logged in P4

P4 Render Job structure is pretty same as Default Render Job but contains extra Environments

   * Render Job (**Deadline Cloud Render Job**) - entrypoint

      * Environments

         * CMF/SMF Sync Environment (**Deadline Cloud P4 Environment**) - executes initialize and
           sync of P4 repo on the worker node
         * Launch UE Environment (**Deadline Cloud Environment**) - starts UE on the worker nodes

      * Steps

         * Render Step (**Deadline Cloud Render Step**) - executes main render process

P4 Render Step data asset
**************************

#. Select same "Deadline Cloud Render Step" and name asset "P4RenderStep" for example
#. Select **Content/Python/openjd_templates/p4/p4_render_step.yml**
#. This YAML has the same content as default render step. It is in the **p4** folder just for convenience.


CMF/SMF Sync Environment data asset
***********************************

#. Select "Deadline Cloud Perforce Environment". Name an asset, for example "P4SyncCmfEnvironment" (SyncSmf) and open it for editing

   .. image:: /images/create_p4_render_job_0.png

#. Select **Content/Python/openjd_templates/p4/p4_sync_cmf_environment.yml** (**p4_sync_smf_environment.yml**)
#. Environment variables and Name from YAML will be loaded to data asset

   .. image:: /images/create_p4_render_job_1.png

   a. P4_CLIENTS_ROOT_DIRECTORY - path where all the workspaces should be created on the render node

P4 Launch UE Environment data asset
************************************

#. Select same "Deadline Cloud Environment" and name asset "P4LaunchUnrealEnvironment" for example
#. Select **Content/Python/openjd_templates/p4/p4_launch_ue_environment.yml**
#. This YAML has the same content as default launch ue environment,
   but project and executable paths have prefix %P4_CLIENT_DIRECTORY% that is environment variables
   set by P4 Sync Cmf (Smf) Environment that points to root of P4 workspace to work within

P4 Render Job data asset
*************************

#. Select same "Deadline Cloud Render Job" and name asset "P4RenderJob" for example
#. Select **Content/Python/openjd_templates/p4/p4_render_job.yml**
#. Parameter Definitions from YAML will be loaded to data asset

   .. image:: /images/create_p4_render_job_2.png

   a. ProjectRelativePath - Local path of the current Unreal Project relative to P4 workspace root.
      **Filled automatically during the submission**
   #. ProjectName - Unreal project name needed for P4 workspace creation on render node.
      **Filled automatically during the submission**
   #. PerforceChangelistNumber - P4 changelist number to sync the workspace to on the render node.
      **Filled automatically during the submission**
   #. ExtraCmdArgs - Additional CMD arguments to launch Unreal executable with
   #. ExtraCmdArgsFile - Specific file parameter where **ExtraCmdArgs** will be stored.
      Need to avoid **1024 chars limit** on **STRING** parameter.
      **Filled automatically during the submission**
   #. Executable - Unreal executable name to launch on render node
   #. MrqJobDependenciesDescriptor - Path to JSON file with all MRQ job dependencies to sync on render node.
      Since some dependencies can be a type of "Soft Reference", links to they on render node will be None
      if they don't exist on the disk. Therefore its necessary to collect them locally.
      **Filled automatically during the submission**
   #. PerforceWorkspaceSpecificationTemplate - P4 Client specification (Name, Root, Stream and View properties)
      with workspace name replaced with token **{workspace_name}** to make it possible to create similar workspaces
      on other machines, such as render node.

#. Set environments in this order:

   a. CMF/SMF Sync Environment
   #. Launch UE Environment

#. Add render step
#. Final state of P4 Render Job data asset

   .. image:: /images/create_p4_render_job_3.png
