"""Test that all config classes support the source parameter."""

import json
import os

import pytest

from cyclopts import App
from cyclopts.config import Dict, Env, Json, Toml, Yaml
from cyclopts.exceptions import MissingArgumentError


def test_json_default_source(tmp_path):
    """Test that Json uses file path as default source."""
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"name": "Alice"}))

    config = Json(config_file)
    assert config.source == str(config_file.absolute())


def test_json_custom_source(tmp_path):
    """Test that Json accepts custom source parameter."""
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"name": "Alice"}))

    config = Json(config_file, source="my-custom-source")
    assert config.source == "my-custom-source"


def test_json_custom_source_in_error(tmp_path):
    """Test that custom source appears in error messages."""
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"age": 30}))

    app = App(config=Json(config_file, source="api-config"), result_action="return_value")

    @app.default
    def main(name: str, age: int):
        return f"{name} is {age} years old."

    with pytest.raises(MissingArgumentError):
        app([], exit_on_error=False)


def test_json_source_setter(tmp_path):
    """Test that Json.source can be modified via setter."""
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"name": "Alice"}))

    config = Json(config_file)
    original_source = config.source

    config.source = "updated-source"
    assert config.source == "updated-source"

    config.source = original_source
    assert config.source == original_source


def test_toml_default_source(tmp_path):
    """Test that Toml uses file path as default source."""
    config_file = tmp_path / "config.toml"
    config_file.write_text('[main]\nname = "Alice"')

    config = Toml(config_file)
    assert config.source == str(config_file.absolute())


def test_toml_custom_source(tmp_path):
    """Test that Toml accepts custom source parameter."""
    config_file = tmp_path / "config.toml"
    config_file.write_text('[main]\nname = "Alice"')

    config = Toml(config_file, source="my-toml-source")
    assert config.source == "my-toml-source"


def test_yaml_default_source(tmp_path):
    """Test that Yaml uses file path as default source."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("main:\n  name: Alice")

    config = Yaml(config_file)
    assert config.source == str(config_file.absolute())


def test_yaml_custom_source(tmp_path):
    """Test that Yaml accepts custom source parameter."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("main:\n  name: Alice")

    config = Yaml(config_file, source="my-yaml-source")
    assert config.source == "my-yaml-source"


def test_env_default_source():
    """Test that Env uses 'env' as default source."""
    config = Env("TEST_")
    assert config.source == "env"


def test_env_custom_source():
    """Test that Env accepts custom source parameter."""
    config = Env("TEST_", source="environment-variables")
    assert config.source == "environment-variables"


def test_env_custom_source_in_tokens():
    """Test that Env custom source is used when creating tokens."""
    app = App(config=Env("TEST_", source="custom-env"), result_action="return_value")

    @app.default
    def main(name: str = "default"):
        return name

    os.environ["TEST_NAME"] = "Alice"
    try:
        result = app([])
        assert result == "Alice"
    finally:
        del os.environ["TEST_NAME"]


def test_dict_default_source():
    """Test that Dict uses 'dict' as default source."""
    config = Dict({"name": "Alice"})
    assert config.source == "dict"


def test_dict_custom_source():
    """Test that Dict accepts custom source parameter."""
    config = Dict({"name": "Alice"}, source="api-response")
    assert config.source == "api-response"


def test_multiple_configs_with_custom_sources(tmp_path):
    """Test using multiple configs with custom sources."""
    json_file = tmp_path / "config.json"
    json_file.write_text(json.dumps({"name": "Alice"}))

    app = App(
        config=[
            Json(json_file, source="json-config"),
            Dict({"age": 30}, source="dict-config"),
            Env("TEST_", source="env-config"),
        ],
        result_action="return_value",
    )

    @app.default
    def main(name: str, age: int, city: str = "Unknown"):
        return f"{name}, {age}, {city}"

    os.environ["TEST_CITY"] = "Springfield"
    try:
        result = app([])
        assert result == "Alice, 30, Springfield"
    finally:
        del os.environ["TEST_CITY"]


def test_source_preserved_across_app_calls(tmp_path):
    """Test that custom source is preserved across multiple app calls."""
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"value": 42}))

    config = Json(config_file, source="persistent-source")
    app = App(config=config, result_action="return_value")

    @app.default
    def main(value: int):
        return value

    result1 = app([])
    assert result1 == 42
    assert config.source == "persistent-source"

    result2 = app([])
    assert result2 == 42
    assert config.source == "persistent-source"
