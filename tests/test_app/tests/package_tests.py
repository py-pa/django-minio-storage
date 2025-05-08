from importlib.metadata import version as package_version

from packaging.version import parse as parse_version

# Any version less than this is a bug, but versions greater are fine
MIN_VERSION = parse_version("0.5.7")


def test_package_version_file():
    from minio_storage.version import __version__

    version = parse_version(__version__)
    assert version >= MIN_VERSION


def test_package_version_metadata():
    version = parse_version(package_version("django_minio_storage"))
    assert version >= MIN_VERSION
