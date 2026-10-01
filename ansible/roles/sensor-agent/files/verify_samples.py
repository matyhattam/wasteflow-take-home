import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

env_path = Path(sys.argv[1])

config = dict(
    line.split("=", 1)
    for line in env_path.read_text().splitlines()
    if line and not line.startswith("#")
)

port = config["PORT"]
sensor_id = config["SENSOR_ID"]
interval = float(config["POLL_INTERVAL_SECONDS"])
base_url = f"http://127.0.0.1:{port}"


def wait_for_health():
    for attempt in range(10):
        try:
            with urlopen(f"{base_url}/health", timeout=3) as response:
                if response.status == 200 and response.read().strip() == b"ok":
                    return
        except (URLError, TimeoutError):
            pass

        if attempt < 9:
            time.sleep(2)

    raise RuntimeError("The selected release did not become healthy")


def sample_count():
    with urlopen(f"{base_url}/metrics", timeout=3) as response:
        metrics = response.read().decode()

    prefix = f'sensor_samples_total{{sensor_id="{sensor_id}"}} '
    for line in metrics.splitlines():
        if line.startswith(prefix):
            return float(line[len(prefix) :])

    raise RuntimeError("Expected sensor metric is missing")


wait_for_health()
before = sample_count()
time.sleep(interval + 1)
after = sample_count()

if not after > before:
    raise RuntimeError(f"Sampling is not progressing: {before} -> {after}")

print(f"Selected release is healthy; samples increased: {before} -> {after}")
