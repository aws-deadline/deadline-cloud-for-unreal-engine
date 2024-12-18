# Development documentation

This package has two active branches:
- `mainline` -- For active development. This branch is not intended to be consumed by other packages. Any commit to this branch may break APIs, dependencies, and so on, and thus break any consumer without notice.
- `release` -- The official release of the package intended for consumers. Any breaking releases will be accompanied with an increase to this package's interface version.

## Build and Install the Plugin, Submitter, and Adapter

Full instructions for building and installing these packages and the necessary dependencies to act as a submitter and/or worker can be found in [this guide](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/blob/mainline/SETUP_SUBMITTER_CMF.md).  Use the "mainline" branch for development rather than "release", and if you plan on submitting pull requests work out of [a fork](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/blob/mainline/CONTRIBUTING.md#contributing-via-pull-requests).


## Build / Test / Release

### Build the python packages

```bash
hatch build
```

### Run tests

```bash
hatch run test
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

When making C++ changes before testing you'll need to rebuild and copy your modified plugin to your Unreal plugins folder following [these steps](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/blob/mainline/SETUP_SUBMITTER_CMF.md#build-the-plugin).


### Testing Python Changes

When making changes to the Python submitter you'll need to rebuild and install your .whl file, adjusting paths to your local installation:

```
// Install hatch if not yet installed
pip install hatch
hatch build
"C:\Program Files\Epic Games\UE_5.4\Engine\Binaries\ThirdParty\Python3\Win64\python" -m pip install dist\deadline_cloud_for_unreal_engine-0.2.2.post21-py3-none-any.whl --target "C:\Program Files\Epic Games\UE_5.4\Engine\Plugins\UnrealDeadlineCloudService\Content\Python\libraries"
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

To test out any significant changes it's useful to submit a test render following [this guide](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/blob/mainline/SETUP_SUBMITTER_CMF.md#submit-a-test-render-optional)


### Building the docs

1. Install python requirements for building Sphinx documentation
   ```
   pip install -r docs_requirements.txt
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








