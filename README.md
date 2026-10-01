## Regarding the setup and the validation

Docs relative to this implementation:
[Setup](docs/setup.md) and [Validation](docs/validation.md)

## One-page README
1. ### How would you extend this to OTA updates across 100+ devices?

   I’d use a fleet controller to decide which devices receive each release, with devices downloading and applying updates locally. The priorities are trusted artifacts, gradual rollout, and predictable behavior when devices are offline or several versions behind.

   - **Secure, reproducible releases.** Build and test once in CI, then promote the same artifact. Devices verify its signature and checksum before installation. Protect signing keys in a managed signing service, with a tested process for rotating keys and distributing revocations.

   - **Controlled rollout.** Start with a Canary deployment strategy, with only 1% of the devices, then 5%, 10 etc, then expand in batches after an observation period. Health regressions pause promotion. Stagger downloads and add random delays to retries so devices do not reconnect or download simultaneously.

   - **Device-aware delivery.** Track device identity, hardware, current version, intended version, and last contact. Devices pull updates over authenticated connections; offline devices remain pending. Release metadata declares compatibility and supported upgrade paths, including intermediate releases where a direct upgrade is unsafe.

2. ### How would you roll back a bad release?

   The device must be able to recover without the network, and the fleet controller must stop spreading a bad release. I’d make recovery a tested part of every deployment.

   - **Preserve a complete recovery target.** Keep the previous application, dependencies, and matching configuration locally. Install alongside it and activate provisionally. Local data changes must remain compatible with the previous version or have an explicit recovery procedure.

   - **Check useful work against a baseline.** Record service and sensor health before updating, then verify stability and fresh samples over several expected sampling intervals after startup. A sensor that was already failing should defer the update or require investigation.

   - **Bound recovery attempts.** If a new failure appears, restore the previous release once and verify it. If that also fails, stop cycling versions, preserve diagnostics, and raise a true incident.
   The cause may be hardware or another shared dependency.

   - **Contain the fleet impact.** Pause further deployment, prevent automatic retries of the rejected release, and recover affected devices. Record “deployment failed, rollback succeeded” separately from a successful update.

3. ### What are the first three things you would monitor in production?

   I’d monitor whether devices are producing useful data, whether the fleet is reachable and stable, and whether deployments are succeeding. Those same signals would decide whether each rollout stage can proceed.

   - **Data freshness and completeness**
     - Time since the last valid sample and sample rate versus expectations.
     - Upload delay and buffered backlog, to distinguish collection failures from connectivity problems.

   - **Device and service availability**
     - Last heartbeat, crashes, and unexpected restarts.
     - Group alerts by site and account for normal reporting intervals to avoid duplicate or premature alarms.

   - **Deployment health**
     - Intended versus reported versions, including pending, failed, and rolled-back devices.
     - Compare data freshness and stability across releases, hardware types, and sites before expanding the rollout.
