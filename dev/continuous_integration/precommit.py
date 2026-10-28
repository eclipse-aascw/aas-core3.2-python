#!/usr/bin/env python3

"""Run pre-commit checks on the repository."""

import argparse
import enum
import os
import pathlib
import shlex
import subprocess
import sys
from typing import Optional, Mapping, Sequence

import continuous_integration.common as continuous_integration_common


class Step(enum.Enum):
    """Enumerate different pre-commit steps."""

    REFORMAT = "reformat"
    MYPY = "mypy"
    RUFF = "ruff"
    TEST = "test"
    DOCTEST = "doctest"
    CHECK_INIT_AND_PYPROJECT_TOML_CONSISTENT = "check-init-and-pyproject-consistent"


def call_and_report(
    verb: str,
    cmd: Sequence[str],
    cwd: Optional[pathlib.Path] = None,
    env: Optional[Mapping[str, str]] = None,
) -> int:
    """
    Wrap a subprocess call with the reporting to STDERR if it failed.

    Return 1 if there is an error and 0 otherwise.
    """
    cmd_str = " ".join(shlex.quote(part) for part in cmd)

    if cwd is not None:
        print(f"Executing from {cwd}: {cmd_str}")
    else:
        print(f"Executing: {cmd_str}")

    exit_code = subprocess.call(cmd, cwd=str(cwd) if cwd is not None else None, env=env)

    if exit_code != 0:
        print(
            f"Failed to {verb} with exit code {exit_code}: {cmd_str}", file=sys.stderr
        )

    return exit_code


def main() -> int:
    """Execute entry_point routine."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--overwrite",
        help="Try to automatically fix the offending files (e.g., by re-formatting).",
        action="store_true",
    )
    parser.add_argument(
        "--select",
        help=(
            "If set, only the selected steps are executed. "
            "This is practical if some of the steps failed and you want to "
            "fix them in isolation. "
            "The steps are given as a space-separated list of: "
            + " ".join(value.value for value in Step)
        ),
        metavar="",
        nargs="+",
        choices=[value.value for value in Step],
    )
    parser.add_argument(
        "--skip",
        help=(
            "If set, skips the specified steps. "
            "This is practical if some of the steps passed and "
            "you want to fix the remainder in isolation. "
            "The steps are given as a space-separated list of: "
            + " ".join(value.value for value in Step)
        ),
        metavar="",
        nargs="+",
        choices=[value.value for value in Step],
    )

    args = parser.parse_args()

    overwrite = bool(args.overwrite)

    selects = (
        [Step(value) for value in args.select]
        if args.select is not None
        else list(Step)
    )
    skips = [Step(value) for value in args.skip] if args.skip is not None else []

    repo_root = continuous_integration_common.REPO_ROOT

    module_dir = str(continuous_integration_common.module_dir())

    if Step.REFORMAT in selects and Step.REFORMAT not in skips:
        print("Re-formatting...")
        reformat_targets = [
            module_dir,
            "dev/continuous_integration",
            "dev/tests",
            "dev/dev_scripts",
        ]

        reformat_exclude = "dev/dev_scripts/codegen"

        if overwrite:
            exit_code = call_and_report(
                verb="black",
                cmd=[sys.executable, "-m", "black"]
                + reformat_targets
                + ["--exclude", reformat_exclude],
                cwd=repo_root,
            )
            if exit_code != 0:
                return 1
        else:
            exit_code = call_and_report(
                verb="check with black",
                cmd=[sys.executable, "-m", "black", "--check"]
                + reformat_targets
                + ["--exclude", reformat_exclude],
                cwd=repo_root,
            )
            if exit_code != 0:
                return 1
    else:
        print("Skipped re-formatting.")

    if Step.MYPY in selects and Step.MYPY not in skips:
        print("Mypy'ing...")
        mypy_targets = [
            module_dir,
            "dev/tests",
            "dev/continuous_integration",
            "dev/dev_scripts",
        ]

        mypy_exclude = "dev/dev_scripts/codegen"

        config_file = pathlib.Path("dev/continuous_integration/mypy.ini")

        exit_code = call_and_report(
            verb="mypy",
            cmd=[
                sys.executable,
                "-m",
                "mypy",
                "--strict",
                "--config-file",
                str(config_file),
            ]
            + mypy_targets
            + ["--exclude", mypy_exclude],
            cwd=repo_root,
        )
        if exit_code != 0:
            return 1
    else:
        print("Skipped mypy'ing.")

    if Step.RUFF in selects and Step.RUFF not in skips:
        print("Ruff'ing...")
        ruff_targets = [
            module_dir,
            "dev/tests",
            "dev/continuous_integration",
            "dev/dev_scripts",
        ]

        ruff_exclude = "dev/dev_scripts/codegen"

        config = pathlib.Path("dev/continuous_integration/ruff.toml")

        exit_code = call_and_report(
            verb="ruff",
            cmd=[sys.executable, "-m", "ruff", "check", f"--config={config}"]
            + (["--fix"] if overwrite else [])
            + ruff_targets
            + [f"--extend-exclude={ruff_exclude}"],
            cwd=repo_root,
        )
        if exit_code != 0:
            return 1
    else:
        print("Skipped ruff'ing.")

    if Step.TEST in selects and Step.TEST not in skips:
        print("Testing...")
        env = os.environ.copy()
        env["ICONTRACT_SLOW"] = "true"

        exit_code = call_and_report(
            verb="execute unit tests",
            cmd=[
                sys.executable,
                "-m",
                "coverage",
                "run",
                "--source",
                module_dir,
                "-m",
                "unittest",
                "discover",
                "--start-directory",
                "dev/tests",
            ],
            cwd=repo_root,
            env=env,
        )
        if exit_code != 0:
            return 1

        exit_code = call_and_report(
            verb="report the coverage",
            cmd=[sys.executable, "-m", "coverage", "report"],
            cwd=repo_root,
        )
        if exit_code != 0:
            return 1
    else:
        print("Skipped testing.")

    if Step.DOCTEST in selects and Step.DOCTEST not in skips:
        print("Doctest'ing...")

        doc_files = sorted(
            ["README.rst"]
            + [str(path) for path in (repo_root / "docs" / "source").glob("**/*.rst")]
        )

        exit_code = call_and_report(
            verb="doctest",
            cmd=[sys.executable, "-m", "doctest"] + doc_files,
            cwd=repo_root,
        )
        if exit_code != 0:
            return 1

        for pth in (repo_root / module_dir).glob("**/*.py"):
            if pth.name == "__main__.py":
                continue

            # NOTE (mristin):
            # The subprocess calls are expensive, call only if there is an actual
            # doctest
            text = pth.read_text(encoding="utf-8")
            if ">>>" in text:
                exit_code = call_and_report(
                    verb="doctest",
                    cmd=[sys.executable, "-m", "doctest", str(pth)],
                    cwd=repo_root,
                )
                if exit_code != 0:
                    return 1
    else:
        print("Skipped doctest'ing.")

    if (
        Step.CHECK_INIT_AND_PYPROJECT_TOML_CONSISTENT in selects
        and Step.CHECK_INIT_AND_PYPROJECT_TOML_CONSISTENT not in skips
    ):
        print("Checking that __init__.py and pyproject.toml are consistent...")
        exit_code = call_and_report(
            verb="check that __init__.py and pyproject.toml are consistent",
            cmd=[
                sys.executable,
                "dev/continuous_integration/check_init_and_pyproject_toml_consistent.py",
            ],
            cwd=repo_root,
        )
        if exit_code != 0:
            return 1
    else:
        print("Skipped checking that __init__.py and pyproject.toml are consistent.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
