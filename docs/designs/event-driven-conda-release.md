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
original test, build, signing, and publishing implementations. Use the existing
`AuthorizePublish` job to upload a release identity after staging succeeds, and
the existing `CheckConda` job for the protected wait and approval verification. Identify the approval by repository, run, attempt, package,
version, required platforms, and immutable tagged source.

Environment approval alone is insufficient: verify the configured App's successful
check for that identity before building the public release, then recheck the public
manifest. This also prevents publication if the environment rule is missing.

See [the workflow contract and rollout guide](../release-workflow.md) for exact
fields, permissions, recovery, and limits.

## Independent implementation tasks

1. Repository: consolidate workflow, add metadata and approval verification,
   test stale/missing/mismatched approvals, and document recovery.
2. Infrastructure: implement signed webhook intake, queued promotion events,
   progress updates, exact availability reconciliation, and gate callbacks.
3. Validate both together in a development account and personal fork before enabling
   the repository workflow.

## Verification status

The earlier fork experiment verified a real environment pause, progress reporting,
automatic resume from controlled events, and preserved build artifacts. It did not
prove delivery of native promotion events. That verification and production App
configuration remain prerequisites for merging and enabling the replacement.
