# UnrealDeadlineCloudService

## Development pipeline

### Adding UnrealSubmitter to the UE plugin
Approach: CI/CD build UE plugin with unreal_submitter with .bat file
1. Remove all files from Content/Python/libraries
2. cloning deadline-cloud-for-unreal, deadline-cloud
3. pip install deadline-cloud/ --target=Content/Python/libraries
4. Copy deadline-cloud-for-unreal/src/deadline/unreal_submitter to Content/Python/libraries folder
5. Delete cloned repos.
6. Delete pull_submitter.bat from release plugin package (via CI/CD)

### Generating C++ code documentation
C++ documentation is generated with [Doxygen](https://www.doxygen.nl/) 
1. Install Doxygen. Add doxygen exe to system path
2. cd UnrealDeadlineCloudService/Documentation
3. Generate documentation by running ```doxygen``` command in command line