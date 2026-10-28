"""Download the latest test data released on aas-core-testdatagen."""

import argparse
import collections
import json
import pathlib
import shutil
import sys
import uuid
import zipfile
from typing import Final, List

import requests
from icontract import require

import dev_scripts.common as dev_scripts_common

_REPO: Final[str] = "eclipse-aascw/aas-core-testdatagen"


class _Release:
    """Represent a release of aas-core-testdatagen with our test data."""

    #: Git tag of the release, not the version of the meta-model
    tag_name: Final[str]

    #: URL to download the test data for our version of the meta-model
    url: Final[str]

    def __init__(self, tag_name: str, url: str) -> None:
        """Initialize with the given values."""
        self.tag_name = tag_name
        self.url = url


def _get_latest_release(include_prereleases: bool) -> _Release:
    """
    Get the latest release of aas-core-testdatagen with our test data.

    The test data for a new version of the meta-model is usually published first
    in a pre-release, while the latest full release might only contain the test
    data for older versions. Hence, we pick the newest release which actually
    contains the test data for our version of the meta-model.

    If ``include_prereleases`` is set, the pre-releases are also considered.
    Otherwise, only the full releases are considered.
    """
    asset_name = f"test_data_for_{dev_scripts_common.version_stem()}.zip"

    # NOTE (mristin):
    # GitHub lists the releases, including the pre-releases, sorted by
    # their creation date, the newest first.
    url = f"https://api.github.com/repos/{_REPO}/releases"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exception:
        raise RuntimeError(f"Error fetching the releases from {url}") from exception

    if not isinstance(data, list):
        raise RuntimeError(f"Expected a list of releases from {url}, but got: {data}")

    skipped_prereleases: List[str] = []

    for release in data:
        if not isinstance(release, dict) or release.get("draft", False):
            continue

        tag_name = release.get("tag_name")
        if not isinstance(tag_name, str):
            raise RuntimeError(
                f"Expected the 'tag_name' to be a string, but got: {tag_name}"
            )

        download_url = next(
            (
                asset.get("browser_download_url")
                for asset in release.get("assets", [])
                if isinstance(asset, dict) and asset.get("name") == asset_name
            ),
            None,
        )

        if download_url is None:
            continue

        if not isinstance(download_url, str):
            raise RuntimeError(
                f"Expected the 'browser_download_url' of {asset_name} "
                f"in the release {tag_name} to be a string, but got: {download_url}"
            )

        if release.get("prerelease", False) and not include_prereleases:
            skipped_prereleases.append(tag_name)
            continue

        return _Release(tag_name=tag_name, url=download_url)

    message = f"No release at {url} contains {asset_name}"
    if len(skipped_prereleases) > 0:
        message += (
            f"; only the pre-release(s) {', '.join(skipped_prereleases)} do, "
            f"consider --include_prereleases"
        )

    raise RuntimeError(message)


def _download(url: str, destination: pathlib.Path) -> None:
    """Download the test data zip file."""
    response = requests.get(url, stream=True, timeout=30)
    response.raise_for_status()

    with open(destination, "wb") as f:
        f.writelines(response.iter_content(chunk_size=8192))


# fmt: off
@require(
    lambda zip_path:
    zip_path.name.endswith(".zip")
    and zip_path.exists()
    and zip_path.is_file()
)
# fmt: on
def _extract_zip_in_its_parent(zip_path: pathlib.Path) -> None:
    """Extract the archive in its directory."""
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(zip_path.parent)

    except Exception as exception:
        raise RuntimeError(
            f"Failed to unpack {zip_path} to {zip_path.parent}"
        ) from exception


def main() -> int:
    """Execute the main routine."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include_prereleases",
        help=(
            "If set, consider also the pre-releases when determining "
            "the latest version"
        ),
        action="store_true",
    )
    args = parser.parse_args()

    include_prereleases = bool(args.include_prereleases)

    release = _get_latest_release(include_prereleases=include_prereleases)
    print(f"Latest release with our test data: {release.tag_name}")

    test_data_dir = dev_scripts_common.REPO_ROOT / "dev" / "test_data"

    zip_path = (
        test_data_dir
        / f"test_data_for_{dev_scripts_common.version_stem()}.{uuid.uuid4()}.zip"
    )

    json_dir = test_data_dir / "Json"
    xml_dir = test_data_dir / "Xml"
    source_path = test_data_dir / "source.json"

    try:
        # NOTE (mristin):
        # We download before deleting the existing test data so that we do not
        # end up without any test data if the download fails.
        print(f"Downloading from: {release.url} to {zip_path} ...")
        _download(url=release.url, destination=zip_path)

        for directory in (json_dir, xml_dir):
            if directory.exists():
                print(f"Deleting existing {directory} ...")
                shutil.rmtree(directory)

        if source_path.exists():
            print(f"Deleting existing {source_path} ...")
            source_path.unlink()

        _extract_zip_in_its_parent(zip_path=zip_path)

        print(f"Writing the version to {source_path} ...")
        with source_path.open("wt") as fid:
            json.dump(
                collections.OrderedDict(
                    [("version", release.tag_name), ("url", release.url)]
                ),
                fid,
                indent=2,
            )

    finally:
        if zip_path.exists():
            print(f"Deleting {zip_path} ...")
            zip_path.unlink()

    return 0


if __name__ == "__main__":
    sys.exit(main())
