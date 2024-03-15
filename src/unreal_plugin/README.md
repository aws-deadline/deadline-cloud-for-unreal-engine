# UnrealDeadlineCloudService

- Provides a UI and API for submitting render jobs on the artist machine.\
- Executes rendering on Worker Node 


## Requirements
- Unreal Engine 5.2


## Installation
Should be placed in the "Plugins" folder of the UE project.

## Development
See the [DEVELOPMENT](DEVELOPMENT.md) file for development pipelines

## Telemetry

This library collects telemetry data by default. Telemetry events contain non-personally-identifiable information that helps us understand how users interact with our software so we know what features our customers use, and/or what existing pain points are.

You can opt out of telemetry data collection by either:

1. Setting the environment variable: `DEADLINE_CLOUD_TELEMETRY_OPT_OUT=true`
2. Setting the config file: `deadline config set telemetry.opt_out true`

Note that setting the environment variable supersedes the config file setting.

## License
This project is licensed under the Apache-2.0 License. 
