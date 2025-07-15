Create UGS Render Job
======================

.. note:: Before creating the UGS jobs, please refer to :ref:`p4-credentials-management` to see
          how to set up/pass P4 credentials on your workers fleet

To submit MRQ Job from Unreal Project under UGS repository you need to meet next requirements:
   1. Unreal Project should lay under the P4 workspace (UGS repository)
   #. Unreal Project should be launched with the Unreal Editor executable under the P4 Workspace (UGS repository).
      Mostly, it’s under the **<repo_root>/Engine** or **<repo_root>/UE5/Engine** directory
   #. Check that your current P4 connection is established and you’re logged in P4

.. note::
   Example structure of P4 Workspace

   .. image:: ../../images/create_ugs_render_job_0.png

UGS Render Job structure is pretty same as Default Render Job but contains extra Environments

   * Render Job (**Deadline Cloud Render Job**) - entrypoint

      * Environments

         * CMF/SMF Sync Environment (**Deadline Cloud Ugs Environment**) - executes initialize and
           sync of UGS repo on the worker node
         * Launch UE Environment (**Deadline Cloud Environment**) - starts UE on the worker nodes

      * Steps

         * Render Step (**Deadline Cloud Render Step**) - executes main render process

UGS Render Step data asset
**************************

#. Select same "Deadline Cloud Render Step" and name asset "UgsRenderStep" for example
#. Select **Content/Python/openjd_templates/ugs/ugs_render_step.yml**
#. This YAML has the same content as default render step. It is in the **ugs** folder just for convenience.


CMF/SMF Sync Environment data asset
***********************************

#. Select "Deadline Cloud Ugs Environment". Name an asset, for example "UgsSyncCmfEnvironment" (SyncSmf) and open it for editing

   .. image:: ../../images/create_ugs_render_job_1.png

#. Select **Content/Python/openjd_templates/ugs/ugs_sync_cmf_environment.yml** (**ugs_sync_smf_environment.yml**)
#. Environment variables and Name from YAML will be loaded to data asset

   .. image:: ../../images/create_ugs_render_job_2.png

   a. P4_CLIENTS_ROOT_DIRECTORY - path where all the workspaces should be created on the render node

UGS Launch UE Environment data asset
************************************

#. Select same "Deadline Cloud Environment" and name asset "UgsLaunchUnrealEnvironment" for example
#. Select **Content/Python/openjd_templates/ugs/ugs_launch_ue_environment.yml**
#. This YAML has the same content as default launch ue environment,
   but project and executable paths have prefix %P4_CLIENT_DIRECTORY% that is environment variables
   set by Ugs Sync Cmf (Smf) Environment that points to root of P4 workspace to work within

UGS Render Job data asset
*************************

#. Select same "Deadline Cloud Render Job" and name asset "UgsRenderJob" for example
#. Select **Content/Python/openjd_templates/ugs/ugs_render_job.yml**
#. Parameter Definitions from YAML will be loaded to data asset

   .. image:: ../../images/create_ugs_render_job_3.png

   a. ProjectRelativePath - Local path of the current Unreal Project relative to P4 workspace root.
      **Filled automatically during the submission**
   #. ProjectName - Unreal project name needed for P4 workspace creation on render node.
      **Filled automatically during the submission**
   #. PerforceStreamPath - P4 stream path (e.g. //MyProject/Mainline) needed for P4 workspace creation on render node.
      **Filled automatically during the submission**
   #. ExecutableRelativePath - Local path of the currently running UE executable relative to the P4 workspace root.
      **Filled automatically during the submission**
   #. PerforceChangelistNumber - P4 changelist number to sync the workspace to on the render node.
      **Filled automatically during the submission**
   #. ExtraCmdArgs - Additional CMD arguments to launch Unreal executable with
   #. ExtraCmdArgsFile - Specific file parameter where **ExtraCmdArgs** will be stored.
      Need to avoid **1024 chars limit** on **STRING** parameter.
      **Filled automatically during the submission**
   #. Executable - Unreal executable name to launch on render node

#. Set environments in this order:

   a. CMF/SMF Sync Environment
   #. Launch UE Environment

#. Add render step
#. Final state of UGS Render Job data asset

   .. image:: ../../images/create_ugs_render_job_4.png
