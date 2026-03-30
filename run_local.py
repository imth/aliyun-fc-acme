"""Local test runner — loads .env and calls handler()."""

import os

# Load .env file
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            os.environ[key.strip()] = value.strip().strip("'\"")

from index import handler  # noqa: E402

if __name__ == "__main__":
    result = handler({}, None)
    print("\nResult:", result)
