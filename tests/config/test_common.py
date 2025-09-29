from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

import pytest

from cyclopts.argument import Token
from cyclopts.config._common import ConfigFromFile
from cyclopts.exceptions import CycloptsError
from cyclopts.parameter import Parameter


class DummyErrorConfigNoMsg(ConfigFromFile):
    def _load_config(self, path: Path) -> dict[str, Any]:
        raise ValueError


class DummyErrorConfigMsg(ConfigFromFile):
    def _load_config(self, path: Path) -> dict[str, Any]:
        raise ValueError("My exception's message.")


class Dummy(ConfigFromFile):
    def _load_config(self, path: Path) -> dict[str, Any]:
        return {
            "key1": "foo1",
            "key2": "foo2",
            "function1": {
                "key1": "bar1",
                "key2": "bar2",
            },
            "meta_param": 123,
        }


class DummyRootKeys(ConfigFromFile):
    def _load_config(self, path: Path) -> dict[str, Any]:
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


class DummySubKeys(ConfigFromFile):
    def _load_config(self, path: Path) -> dict[str, Any]:
        return {
            "key1": {
                "subkey1": ["subkey1val1", "subkey1val2"],
                "subkey2": ["subkey2val1", "subkey2val2"],
            },
            "key2": "foo2",
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
def config_sub_keys(tmp_path):
    return DummySubKeys(tmp_path / "cyclopts-config-test-file.dummy")


@pytest.fixture
def configured_app(app):
    @app.command
    def function1():
        pass

    @app.default
    def foo(key1, key2):
        pass

    @app.meta.default
    def meta(
        *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
        meta_param: Annotated[int, Parameter(negative=())] = 42,
    ):
        pass

    return app


def test_config_common_root_keys_empty(configured_app, config):
    config.path.touch()
    configured_app.config = config
    _, _, _, _, argument_collection = configured_app._parse_known_args("--key1 cli1")
    assert len(argument_collection) == 2
    assert argument_collection[0].tokens == [Token(keyword="--key1", value="cli1", source="cli")]
    assert argument_collection[1].tokens == [Token(keyword="[key2]", value="foo2", source=str(config.path))]


def test_config_common_root_keys_populated(configured_app, config_root_keys):
    configured_app.config = config_root_keys
    config_root_keys.path.touch()
    config_root_keys.root_keys = ["tool", "cyclopts"]
    _, _, _, _, argument_collection = configured_app._parse_known_args("--key1 cli1")

    assert len(argument_collection) == 2
    assert argument_collection[0].tokens == [Token(keyword="--key1", value="cli1", source="cli")]
    assert argument_collection[1].tokens == [
        Token(keyword="[tool][cyclopts][key2]", value="foo2", source=str(config_root_keys.path))
    ]


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
def test_config_common_search_parents_absolute_true_exists(tmp_path, must_exist, config, mocker):
    """Tests finding an existing parent if path is absolute."""
    spy_load_config = mocker.spy(config, "_load_config")

    original_path = config.path
    original_path.touch()
    config.path = tmp_path / "folder1" / "folder2" / "folder3" / "folder4" / config.path.name
    config.must_exist = must_exist
    config.search_parents = True

    _ = config.config

    spy_load_config.assert_called_once_with(original_path)


def test_config_common_search_parents_relative_true_exists(tmp_path, mocker, monkeypatch):
    """Tests finding an existing parent if path is relative."""
    config_path = tmp_path / "cyclopts-config-test-file.dummy"
    config_path.touch()
    config = Dummy("cyclopts-config-test-file.dummy", search_parents=True)
    spy_load_config = mocker.spy(config, "_load_config")

    deep_dir = tmp_path / "foo" / "bar" / "baz"
    deep_dir.mkdir(parents=True)
    monkeypatch.chdir(deep_dir)

    _ = config.config

    spy_load_config.assert_called_once_with(config_path.resolve())


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


def test_config_common_kwargs(app, config):
    """Make sure that we don't look for the string "kwargs" as a key."""
    app.config = config
    config.path.touch()

    @app.default
    def foo(key1, **kwargs):
        pass

    # Define these commands so that their corresponding keys in the config do not get interpreted for kwargs.
    @app.command
    def function1():
        pass

    @app.meta.default
    def meta(
        *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
        meta_param: Annotated[int, Parameter(negative=())] = 42,
    ):
        pass

    _, _, _, _, argument_collection = app._parse_known_args("--key1 foo1")

    # Don't attempt to parse the key ``"kwargs"`` from config.
    assert len(argument_collection) == 2
    assert argument_collection[-1].tokens == [
        Token(keyword="[key2]", value="foo2", source=str(config.path.absolute()), index=0, keys=("key2",)),
    ]


def test_config_common_subkeys(app, config_sub_keys):
    config_sub_keys.path.touch()
    app.config = config_sub_keys

    @dataclass
    class Example:
        subkey1: list[str]
        subkey2: list[str]

    @app.default
    def foo(key1: Example, key2):
        pass

    _, _, _, _, argument_collection = app._parse_known_args("")

    assert len(argument_collection) == 4

    assert len(argument_collection[0].tokens) == 0

    assert len(argument_collection[1].tokens) == 2
    assert argument_collection[1].tokens[0].keyword == "[key1][subkey1]"
    assert argument_collection[1].tokens[0].value == "subkey1val1"
    assert argument_collection[1].tokens[0].index == 0
    assert argument_collection[1].tokens[0].keys == ()
    assert argument_collection[1].tokens[0].source.endswith("cyclopts-config-test-file.dummy")
    assert argument_collection[1].tokens[1].keyword == "[key1][subkey1]"
    assert argument_collection[1].tokens[1].value == "subkey1val2"
    assert argument_collection[1].tokens[1].index == 1
    assert argument_collection[1].tokens[1].keys == ()
    assert argument_collection[1].tokens[1].source.endswith("cyclopts-config-test-file.dummy")

    assert len(argument_collection[2].tokens) == 2
    assert argument_collection[2].tokens[0].keyword == "[key1][subkey2]"
    assert argument_collection[2].tokens[0].value == "subkey2val1"
    assert argument_collection[2].tokens[0].index == 0
    assert argument_collection[2].tokens[0].keys == ()
    assert argument_collection[2].tokens[0].source.endswith("cyclopts-config-test-file.dummy")
    assert argument_collection[2].tokens[1].keyword == "[key1][subkey2]"
    assert argument_collection[2].tokens[1].value == "subkey2val2"
    assert argument_collection[2].tokens[1].index == 1
    assert argument_collection[2].tokens[1].keys == ()
    assert argument_collection[2].tokens[1].source.endswith("cyclopts-config-test-file.dummy")

    assert len(argument_collection[3].tokens) == 1
    assert argument_collection[3].tokens[0].keyword == "[key2]"
    assert argument_collection[3].tokens[0].value == "foo2"
    assert argument_collection[3].tokens[0].index == 0
    assert argument_collection[3].tokens[0].keys == ()
    assert argument_collection[3].tokens[0].source.endswith("cyclopts-config-test-file.dummy")


def test_config_exception_during_load_config_no_msg(tmp_path):
    path = tmp_path / "config"
    path.touch()
    dummy_error_config = DummyErrorConfigNoMsg(path)
    with pytest.raises(CycloptsError) as e:
        _ = dummy_error_config.config
    assert str(e.value) == "ValueError"


def test_config_exception_during_load_config_msg(tmp_path):
    path = tmp_path / "config"
    path.touch()
    dummy_error_config = DummyErrorConfigMsg(path)
    with pytest.raises(CycloptsError) as e:
        _ = dummy_error_config.config
    assert str(e.value) == "ValueError: My exception's message."
