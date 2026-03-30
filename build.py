"""Build script for FC deployment package.

Uses Docker to install dependencies in a Linux environment, ensuring all
binary packages (.so) are compatible with FC runtime (Linux x86_64).
Output: deploy.zip (ready to upload to Alibaba Cloud FC)
"""

import os
import shutil
import subprocess
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(ROOT, "build")
OUTPUT_ZIP = os.path.join(ROOT, "deploy.zip")
PYTHON_VERSION = "3.12"


def clean():
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    if os.path.exists(OUTPUT_ZIP):
        os.remove(OUTPUT_ZIP)


def install():
    """Install project and dependencies in Docker (manylinux for max GLIBC compatibility)."""
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--platform",
            "linux/amd64",
            "-v",
            f"{ROOT}:/app",
            "-w",
            "/app",
            "quay.io/pypa/manylinux2014_x86_64",
            "/opt/python/cp312-cp312/bin/pip",
            "install",
            ".",
            "-t",
            "build",
            "--quiet",
        ],
        cwd=ROOT,
        check=True,
    )


def copy_entry():
    """Copy FC entry point to build/."""
    shutil.copy2(os.path.join(ROOT, "index.py"), os.path.join(BUILD_DIR, "index.py"))


def create_zip():
    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirpath, _, filenames in os.walk(BUILD_DIR):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                arcname = os.path.relpath(filepath, BUILD_DIR)
                zf.write(filepath, arcname)

    size_mb = os.path.getsize(OUTPUT_ZIP) / (1024 * 1024)
    print(f"Created {OUTPUT_ZIP} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    print("Cleaning build directory...")
    clean()

    print(f"Installing dependencies via Docker (Python {PYTHON_VERSION}, Linux x86_64)...")
    os.makedirs(BUILD_DIR, exist_ok=True)
    install()

    print("Copying entry point...")
    copy_entry()

    print("Creating zip package...")
    create_zip()

    print("Done! Upload deploy.zip to Alibaba Cloud FC.")
