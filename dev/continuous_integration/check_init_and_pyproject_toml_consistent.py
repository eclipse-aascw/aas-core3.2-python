"""Check that meta-data in ``pyproject.toml`` and ``__init__.py`` are consistent."""

import importlib
import sys
from typing import List

import continuous_integration.common as continuous_integration_common


def main() -> None:
    """Execute the main routine."""
    errors: List[str] = []

    pyproject_data = continuous_integration_common.load_pyproject()

    module = importlib.import_module(continuous_integration_common.module_name())

    init_version = module.__version__
    pyproject_version = pyproject_data["project"]["version"]

    # NOTE (mristin):
    # We check for the version.
    if init_version != pyproject_version:
        errors.append(
            f"Version mismatch: __init__.py has {init_version!r}, "
            f"pyproject.toml has {pyproject_version!r}"
        )

    # NOTE (mristin):
    # We check for the authors.
    init_authors = [author.strip() for author in module.__author__.split(",")]
    pyproject_authors = [
        author["name"] for author in pyproject_data["project"]["authors"]
    ]

    if init_authors != pyproject_authors:
        errors.append(
            f"Authors mismatch: __init__.py has {init_authors!r}, "
            f"pyproject.toml has {pyproject_authors!r}"
        )

    # NOTE (mristin):
    # We check for the development status.
    init_status = module.__status__
    pyproject_status = ""

    for classifier in pyproject_data["project"]["classifiers"]:
        if classifier.startswith("Development Status"):
            parts = classifier.split("::")

            if len(parts) >= 2:
                status = parts[1].strip()

                # NOTE (mristin):
                # We extract just the status part (*e.g.*, "5 - Production/Stable" ->
                # "Production/Stable").

                if " - " in status:
                    pyproject_status = status.split(" - ", 1)[1]
                else:
                    pyproject_status = status

                break

    if init_status != pyproject_status:
        errors.append(
            f"Status mismatch: __init__.py has {init_status!r}, "
            f"pyproject.toml classifiers have {pyproject_status!r}"
        )

    # NOTE (mristin):
    # We check for the license.
    init_license = module.__license__
    pyproject_license = pyproject_data["project"]["license"]

    if init_license != pyproject_license:
        errors.append(
            f"License mismatch: __init__.py has {init_license!r}, "
            f"pyproject.toml has {pyproject_license!r}"
        )

    if len(errors) > 0:
        errors_str = "\n".join(errors)
        print(f"Meta-data consistency check failed:\n{errors_str}", file=sys.stderr)
        sys.exit(1)

    print("All meta-data fields are consistent between __init__.py and pyproject.toml.")


if __name__ == "__main__":
    main()
