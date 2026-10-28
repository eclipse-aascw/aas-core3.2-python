"""Provide the settings shared among the continuous integration scripts."""

import os
import pathlib
import sys
from typing import Any, Final, Mapping

from icontract import ensure

if sys.version_info >= (3, 11):
    import tomllib
else:
    # noinspection PyUnreachableCode
    import tomli as tomllib

REPO_ROOT: Final[pathlib.Path] = pathlib.Path(
    os.path.realpath(__file__)
).parent.parent.parent

PYPROJECT_TOML_PATH: Final[pathlib.Path] = REPO_ROOT / "pyproject.toml"


def load_pyproject() -> Mapping[str, Any]:
    """Load the ``pyproject.toml`` of the SDK."""
    with PYPROJECT_TOML_PATH.open("rb") as f:
        return tomllib.load(f)


def module_name() -> str:
    """
    Determine the name of the SDK module from ``pyproject.toml``.

    The continuous integration checks the package as it is shipped, so we take
    the name from [tool.setuptools.packages.find] include.
    """
    pyproject_data = load_pyproject()

    packages_find = (
        pyproject_data.get("tool", {})
        .get("setuptools", {})
        .get("packages", {})
        .get("find", {})
    )
    include_packages = packages_find.get("include", [])

    if len(include_packages) != 1:
        raise AssertionError(
            f"Expected exactly one package in [tool.setuptools.packages.find] include "
            f"in {PYPROJECT_TOML_PATH}, but got: {include_packages}"
        )

    result = include_packages[0]
    assert isinstance(result, str)
    return result


@ensure(lambda result: not result.is_absolute())
def module_dir() -> pathlib.Path:
    """
    Determine the directory of the SDK module relative to the repo root.

    The module name can include parent modules (*e.g.*,
    ``some.parent.aas_core3_2``), so we map it to nested directories.
    """
    return pathlib.Path(*module_name().split("."))
