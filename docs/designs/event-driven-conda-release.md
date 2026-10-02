# Event-driven Conda release gate

## Approved direction

A release should visibly wait for its Conda adaptor in the same GitHub workflow
that stages and publishes it. Keep manual changelog approval and merging.
Use a GitHub App custom deployment protection rule for the wait; report promotion
progress through GitHub Checks and resume on approval.

The event processor uses a queue and one handler, with progress state in GitHub.
Separate database storage, a second reporting handler, and periodic readiness
polling are unnecessary for this design.

## Repository implementation

Combine the existing Stage and Publish job chains without adding jobs. Keep the
original test, build, signing, and publishing implementations. `TagRelease`
validates the version before testing; remove its redundant later invocation as
`ValidateRelease`. Use `AuthorizePublish` to upload release metadata after staging
and `CheckConda` as a wait-only job protected by the GitHub App.

The App verifies signed requests, exact release/run/attempt identity, final
DocsUpdate completion and exact public manifest availability before approving.
Publishing uses the original `TagRelease` outputs. Release tags remain fixed
throughout an active release, and the environment protection rule remains enabled.

See [the workflow contract and rollout guide](../release-workflow.md) for exact
fields, permissions, recovery, and limits.

## Independent implementation tasks

1. Repository: consolidate workflow, record metadata, retain the protected wait,
   validate metadata and workflow dependencies, and document recovery.
2. Infrastructure: implement signed webhook intake, queued promotion events,
   progress updates, exact availability reconciliation, and gate callbacks.
3. Validate both together in a development account and personal fork before enabling
   the repository workflow.

## Verification status

The earlier fork experiment verified a real environment pause, progress reporting,
automatic resume from controlled events, and preserved build artifacts. It did not
prove delivery of native promotion events. That verification and production App
configuration remain prerequisites for merging and enabling the replacement.
