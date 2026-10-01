import os
import tomllib

with open("pyproject.toml", "rb") as file:
    version = tomllib.load(file)["project"]["version"]

expected = f"v{version}"
actual = os.environ["GITHUB_REF_NAME"]

if actual != expected:
    raise SystemExit(f"Tag {actual!r} does not match expected tag {expected!r}")

print(f"Release version verified: {version}")
