.. _p4-credentials-management:

How To Manage Perforce Credentials in P4 and UGS Jobs
=====================================================

P4 Credentials Basics
*********************

Perforce follows a priority system for retrieving connection settings, including Port, User,
Client (Workspace), and Password:

#. Connection parameters in any framework for P4 (``p4python.P4`` for example)
#. User/System OS environment variables: ``P4PORT``, ``P4USER``, ``P4CLIENT``, ``P4PASSWD``
#. Windows registry: ``HKEY_LOCAL_MACHINE\SOFTWARE\Perforce\Environment`` (system-wide settings) or
   ``HKEY_CURRENT_USER\SOFTWARE\Perforce\Environment`` (user-specific settings)

So if you have next environment:

* ``%P4PORT%`` is ``ssl:perforce.from.env:1666``
* ``HKEY_CURRENT_USER\SOFTWARE\Perforce\Environment:P4PORT`` is ``ssl:perforce.from.registry:1666``
* ``HKEY_CURRENT_USER\SOFTWARE\Perforce\Environment:P4USER`` is ``user.from.registry``
* ``HKEY_CURRENT_USER\SOFTWARE\Perforce\Environment:P4PASSWD`` is ``password.from.registry``
* Connection parameter ``password`` is ``password.from.connection``

the new connection will be configured as:

.. code-block::

   Port = ssl:perforce.from.env:1666
   User = user.from.registry
   Password = password.from.connection

Use AWS Secrets Manager
***********************

AWS Secrets Manager allows you to store and manage secrets, such as connection credentials,
in a secure, highly available, and easily managed service. All workers in your fleet (CMF or SMF)
can access it if you have configured roles and access across workers in your farm.

.. note:: You should configure the access for action ``secretsmanager:GetSecretValue`` for the worker in the queue.
   For more information visit `Manage access to Windows job user secrets`_. In general, a request to configure access looks like this:

   .. code-block:: json

      {
        "Version" : "2012-10-17",
        "Statement" : [
          //...
          {
            "Effect" : "Allow",
            "Action" : "secretsmanager:GetSecretValue",
            "Resource" : [
              "arn:aws:secretsmanager:<your_region>:<your_resource_account>:secret:<your_secret_id_or_wildcard>"
          }
          //...
        ]
      }

.. _Manage access to Windows job user secrets: https://docs.aws.amazon.com/deadline-cloud/latest/developerguide/manage-access-windows-secrets.html#grant-access

To make worker apply connection credentials from AWS Secrets Manager, you need to provide the
name of the secret in the ``AWS_SECRET_P4INFO`` environment variable in any P4 (UGS) Sync Environment you use.
Or create the new Environment template and prepend it to your Job.

.. code-block:: yaml

   name: P4SyncCmf
   variables:
     AWS_SECRET_P4INFO: DeadlineCloud/MyFleet/P4INFO

.. note:: If ``AWS_SECRET_P4INFO`` value is empty, applying connections from Secrets Manager will be skipped

Secret ``DeadlineCloud/MyFleet/P4INFO`` may contains any of the following key/value pairs:

#. P4PORT - Perforce server port
#. P4USER - Perforce user
#. P4PASSWD - Perforce password

.. note:: The names of the keys should be exactly the same
   as the P4 connection parameters, i. e. ``P4PORT``, ``P4USER``, ``P4PASSWD``

For example, you have next P4 Sync Environment:

.. code-block:: yaml

   name: P4SyncCmf
   variables:
     AWS_SECRET_P4INFO: DeadlineCloud/MyFleet/P4INFO
     P4USER: j.doe
     P4PORT: ssl:my-perforce.com:1666
   ...

And the secret ``DeadlineCloud/MyFleet/P4INFO`` contains:

#. P4PASSWD = MyVeRyS3cretP4ssW0rd
#. P4USER = aws-admin-user

Environment variables from AWS Secrets Manager will override the ones from the Job. Configured connection
parameters will be:

.. code-block::

   Port = ssl:my-perforce.com:1666
   User = aws-admin-user
   Password = MyVeRyS3cretP4ssW0rd

User appears twice - in Job environment and in AWS Secrets Manager, but last one take precedence.

In UGS case you need to prepend to the Job's environments data asset for applying P4 secrets -
``src/unreal_plugin/Content/OpenJD_DataAssets/Render/OpenJD_Environment_ApplyP4Secrets.uasset`` -
which is referencing to ``src/unreal_plugin/Content/Python/openjd_templates/p4/p4_apply_secrets_environment.yml``:

.. literalinclude:: ../../../src/unreal_plugin/Content/Python/openjd_templates/p4/p4_apply_secrets_environment.yml
    :language: yaml
    :linenos:

.. warning:: This environment apply P4 credentials from AWS Secretes Manager by printing them to the Job log
   with prefix ``openjd_env:``. Please, see `OpenJD Environment`_ documentation about sharing new
   environment variables across actions and other environments in runtime.

   **Consider adding a CloudWatch data protection policy to your account if you'll be echoing***
   **sensitive information. For example, this will apply a global policy to your CloudWatch logs**
   **which suppresses "openjd_env": lines which appear to be setting environment variables:**

   .. literalinclude:: ../resources/logs_policy_example.sh
    :language: sh
    :linenos:

   For more information and options please see `Custom data identifiers`_

.. _OpenJD Environment: https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/wiki/2023-09-Template-Schemas.md#4-environment
.. _Custom data identifiers: https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL-custom-data-identifiers.html

You can override ``AWS_SECRET_P4INFO`` value in MRQ Slate UI (Environments overrides block) or update its value
in the ``src/unreal_plugin/Content/Python/openjd_templates/p4/p4_apply_secrets_environment.yml`` file.

Pass Connection Credentials within the Job Environment
******************************************************

You can pass connection credentials within the Job Environment where the workspace creation
happens, for example in P4SyncCmf (``src/unreal_plugin/Content/Python/openjd_templates/p4/p4_sync_cmf_environment.yml``),
UGSSyncCmf (``src/unreal_plugin/Content/Python/openjd_templates/ugs/ugs_sync_cmf_environment.yml``), same for SMF case.
Or create the new Environment template and prepend it to your Job.

.. code-block:: yaml

   name: P4SyncCmf
   variables:
     P4PORT: ssl:my-perforce.com:1666
     P4USER: j.doe
     P4PASSWD: MyVeRyS3cretP4ssW0rd


Use single admin user in P4 across all of the workers
*****************************************************

It is also common practice to create an admin P4 user for render nodes with a non-expiring connection
to eliminate the need to pass secret data such as password and user.

.. note:: This solution may only be suitable for CMF farms where worker hosts exist permanently and
   can be configured via group policies.

In this case, a single admin P4 user can be used to connect to all P4 servers, including the
Commit (Master) and Edge servers where the project depot is accessible.

Therefore, it is recommended to pass only the port to connect to, if default on is not configured on workers:

.. code-block:: yaml

   name: P4SyncCmf
   variables:
     P4PORT: ssl:my-perforce.com:1666


Configure Deadline Cloud Queue Environment
******************************************

According to `Deadline Cloud Developer Guide`_ the Queue Environment is a set of environment variables
and commands that set up fleet workers. You can use queue environments to provide software applications,
**environment variables**, and other resources to jobs in the queue.

You can add the new Queue Environment from the DeadlineCloudMonitorApp or from the console by following
the `Deadline Cloud Queue Environments Git sample`_:

.. code-block:: yaml

   # file://p4_credentials.yaml

   name: P4Credentials
   variables:
     P4PORT: ssl:my-perforce.com:1666
     P4USER: j.doe
     P4PASSWD: MyVeRyS3cretP4ssW0rd

.. code-block:: bash

   # CLI command

   aws deadline create-queue-environment \
    --farm-id FARM_ID \
    --queue-id QUEUE_ID \
    --priority 1 \
    --template-type YAML \
    --template file://p4_credentials.yaml

.. _Deadline Cloud Developer Guide: https://docs.aws.amazon.com/deadline-cloud/latest/userguide/create-queue-environment.html
.. _Deadline Cloud Queue Environments Git sample: https://github.com/aws-deadline/deadline-cloud-samples/tree/mainline/queue_environments


Conclusions
***********

#. Perforce connection credentials can be stored in centralized location in Secrets Manager from a
   secret your workers will retrieve at runtime. Be aware that with UGS this method currently
   requires exposing these credentials to your job logs in your account. Consider using a data
   protection policy to hide them. This will work for both CMF and SMF.
#. If you have a CMF farm, where all workers are inside a network that is not accessible from the outside,
   then you can use a single P4 admin user on all workers, changing only ``P4PORT`` if necessary.
   Optionally, you can pass the credentials within the Job Environment.
#. If you are concerned about data security or you are using SMF, then the best solution is to create
   a queue environment where you can set up variables for the connection: ``P4PORT``, ``P4USER``, ``P4PASSWD``.