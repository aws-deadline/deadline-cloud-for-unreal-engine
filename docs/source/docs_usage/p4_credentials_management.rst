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

#. If you have a CMF farm, where all workers are inside a network that is not accessible from the outside,
   then you can use a single P4 admin user on all workers, changing only ``P4PORT`` if necessary.
   Optionally, you can pass the credentials within the Job Environment.
#. If you are concerned about data security or you are using SMF, then the best solution is to create
   a queue environment where you can set up variables for the connection: ``P4PORT``, ``P4USER``, ``P4PASSWD``.
