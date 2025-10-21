# Perforce Credentials Management

This guide covers secure credential management for integrating Perforce with AWS Deadline Cloud workers.

## Overview

There are several approaches to configure Perforce credentials for Deadline Cloud workers. Each method has different security implications and use cases:

| Method | Security Level | Deployment Support | Recommended Use |
|--------|---------------|-------------------|-----------------|
| **AWS Secrets Manager** | ✅ High | SMF + CMF | **Production (Recommended)** |
| Job environment variables | ⚠️ Low | SMF + CMF | Development/Testing only |
| Queue environment variables | ⚠️ Low | SMF + CMF | Development/Testing only |
| Windows registry | 🔶 Medium | CMF only | Legacy CMF setups |
| Pre-configured admin user | 🔶 Medium | CMF only | Simplified CMF setups |

> **🔒 Security Recommendation**: Use AWS Secrets Manager for production environments. It provides centralized, encrypted credential storage with audit trails and works with both SMF and CMF deployments.

The following sections detail each approach.

## P4 Credentials Basics

To retrieve connection settings, including Perforce server URL and port, username, and password, Perforce follows the following priority:

1. Connection parameters in any framework for Perforce (P4) (`p4python.P4` for example)
2. User/System environment variables: `P4PORT`, `P4USER`, `P4CLIENT`, `P4PASSWD`
3. Windows registry: `HKEY_LOCAL_MACHINE\SOFTWARE\Perforce\Environment` (system-wide settings) or
   `HKEY_CURRENT_USER\SOFTWARE\Perforce\Environment` (user-specific settings)

With these priorities, if you have the following setup:

* Connection parameter `password` is `password.from.connection`
* Environment variable `%P4PORT%` is `ssl:perforce.from.env:1666`
* Windows registry `HKEY_CURRENT_USER\SOFTWARE\Perforce\Environment:P4PORT` is `ssl:perforce.from.registry:1666`
* Windows registry `HKEY_CURRENT_USER\SOFTWARE\Perforce\Environment:P4USER` is `user.from.registry`
* Windows registry `HKEY_CURRENT_USER\SOFTWARE\Perforce\Environment:P4PASSWD` is `password.from.registry`

The resulting Perforce connection will be:

```text
Port = ssl:perforce.from.env:1666
User = user.from.registry
Password = password.from.connection
```

## AWS Secrets Manager (Recommended)

> **🔒 Production Ready**: This is the recommended approach for managing Perforce credentials in production environments.

AWS Secrets Manager provides the most secure and scalable solution for both CMF and SMF deployments.

### Benefits

- **🔐 Centralized Security**: Store all P4 credentials in one encrypted location
- **🚫 No Credential Exposure**: Credentials never appear in job configurations or logs
- **🔄 Automatic Rotation**: Support credential rotation without job reconfiguration
- **📊 Audit Trails**: Track credential access and usage
- **🌐 Universal Support**: Works with both CMF and SMF deployments
- **🔍 Log Redaction**: Connection credentials automatically redacted in job logs

### Step 1: Create a Secret in AWS Secrets Manager

Create a secret containing your Perforce connection parameters:

**Required Key-Value Pairs:**
- `P4PORT` - Perforce server URL and port
- `P4USER` - Perforce username  
- `P4PASSWD` - Perforce password

> **⚠️ Important**: Key names must exactly match P4 connection parameters to work with `deadline-cloud-for-unreal-engine`.

**Example Secret:**
```json
{
   "P4PORT": "ssl:your-perforce-server.com:1666",
   "P4USER": "your-perforce-username",
   "P4PASSWD": "your-perforce-password"
}
```

**To create the secret:**
1. Open the AWS Secrets Manager console
2. Choose "Store a new secret"
3. Select "Other type of secret"
4. Enter the key-value pairs above
5. Name your secret (e.g., `deadline-cloud-p4-credentials`)
6. Complete the creation process

### Step 2: Grant Worker Access to the Secret

Workers need `secretsmanager:GetSecretValue` permission to access the secret. This follows the same pattern as [managing Windows job user secrets](https://docs.aws.amazon.com/deadline-cloud/latest/developerguide/manage-access-windows-secrets.html#grant-access).

**To grant access:**

1. Open the AWS Secrets Manager console and navigate to your secret
2. In the "Resource permissions" section, add this policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "QUEUE_ROLE_ARN"
      },
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "*"
    }
  ]
}
```

3. Replace `QUEUE_ROLE_ARN` with your actual queue role ARN
4. Save the policy

> **📝 Note**: Save the secret name - you'll need it when configuring P4 render jobs. See [Create Perforce Render Job](./create-perforce-render-job.md) for next steps.

## Job Environment Variables

> **⚠️ Security Warning**: This approach is **not recommended for production** as it exposes credentials in job configurations and logs. Use AWS Secrets Manager for production environments.

You can pass connection credentials within the Job Environment where workspace creation happens, 
for example in [p4_sync_smf_environment](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/blob/mainline/src/unreal_plugin/Content/Python/openjd_templates/p4/p4_sync_smf_environment.yml),
[ugs_sync_smf_environment](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/blob/mainline/src/unreal_plugin/Content/Python/openjd_templates/ugs/ugs_sync_smf_environment.yml) or similar environments for CMF.
Alternatively, create a new Environment template and prepend it to your Job.

```yaml
name: P4Credentials
variables:
  P4PORT: ssl:my-perforce.com:1666
  P4USER: j.doe
  P4PASSWD: MyVeRyS3cretP4ssW0rd
```

**Security Risks:**

* Credentials are visible in job configurations
* Passwords may appear in logs (not automatically redacted)
* No centralized credential management
* Difficult to rotate credentials

## Queue Environment Variables

> **⚠️ Security Warning**: This approach is **not recommended for production** as it stores credentials in queue configurations. Use AWS Secrets Manager for secure credential management.

Per [Deadline Cloud Developer Guide](https://docs.aws.amazon.com/deadline-cloud/latest/userguide/create-queue-environment.html), 
you can use queue environments to provide software applications, environment variables, and other resources to jobs in the queue. 
Queue environment samples can be found in the [queue_environments folder in deadline-cloud-samples](https://github.com/aws-deadline/deadline-cloud-samples/tree/mainline/queue_environments).

### Add queue environment using Deadline Cloud Monitor (DCM) App or console

1. Open Deadline Cloud Monitor (DCM) App or AWS console
2. Navigate to the farm and queue you are working with
3. Select "Queue environments" tab
4. Click on "Action" and select "Create new with YAML"
5. Add the following and save:

```yaml
specificationVersion: environment-2023-09
name: P4Credentials
variables:
   P4PORT: ssl:my-perforce.com:1666
   P4USER: j.doe
   P4PASSWD: MyVeRyS3cretP4ssW0rd
```

### Add queue environment using CLI

1. Create `p4_credentials.yaml` file with the sample above
2. Run the following CLI command:

```bash
aws deadline create-queue-environment \
 --farm-id FARM_ID \
 --queue-id QUEUE_ID \
 --priority 1 \
 --template-type YAML \
 --template file://p4_credentials.yaml
```

## Windows Registry (CMF Only)

> **🔶 CMF Only**: This solution is **only suitable for CMF** where you can configure worker hosts directly. **For SMF deployments, use AWS Secrets Manager.**

Windows registry provides local credential storage on worker machines. This method uses the standard Perforce priority system where credentials are stored in:

* `HKEY_LOCAL_MACHINE\SOFTWARE\Perforce\Environment` (system-wide settings)
* `HKEY_CURRENT_USER\SOFTWARE\Perforce\Environment` (user-specific settings)

This approach is only suitable for CMF deployments where you have direct access to configure worker machines.

## Pre-configured Admin User (CMF Only)

> **🔶 CMF Only**: This solution is **only suitable for CMF** where you can configure worker hosts directly. **For SMF deployments, use AWS Secrets Manager.**

Create a dedicated P4 user for render nodes with a non-expiring connection to eliminate the need to pass secret data such as usernames and passwords.
In this case, a single dedicated P4 user can be used to connect to all P4 servers, including the Commit (Master) and Edge servers where the project depot is accessible.

Therefore, you only need to pass the port to connect to, if the default is not configured on workers. This can be achieved by adding the following in job environment or queue environment similar to steps documented above:

```yaml
name: P4Sync
variables:
  P4PORT: ssl:my-perforce.com:1666
```
