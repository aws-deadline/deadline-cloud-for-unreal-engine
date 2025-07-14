Check Parameters Consistency
============================

The plugin allows you to check consistency of the parameters of Step, Job parameters and
variables of Environment while editing the data asset and submitting the Job.

Parameter is **consistent** if its **name** and **type** are the same in the YAML and Data Asset.

Environment Variable is **consistent** if its **name** is the same in the YAML and Data Asset.

That means consistency check failed if:

#. YAML parameter missed in data asset parameters list
#. Data asset parameter missed in YAML parameters list
#. YAML/Data asset parameters with the same name have different type (only for Job and Step)

Check consistency while editing the Data Asset
**********************************************

#. Create new DeadlineCloud Job data asset, select the YAML template for it, save and close it

   .. image:: ../../images/consistency_check_0.png

#. Open that YAML in any text editor and add/remove some parameter to/from **parameterDefinitions** list

   .. image:: ../../images/consistency_check_1.png

#. Open DeadlineCloud Job data asset. You will see the warning message and fix button

   .. image:: ../../images/consistency_check_2.png

#. Click "OK" button to fix the parameters. YAML parameters have the priority on the Data Asset's ones, and
   Fix affect only the data asset parameters, so the fix logic is:
      a. If YAML parameter missed in Data Asset, it will be added
      #. If Data Asset parameter missed in YAML, it will be removed
      #. If parameter in both sources have same **name** but different **types**,
         it will be removed and same YAML parameter will be added
      #. All of the values of added parameters will be empty or equal to **default** described in YAML

   .. image:: ../../images/consistency_check_3.png


Check consistency while submitting
**********************************

#. Create new Job in MRQ widget, select you prepared DeadlineCloud Job data asset and click **Render (Remote)** button
#. You will see the warning message and submission will be aborted

   .. image:: ../../images/consistency_check_4.png
