"""Run all tests and re-record the golden data."""

import argparse
import os
import pathlib
import shutil
import subprocess
import sys

import dev_scripts.common as dev_scripts_common


def main() -> int:
    """Execute the main routine."""
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.parse_args()

    repo_root = pathlib.Path(os.path.realpath(__file__)).parent.parent.parent

    env = os.environ.copy()
    env[dev_scripts_common.record_mode_variable()] = "1"

    for path in (repo_root / "dev/test_data").iterdir():
        if path.is_dir() and path.name not in ["Json", "Xml"]:
            print(f"Deleting {path} ...")
            shutil.rmtree(path)

    print("Running and re-recording all tests...")
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "--source",
            str(dev_scripts_common.module_dir()),
            "-m",
            "unittest",
            "discover",
            "--start-directory",
            "dev/tests",
        ],
        cwd=repo_root,
        env=env,
    )
    print("Re-recorded.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
