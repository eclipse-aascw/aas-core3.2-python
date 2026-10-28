"""Update to the latest meta-model and the latest test data."""

import argparse
import os
import pathlib
import subprocess
import sys

import dev_scripts.common as dev_scripts_common


def main() -> int:
    """Execute the main routine."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include_prereleases",
        help=(
            "If set, consider also the pre-releases when downloading "
            "the latest test data"
        ),
        action="store_true",
    )
    args = parser.parse_args()

    include_prereleases = bool(args.include_prereleases)

    repo_root = pathlib.Path(os.path.realpath(__file__)).parent.parent.parent

    print("Downloading the latest meta-model...")
    subprocess.check_call(
        [
            sys.executable,
            str(repo_root / "dev" / "dev_scripts" / "download_aas_core_meta_model.py"),
        ],
        cwd=str(repo_root),
    )

    print("Generating the code...")
    subprocess.check_call(
        [
            sys.executable,
            str(repo_root / "dev" / "dev_scripts" / "regenerate_code.py"),
        ],
        cwd=str(repo_root),
    )

    print("Re-formatting the code...")
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "black",
            str(dev_scripts_common.module_dir()),
            "dev/tests",
        ],
        cwd=str(repo_root),
    )

    print("Downloading the latest test data...")
    subprocess.check_call(
        [
            sys.executable,
            str(repo_root / "dev" / "dev_scripts" / "download_latest_test_data.py"),
        ]
        + (["--include_prereleases"] if include_prereleases else []),
        cwd=str(repo_root),
    )

    print("Re-recording the test data...")
    subprocess.check_call(
        [sys.executable, str(repo_root / "dev" / "dev_scripts" / "rerecord_tests.py")],
        cwd=str(repo_root),
    )

    print("Running the pre-commit to check that everything worked...")
    subprocess.check_call(
        [
            sys.executable,
            str(repo_root / "dev" / "continuous_integration" / "precommit.py"),
            "--overwrite",
        ],
        cwd=str(repo_root),
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
