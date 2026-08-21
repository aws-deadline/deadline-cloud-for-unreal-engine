Submit Job from Movie Render Queue
==================================

To submit DeadlineCloud Job from Movie Render Queue, follow next steps:

#. Go to "Window" > "Cinematics" > "Movie Render Queue"
#. Select Level Sequence to render

  .. image:: ../../images/submit_job_0.png

#. Set "Job Preset" as created DeadlineCloud Render Job data asset

  .. image:: ../../images/submit_job_1.png

#. Name of the OpenJob will be set as one of the next parameters by next priority

   a. MRQ Job Preset Overrides

      .. image:: ../../images/submit_job_2.png

   #. DeadlineCloudJob Job Shared Settings

      .. image:: ../../images/submit_job_3.png

   #. Name from YAML

      .. image:: ../../images/submit_job_4.png

   #. MRQ Job name (shot name)

      .. image:: ../../images/submit_job_5.png

#. Update parameters in Preset Overrides if needed

   a. Use **Profiling Settings** to enable Unreal Insights CPU, GPU, or Memory tracing.
   #. Enable **CSV Profiler** to capture CSV output and adjust **CSV Capture Frames** if needed.
   #. Enable **MemReport** to request ``MemReport -full`` after render completion.
   #. The submitter automatically adds the required Unreal launch arguments and profiling output directories for these options.
   #. Remote profiling artifacts are uploaded with the job outputs through Job Attachments. They are written to Unreal's native ``<Project>/Saved/Profiling`` directory, independent of the configured MRQ output directory: Insights traces under ``Saved/Profiling/DeadlineCloud``, CSV output under ``Saved/Profiling/CSV``, and MemReport output under ``Saved/Profiling/MemReports``.
   #. Insights produces one startup trace for project initialization and a separate trace for each render task.

#. Click “Render (Remote)” button
