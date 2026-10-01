# Validation

The exercise asks us to think about shipping software to a device we cannot easily walk up to. That shaped the deployment and the way I tested it: the right version needs to install reliably, a second run should leave a healthy service alone, and a failed process or upgrade needs a clear recovery path. I used an Ubuntu VM to check those behaviors with Ansible and systemd, and I looked for fresh sensor samples as well as a running service. The sections below describe what I tested and what remains unproven.

## CI validation

The GitHub Actions workflow runs lint and format checks, unit tests, builds the package, and installs the built wheel for a smoke test. That smoke test checks `/health`, confirms the expected metric is present, and requires `sensor_samples_total` to increase. The workflow uploads the build output as an artifact after these checks pass. This validates the package before deployment; the VM tests below check how that package behaves under systemd and Ansible. A successful workflow run should be confirmed in GitHub Actions rather than inferred from the workflow file alone.

## First installation

I built the wheel and ran the playbook against a fresh Ubuntu VM. The playbook installed the versioned release, enabled and started `sensor-agent.service`, checked `/health`, and verified that `sensor_samples_total` increased over a polling interval. [Setup](setup.md) shows how to repeat the service and metrics checks manually.

## Repeat installation

I ran the same playbook again with the same version and configuration. This was the idempotency check: the requested release was already selected, so the second run made no changes and did not restart the service.

## Process failure and recovery

I killed the running service process and checked that systemd started it again. The unit uses `Restart=on-failure`, so this tests recovery from a process exit. The service and metrics commands in [Setup](setup.md) can be used to check sampling after a restart.

## Upgrade

I built a wheel for a new version, updated `sensor_agent_version` in `ansible/sensor-agent.yml`, and ran the playbook again. It installed the new release in a separate environment, selected it, and restarted the service with the new wheel. The playbook then checked the HTTP endpoint and sampling progress before reporting success.

## Failed deployment and rollback

The deployment records the previous `current` selection before activating a new release. If activation or verification fails, the rescue path is intended to restore that selection, clear the systemd restart limit, restart the previous service, and verify it before reporting the deployment as failed. If there was no previous release, the new first-install recovery tasks check whether a service unit was linked and stop and disable it when present.

The sampling verifier now reads `PORT`, `SENSOR_ID`, and `POLL_INTERVAL_SECONDS` from `current/sensor-agent.env`. This lets it check the settings belonging to the selected release, including the restored release after rollback, instead of assuming the failed release's settings still apply.

I tested a failed upgrade on the VM with a `0.0.2` wheel whose `/health` handler raises an exception when the endpoint is called. The post-deployment health check failed, and the deployment rolled back to the previous release. This exercises rollback after activation when verification fails. I did not record a separate check of Ansible's exit status or the restored release's sample counter for this test.

I have not run a failed-first-install test. That test should confirm that the failed service is stopped and disabled when there is no previous release to restore.

## Limitations and trade-offs

These tests cover one reachable Ubuntu VM, a successful upgrade, and a failed upgrade that triggered rollback. Failed first installation remains unverified. The playbook also assumes the target already has Python for Ansible fact gathering, it does not bootstrap a minimal Linux image without Python. Such a target would need an initial `ansible.builtin.raw` step with fact gathering disabled to install Python before this playbook runs. A process crash is also narrower than every possible failure: `Restart=on-failure` does not repair an agent that stays alive but stops sampling. The playbook detects stalled sampling during deployment, but there is no continuous runtime watchdog for it. I kept releases local and used one Ansible target. fleet rollout, remote artifact distribution, and monitoring would need additional work.
