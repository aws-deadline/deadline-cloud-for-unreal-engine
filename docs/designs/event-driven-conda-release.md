# Event-driven Conda release gate

## Approved direction

A release waits for its Conda adaptor in the same GitHub workflow that stages and
publishes it. Changelog approval and merging remain manual.

The initial App mechanism was demonstrated in dev. The approved Gamma direction
uses a required-reviewer environment and that reviewer's PAT to avoid a new GitHub
App installation. Progress uses commit statuses linked to the run; approval uses
GitHub's pending-deployments API. Organization PAT policies still apply.

One queue and one Lambda handle direct registrations and native pipeline events.
No database, S3 tracking record, reporting Lambda, webhook, or periodic poller is
required. Discovery state is recomputed; GitHub statuses identify registered runs.

## Repository implementation

Combine the existing Stage and Publish chains without adding jobs. Keep their
original tests, builds, signing, and publishing. `TagRelease` validates the version
before testing; remove the redundant `ValidateRelease` job.

`AuthorizePublish` uploads immutable release metadata after staging and registers
its run/attempt with SQS using a mainline-only OIDC role. `CheckConda` remains a
job with required-reviewer protection. After the wait, it checks the CI bot's
success status for the exact workflow run and attempt before publication.
Availability verification remains in Lambda.

Lambda validates current-attempt registration, artifact identity, the tag, exact
package/platform availability, and completed DocsUpdate approval before reviewing
the pending environment. Publication uses the original `TagRelease` outputs.
Release tags and environment protection remain fixed during an active release.

See [the workflow contract and rollout guide](../release-workflow.md) for fields,
permissions, configuration, recovery, and limits.

## Infrastructure and rollout

The Gamma queue, Lambda, PAT secret, and OIDC role are configured manually.
The production CDK CR remains draft and unchanged as requested. Its App-specific
implementation will need the PAT adaptation during the later production review;
it cannot be deployed unchanged with this workflow contract.

Use the actual consolidated workflow for the next intended release after the
Gamma PAT/reviewer configuration and event subscription are configured.
Native event delivery and live PAT approval are verified during that release.
A second disposable harness is unnecessary after the completed dev experiment.
No public release has been triggered by this change.

After that release succeeds, adapt and deploy the production CDK implementation.
Configure its registration role and queue in the production repository variables
while the environment remains `conda-gamma`. Then switch
`CONDA_RELEASE_ENVIRONMENT` to `conda-release`; the same workflow selects the
matching production queue and role. Existing Gamma runs must finish first.
