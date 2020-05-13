from pathlib import Path

import pytest

from ldndc2nc.extra import _find_config


@pytest.fixture
def mock_env_ldndc2nc(monkeypatch):
    monkeypatch.setenv("LDNDC2NC_CONF", "/tmp/ldndc2nc.conf")


@pytest.fixture
def mock_env_ldndc2nc_missing(monkeypatch):
    monkeypatch.setenv("LDNDC2NC_CONF", "__NOTSET__")


# NOTE: fs is a fixture provided by pyfakefs which patches itself into
# pytest when installed


@pytest.mark.parametrize("path", [Path("."), Path.home(), Path("/etc/ldndc2nc")])
def test_find_config_fs(fs, path):
    fs.create_file(path / "ldndc2nc.conf")
    assert _find_config() == Path(path / "ldndc2nc.conf")


def test_find_config_environ(fs, mock_env_ldndc2nc):
    custom_location = Path("/tmp/ldndc2nc.conf")
    fs.create_file(custom_location)
    assert _find_config() == custom_location


def test_find_config_environ_missing(fs, mock_env_ldndc2nc_missing):
    print(_find_config())
    assert _find_config() is None
