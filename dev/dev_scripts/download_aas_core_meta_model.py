# SPDX-FileCopyrightText: 2026 aas-core3.2-python AUTHORS
#
# SPDX-License-Identifier: MIT

"""Download the meta-model to this directory."""

import argparse
import sys
from typing import Dict, Union, Final

import requests

import dev_scripts.common as dev_scripts_common

GITHUB_API: Final[str] = "https://api.github.com"
OWNER: Final[str] = "eclipse-aascw"
REPO: Final[str] = "aas-core-meta"
REF: Final[str] = "main"

# NOTE (aaronzi, 2026-11-08):
# The meta-model is copied verbatim from aas-core-meta, so we attribute it to
# its authors. We only prepend the header if the upstream file does not carry
# a license header itself, so that the header is not duplicated.
#
# REUSE-IgnoreStart
_META_MODEL_LICENSE_HEADER: Final[str] = """\
# SPDX-FileCopyrightText: 2024 aas-core-meta AUTHORS
#
# SPDX-License-Identifier: MIT

"""

_LICENSE_IDENTIFIER_TAG: Final[str] = "SPDX-License-Identifier:"
# REUSE-IgnoreEnd


def _latest_commit_sha_for_path(
    owner: str, repo: str, ref: str, path: str, *, timeout: float = 15.0
) -> str:
    """
    Resolve the latest commit SHA on a ref for a specific path.

    Uses: GET /repos/{owner}/{repo}/commits?path=...&sha=...&per_page=1
    """
    url = f"{GITHUB_API}/repos/{owner}/{repo}/commits"
    params: Dict[str, Union[str, int]] = {"path": path, "sha": ref, "per_page": 1}
    resp = requests.get(url, params=params, timeout=timeout)
    try:
        resp.raise_for_status()
    except requests.HTTPError as ex:
        raise RuntimeError(
            f"Failed to resolve latest commit for {owner}/{repo}:{ref} path={path} "
            f"({resp.status_code}): {resp.text}"
        ) from ex

    commits = resp.json()
    if not commits or not isinstance(commits, list):
        raise RuntimeError(
            "Could not determine latest commit SHA (empty API response)."
        )

    sha = commits[0].get("sha")
    if not sha or not isinstance(sha, str):
        raise RuntimeError("API did not return a valid commit SHA.")
    assert isinstance(sha, str)
    return sha


def _download_raw_from_commit(
    owner: str, repo: str, sha: str, path: str, *, timeout: float = 30.0
) -> str:
    """Download the raw file contents for a given commit SHA and path."""
    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{sha}/{path}"
    resp = requests.get(raw_url, timeout=timeout)
    try:
        resp.raise_for_status()
    except requests.HTTPError as ex:
        raise RuntimeError(
            f"Failed to download file from {raw_url} ({resp.status_code}): {resp.text}"
        ) from ex

    return resp.text


def main() -> int:
    """Execute the main routine."""
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.parse_args()

    filepath = f"aas_core_meta/{dev_scripts_common.version_stem()}.py"

    sha = _latest_commit_sha_for_path(OWNER, REPO, REF, filepath)

    content = _download_raw_from_commit(OWNER, REPO, sha, filepath)

    pinned_url = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/{sha}/{filepath}"
    banner = f"# Downloaded from: {pinned_url}\n"

    out_path = (
        dev_scripts_common.REPO_ROOT
        / "dev"
        / "dev_scripts"
        / "codegen"
        / "meta_model.py"
    )

    license_header = (
        "" if _LICENSE_IDENTIFIER_TAG in content else _META_MODEL_LICENSE_HEADER
    )

    out_path.write_text(
        f"{license_header}{banner}{content.rstrip()}\n\n{banner}",
        encoding="utf-8",
    )

    print(f"Wrote {out_path} (from commit {sha[:12]}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
