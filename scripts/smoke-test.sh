#!/usr/bin/env bash
set -euo pipefail
version="$(
  uv run --no-project python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])'
)"

wheel="$PWD/dist/sensor_agent-${version}-py3-none-any.whl"

if [[ ! -f "$wheel" ]]; then
  echo "Missing wheel: $wheel" >&2
  exit 1
fi

smoke_dir="$(mktemp -d)"

uv venv --python "$(command -v python)" "$smoke_dir/venv"
uv pip install \
  --python "$smoke_dir/venv/bin/python" \
  --no-index \
  --no-deps \
  "$wheel"

cd "$smoke_dir"
"$smoke_dir/venv/bin/sensor-agent" >agent.log 2>&1 &
agent_pid=$!

cleanup() {
  cat agent.log
  kill "$agent_pid" 2>/dev/null || true
  wait "$agent_pid" 2>/dev/null || true
}
trap cleanup EXIT

ready=false
for attempt in {1..15}; do
  if ! kill -0 "$agent_pid" 2>/dev/null; then
    echo "Agent exited before becoming healthy"
    exit 1
  fi

  if curl --fail --silent --max-time 1 \
    "http://127.0.0.1:$PORT/health" >health.txt; then
    ready=true
    break
  fi
  sleep 1
done

if [[ "$ready" != true ]]; then
  echo "Agent did not become healthy"
  exit 1
fi

grep -qx 'ok' health.txt

curl --fail --silent --show-error --max-time 2 \
  "http://127.0.0.1:$PORT/metrics" >metrics.txt

grep -q '^sensor_reading{sensor_id="ci-smoke"} ' metrics.txt

sample_count() {
  awk '$1 == "sensor_samples_total{sensor_id=\"ci-smoke\"}" {print $2}' metrics.txt
}

initial_samples="$(sample_count)"
if [[ ! "$initial_samples" =~ ^[0-9]+$ ]]; then
  echo "Missing or invalid sample counter"
  cat metrics.txt
  exit 1
fi

for attempt in {1..10}; do
  sleep 0.5
  if ! kill -0 "$agent_pid" 2>/dev/null; then
    echo "Agent exited while checking sampling progress"
    exit 1
  fi

  curl --fail --silent --show-error --max-time 1 \
    "http://127.0.0.1:$PORT/metrics" >metrics.txt
  current_samples="$(sample_count)"
  if [[ ! "$current_samples" =~ ^[0-9]+$ ]]; then
    echo "Missing or invalid sample counter"
    cat metrics.txt
    exit 1
  fi

  if (( current_samples > initial_samples )); then
    echo "Sampling verified: $initial_samples -> $current_samples"
    exit 0
  fi
done

echo "Sampling stalled: counter did not increase from $initial_samples"
cat metrics.txt
exit 1