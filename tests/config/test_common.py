import inspect
from pathlib import Path
from typing import Any, Dict

import pytest

from cyclopts.config._common import ConfigFromFile


class Dummy(ConfigFromFile):
    def _load_config(self, path: Path) -> Dict[str, Any]:
        return {
            "key1": "foo1",
            "key2": "foo2",
            "function1": {
                "key1": "bar1",
                "key2": "bar2",
            },
        }


class DummyRootKeys(ConfigFromFile):
    def _load_config(self, path: Path) -> Dict[str, Any]:
        return {
            "tool": {
                "cyclopts": {
                    "key1": "foo1",
                    "key2": "foo2",
                    "function1": {
                        "key1": "bar1",
                        "key2": "bar2",
                    },
                }
            }
        }


def function1(key1, key2):
    pass


@pytest.fixture
def config(tmp_path):
    return Dummy(tmp_path / "cyclopts-config-test-file.dummy")


@pytest.fixture
def config_root_keys(tmp_path):
    return DummyRootKeys(tmp_path / "cyclopts-config-test-file.dummy")


@pytest.fixture
def bound():
    return {"key1": "cli1"}


@pytest.fixture
def apps():
    """App is only used as a dictionary in these tests."""
    return [{"function1": None}]


def test_config_common_root_keys_empty(apps, config, bound):
    config.path.touch()
    config(apps, (), bound)
    expected = {"key1": "cli1", "key2": "foo2"}
    assert expected == bound


def test_config_common_root_keys_populated(apps, config_root_keys, bound):
    config_root_keys.path.touch()
    config_root_keys.root_keys = ["tool", "cyclopts"]
    config_root_keys(apps, (), bound)
    expected = {"key1": "cli1", "key2": "foo2"}
    assert expected == bound


def test_config_common_must_exist_false(config, mocker):
    """If ``must_exist==False``, then the specified file is allowed to not exist.

    If the file does not exist, then have an empty config.
    """
    spy_load_config = mocker.spy(config, "_load_config")
    config.must_exist = False
    _ = config.config  # does NOT raise a FileNotFoundError
    assert config.config == {}
    spy_load_config.assert_not_called()


def test_config_common_must_exist_true(config):
    """If ``must_exist==True``, then the specified file must exist."""
    config.must_exist = True
    with pytest.raises(FileNotFoundError):
        _ = config.config


@pytest.mark.parametrize("must_exist", [True, False])
def test_config_common_search_parents_true_exists(tmp_path, must_exist, config, mocker):
    """Tests finding an existing parent."""
    spy_load_config = mocker.spy(config, "_load_config")

    original_path = config.path
    original_path.touch()
    config.path = tmp_path / "folder1" / "folder2" / "folder3" / "folder4" / config.path.name
    config.must_exist = must_exist
    config.search_parents = True

    _ = config.config

    spy_load_config.assert_called_once_with(original_path)


def test_config_common_must_exist_true_search_parents_true_missing(tmp_path, config, mocker):
    """Tests finding a missing parent."""
    spy_load_config = mocker.spy(config, "_load_config")

    config.path = tmp_path / "folder1" / "folder2" / "folder3" / "folder4" / config.path.name
    config.must_exist = True
    config.search_parents = True

    with pytest.raises(FileNotFoundError):
        _ = config.config

    spy_load_config.assert_not_called()


def test_config_common_must_exist_false_search_parents_true_missing(tmp_path, config, mocker):
    """Tests finding a missing parent."""
    spy_load_config = mocker.spy(config, "_load_config")

    config.path = tmp_path / "folder1" / "folder2" / "folder3" / "folder4" / config.path.name
    config.must_exist = False
    config.search_parents = True

    assert config.config == {}

    spy_load_config.assert_not_called()
