# Setup

This exercise was tested on an Ubuntu 24.04 VM created with Multipass. I chose a Linux VM because the deployment targets a Linux edge device: it lets me test SSH access, file permissions, systemd service management, logs, and reboot behavior in an environment close to the target, while keeping the test isolated from my Mac. Multipass made it quick to recreate a clean device for deployment and rollback tests.

## Requirements

On the machine running the deployment, install Multipass, `uv`, and Ansible. Run the commands below from the repository root. Replace the public key in `cloud-init.yaml` with your own SSH public key and keep the matching private key on your machine.

## Create and access the VM

Create the VM with that key so it can be accessed over SSH:

```sh
multipass launch 24.04 \
  --name wasteflow-edge \
  --cpus 2 \
  --memory 2G \
  --disk 10G \
  --cloud-init cloud-init.yaml
```

I used direct SSH access to the VM because the Multipass shell command did not work in my environment. Get the current IP after launch, then check that SSH works before running Ansible:

```sh
multipass info wasteflow-edge
ssh ubuntu@VM_IP
```

Replace `VM_IP` with the IP shown by `multipass info`. The VM IP can change after recreation.

## Build and deploy

Build the wheel locally. Its version must match `sensor_agent_version` in `ansible/sensor-agent.yml`:

```sh
uv build --wheel
```

Set `ansible_host` in `ansible/inventory.ini` to the current VM IP.

```sh
ansible-playbook -i ansible/inventory.ini ansible/sensor-agent.yml
```

The playbook installs the wheel, starts the systemd service, checks `/health`, and verifies that samples are being produced.

## Check the running agent

On the VM, inspect the service and its recent logs:

```sh
ssh ubuntu@VM_IP 'systemctl status sensor-agent.service --no-pager'
ssh ubuntu@VM_IP 'journalctl -u sensor-agent.service -n 50 --no-pager'
```

Check the local HTTP endpoints on the VM. With the configured five-second polling interval, the `sensor_samples_total` value should increase between reads:

```sh
ssh ubuntu@VM_IP 'curl -fsS http://127.0.0.1:8000/health'
ssh ubuntu@VM_IP 'curl -fsS http://127.0.0.1:8000/metrics'
sleep 10
ssh ubuntu@VM_IP 'curl -fsS http://127.0.0.1:8000/metrics'
```

An `ok` health response alone does not show that sampling is progressing. Compare the two `sensor_samples_total{sensor_id="wasteflow_vm"}` values.

## Recreate the VM

To delete the VM for a fresh test:

```sh
multipass delete wasteflow-edge && multipass purge
```

`multipass purge` permanently removes **all** deleted Multipass instances, including ones unrelated to this project. Run the launch command above to create this VM again, then check its new IP and update the inventory.
