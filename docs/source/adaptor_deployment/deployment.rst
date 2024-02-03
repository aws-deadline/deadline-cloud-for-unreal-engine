###############################
Adaptor deployment
###############################


.. note:: The entire deployment process is described as if all the python packages are in C:/deadline

#. Deploy deadline-cloud-worker-agent step by step described in AWS developer guide.

#. Prepare to install python packages for UnrealAdaptor:

    a. cd C:/deadline

#. Install AWS packages to python:

    a. python -m pip install deadline-cloud/
    #. python -m pip install openjd-adaptor-runtime-for-python/

#. Install deadline-cloud-for-unreal package to python:

    a. cd C:/deadline/deadline-cloud-for-unreal
    #. python -m build
    #. python -m pip install dist/deadline_cloud_for_unreal-...-py3-none-any.whl

#. We recommend installing the Python version that is used in Unreal Engine (3.9.7), otherwise, there could be some missing library errors.
   For example PyWin32 library has its own dll that is built for each python version. And UnrealClient uses WinClientInterface that imports PyWin32.
   But still, if you are using a different version of Python, it makes sense to install additional libraries, such as PyWin32, in Unreal's Python in the next way:
   **"C:\Program Files\Epic Games\UE_5.2\Engine\Binaries\ThirdParty\Python3\Win64\python.exe" -m pip install pywin32**

#. Install Plugin in the Unreal Engine

    a. Go to *C:\Program Files\Epic Games\UE_5.2\Engine\Plugins\Experimental*
    #. Rename **AWS.UnrealDeadlineCloudService.Unreal** to **UnrealDeadlineCloudService**
    #. Go to UnrealDeadlineCloudService
    #. Run cmd here with the command **“git lfs --fetch all"**

#. Go to “Edit the system environment variables” in Win search bar:
    a. .. image:: /images/dev/1_env_properties.png
    #. Find the “Path” variable in the User's variables list, click “edit”
    #. Ensure that Python scripts folder and Unreal executable directory are here:
        .. image:: /images/dev/2_path_variables.png
       It's necessary to launch unreal adaptor as **UnrealAdaptor** and unreal executable as **UnrealEditor-Cmd**