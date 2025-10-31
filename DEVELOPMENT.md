# Development documentation

This package has two active branches:
- `mainline` -- For active development. This branch is not intended to be consumed by other packages. Any commit to this branch may break APIs, dependencies, and so on, and thus break any consumer without notice.
- `release` -- The official release of the package intended for consumers. Any breaking releases will be accompanied with an increase to this package's interface version.

## Build and Install the Plugin, Submitter, and Adapter

Full instructions for building and installing these packages and the necessary dependencies to act as a submitter and/or worker can be found in [Submitter Setup Guide](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/blob/mainline/docs/user_guide/setup-submitter.md) and [CMF Worker Setup Guide](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/blob/mainline/docs/user_guide/setup-cmf-worker.md).  Use the "mainline" branch for development rather than "release", and if you plan on submitting pull requests work out of [a fork](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/blob/mainline/CONTRIBUTING.md#contributing-via-pull-requests).


## Build / Test / Release

### Build the python packages

```bash
hatch build
```

### Run tests

```bash
hatch run test
```

### Run E2E tests

End to end tests validate a more complete render job workflow than our unit tests.  They create associated test resouces and attempt to submit and run jobs locally.

```bash
hatch run e2e -s
```

### Run linting

```bash
hatch run lint
```

### Run formatting

```bash
hatch run fmt
```

### Run tests for all supported Python versions

```bash
hatch run all:test
```

### Testing C++ Changes

When making C++ changes before testing you'll need to rebuild and copy your modified plugin to your Unreal plugins folder following [these steps](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/blob/mainline/docs/user_guide/setup-submitter.md#build-the-plugin) OR run the end to end tests (hatch run e2e -s) which builds and install both the C++ and python code.


### Testing Python Changes

When making changes to the Python submitter you'll need to rebuild and install your .whl file, adjusting paths to your local installation:

```
// Install hatch if not yet installed
pip install hatch
hatch build
"C:\Program Files\Epic Games\UE_5.5\Engine\Binaries\ThirdParty\Python3\Win64\python" -m pip install dist\deadline_cloud_for_unreal_engine-0.2.2.post21-py3-none-any.whl --target "C:\Program Files\Epic Games\UE_5.5\Engine\Plugins\UnrealDeadlineCloudService\Content\Python\libraries"
```

When making adaptor changes, the same .whl can either be transferred to your worker or built on the worker off the same changes.

Install the .whl on the worker with:

// Note we're installing the Adaptor to the global pip install which should be found on our path rather than our Unreal plugin.
pip install ./path/to/my-file.whl


### Running Unreal Spec Tests

The Deadline Cloud plugin's Unreal Automation Tests can be run from within Unreal.

1. Open the Tools menu
2. Select "Session Frontend"
3. Open the Automation tab
4. Select "Deadline"
5. Hit the Go button


## Submit a test render

To test out any significant changes it's useful to submit a test render following [Submit a Test Render](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/blob/mainline/docs/user_guide/setup-submitter.md#submit-a-test-render)

## Building user guide

The user guide is generated from the markdown files in `docs/user_guide` and published to GitHub pages. To view the renderd user guide locally, run `hatch run docs:serve` which will open the user guide in your browser.

## Building the docs

1. Install python requirements for building Sphinx documentation
   ```
   pip install -r requirements-docs.txt
   ```
2. Build and install the **deadline-cloud-for-unreal** package in the python that you use to build the docs
   ```
   cd .\path\to\deadline-cloud\for-unreal
   python -m build
   python -m pip install dist/deadline_cloud_for_unreal-*-py3-none-any.whl
   ```
3. Go to the "docs" folder
   ```
   cd docs
   ```

4. Run documentation building
   ```
   make.bat html
   ```
   
5. Generated documentation will be placed at *docs/build/html* folder.
   You can visit the "Home" page of the docs by opening the **index.html** file

## Troubleshooting

### Credential Configuration Errors

Error: No valid credentials for ### available.

Root Cause: Misconfigured "Run as user" in the queue

Solution: 
   - **Non-E2E tests**: Configure Windows user credentials following the [Manage access to Windows job user secrets](https://docs.aws.amazon.com/deadline-cloud/latest/developerguide/manage-access-windows-secrets.html) guide

   - **E2E tests**: Set the E2E test queue "Run as user" to "Worker agent user"

### CloudWatch Logs Permission Errors

Error: An error occurred (ResourceNotFoundException) when calling the PutLogEvents operation: The specified log stream does not exist. 

Root Cause: The "Run as user" role lacks proper CloudWatch Logs permissions.

Solution: 
   -  **Non-E2E tests**: Ensure the "Run as user" role has the following permissions.
   - **E2E tests**: E2E tests use `BealineTaskExecutionRole` role. Ensure the `BealineTaskExecutionRole` IAM role includes the following permissions.
```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:GetLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/deadline/*"
    }
  ]
}
```

### Unreal Engine Version Mismatch

Error: The package '/Temp/UnrealDeadlineCloudService/RenderJobManifests/###' was saved with an older version which is not backwards compatible with the current process

Root Cause: Version mismatch between the Unreal Engine version used to submit the job and the version running on the worker node.

Solutions:
   - Resubmit the job using the Unreal Engine version that matches the worker node. On Service Managed Fleets - Ensure the Conda package version selected matches your project's version of Unreal Engine
   - Install the correct Unreal Engine version on the worker node and update environment variables to match the job's Unreal Engine version

### Missing Deadline Cloud Job Submission Configuration in Movie Render Queue

Issue: When launching Movie Render Queue, Deadline Cloud job submission configurations are not visible.

Root Cause: Movie Render Pipeline project settings were not properly configured.

Solution: Configure Movie Render Pipeline settings as described in [Submit a Test Render](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/blob/mainline/docs/user_guide/setup-submitter.md#submit-a-test-render):
   - Under "Edit"/"Project Settings" search for the "Movie Render Pipeline" section
     - For "Default Remote Executor", select "MoviePipelineDeadlineCloudRemoteExecutor"
     - For "Default Executor Job", select "MoviePipelineDeadlineCloudExecutorJob"
     - Under "Default Job Settings Classes", click add icon, and add "DeadlineCloudRenderStepSetting"
