from pathlib import Path

import pkg_resources
import pytest

from ldndc2nc.config_handler import ConfigHandler, find_config


@pytest.fixture
def mock_env_ldndc2nc(monkeypatch):
    monkeypatch.setenv("LDNDC2NC_CONF", "/tmp/ldndc2nc.conf")


@pytest.fixture
def mock_env_ldndc2nc_missing(monkeypatch):
    monkeypatch.setenv("LDNDC2NC_CONF", "__NOTSET__")


@pytest.fixture
def fs_with_config_file(fs):
    fs.add_real_file(
        pkg_resources.resource_filename("ldndc2nc", "data/ldndc2nc.conf"),
        target_path=Path.home(),
    )
    yield fs


# NOTE: fs is a fixture provided by pyfakefs which patches itself into
# pytest when installed


@pytest.mark.parametrize("path", [Path("."), Path.home(), Path("/etc/ldndc2nc")])
def test_find_config_fs(fs, path):
    fs.create_file(path / "ldndc2nc.conf")
    assert find_config() == Path(path / "ldndc2nc.conf")


def test_find_config_custom(fs):
    custom = "/tmp/custom.conf"
    fs.create_file(custom)
    assert find_config(custom) == Path(custom)


def test_find_config_environ(fs, mock_env_ldndc2nc):
    custom_location = Path("/tmp/ldndc2nc.conf")
    fs.create_file(custom_location)
    assert find_config() == custom_location


def test_find_config_environ_missing(fs, mock_env_ldndc2nc_missing):
    assert find_config() is None


@pytest.fixture(scope="class")
def handler():
    return ConfigHandler()


class TestConfigHandler:
    def test_read_config(self, handler, fs_with_config_file):
        assert handler.cfg is not None

    @pytest.mark.parametrize(
        "path,expected",
        [(Path.home() / "ldndc2nc.conf", True), (Path("bad/ldndc2nc.conf"), False)],
    )
    def test_find_path(self, handler, fs_with_config_file, path, expected):
        assert (handler.file_path == path) == expected

    def test_variables(self, handler, fs_with_config_file):
        assert len(handler.variables) > 0

    @pytest.mark.parametrize(
        "section,expected",
        [("variables", False), ("VARIABLES", False), ("refdata", True)],
    )
    def test_section(self, handler, fs_with_config_file, section, expected):
        assert (handler.section(section) is None) == expected

    def test_section_unknown(self, handler, fs_with_config_file):
        with pytest.raises(RuntimeError):
            handler.section("_Variables")

    def test_global_info(self, handler, fs_with_config_file):
        # global info data present in default ldndc2nc.conf file
        global_info_entries = {"author", "email", "institution", "name", "version"}
        assert set(handler.global_info.keys()) == global_info_entries
