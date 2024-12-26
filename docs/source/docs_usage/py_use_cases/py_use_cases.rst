How To create, configure and submit Jobs, Steps, Environments from Python
=========================================================================

Examples of the submission from Unreal Python located in **Content/Python/submit_actions**:

#. **render_job_submission.py** - submit default Render Job using S3 to transfer project files
#. **ugs_render_job_submission.py** - submit Render Job using UGS to transfer project files
#. **custom_job_submission.py** - submit custom Job with **custom_script.py** to execute

.. toctree::
   :maxdepth: 1

   py_submission_general
   py_submit_render_job
   py_submit_ugs_render_job
   py_submit_p4_render_job
   py_submit_custom_job