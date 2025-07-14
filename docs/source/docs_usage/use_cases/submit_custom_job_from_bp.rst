Submit Custom Job from Editor Utility Widget
============================================

Plugin provide the ability to submit custom jobs to DeadlineCloud farm via Editor Utility Widgets.
As an example, we add the simple submitter that allows to select python script to execute on the
render node within Unreal Engine session.

#. Check if **Show Plugin Content** is enabled in **Content Browser Settings**

   .. image:: ../../images/submit_render_bp_0.png

#. Find **DeadlinePathSelector** in **All/Plugins/UnrealDeadlineCloudServiceContent/Widgets**

   .. image:: ../../images/submit_custom_bp_0.png

#. Right-click on this file and select **Run Editor Utility Widget**. You will see the UI of Blueprint Submitter

   .. image:: ../../images/submit_custom_bp_1.png

#. Select path to the Python script to execute. As an example, we prepare script **Content/Python/submit_actions/custom_script.py**
   and click "Submit" button

   .. image:: ../../images/submit_custom_bp_2.png
