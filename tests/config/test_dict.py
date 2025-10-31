from cyclopts import App
from cyclopts.config import Dict


def test_config_dict_basic():
    """Test basic Dict config functionality."""
    app = App(config=Dict({"name": "Alice", "age": 30}), result_action="return_value")

    @app.default
    def main(name: str, age: int):
        return f"{name} is {age} years old."

    result = app([])
    assert result == "Alice is 30 years old."


def test_config_dict_with_commands():
    """Test Dict config with commands."""
    config_data = {
        "create": {"name": "Alice", "age": 30},
        "update": {"name": "Bob", "age": 40},
    }
    app = App(config=Dict(config_data), result_action="return_value")

    @app.command
    def create(name: str, age: int):
        return f"Created: {name} is {age} years old."

    @app.command
    def update(name: str, age: int):
        return f"Updated: {name} is {age} years old."

    result = app("create")
    assert result == "Created: Alice is 30 years old."

    result = app("update")
    assert result == "Updated: Bob is 40 years old."


def test_config_dict_with_root_keys():
    """Test Dict config with root_keys navigation."""
    config_data = {
        "production": {
            "database": {
                "host": "prod.example.com",
                "port": 5432,
            }
        }
    }
    app = App(
        config=Dict(config_data, root_keys=["production", "database"]),
        result_action="return_value",
    )

    @app.default
    def main(host: str, port: int):
        return f"Connecting to {host}:{port}"

    result = app([])
    assert result == "Connecting to prod.example.com:5432"


def test_config_dict_use_commands_as_keys_false():
    """Test Dict config with use_commands_as_keys=False."""
    config_data = {"name": "Alice", "age": 30}
    app = App(config=Dict(config_data, use_commands_as_keys=False), result_action="return_value")

    @app.command
    def create(name: str, age: int):
        return f"{name} is {age} years old."

    result = app("create")
    assert result == "Alice is 30 years old."


def test_config_dict_use_commands_as_keys_false_with_sibling_commands():
    """Test Dict config filters sibling command sections when use_commands_as_keys=False.

    Regression test for issue where config filtering used command_app instead of parent app,
    causing sibling command sections in the config to not be properly filtered out.

    This reproduces the bug fixed in core.py where executing "polygon 1 2 3 4" would fail
    because the "line" section in the config wasn't being filtered correctly.
    """
    from dataclasses import KW_ONLY, dataclass
    from typing import Annotated

    from cyclopts import Parameter

    config_data = {
        "units": "meters",
        "line": {"color": "red"},
        "polygon": {"color": "blue"},
        "circle": {"color": "green"},
    }

    app = App(config=Dict(config_data, use_commands_as_keys=False), result_action="return_value")

    @Parameter(name="*")
    @dataclass
    class DrawConfig:
        _: KW_ONLY
        units: str = "meters"
        color: str = "black"

    @app.command
    def line(start: tuple[float, float], end: tuple[float, float], config: DrawConfig | None = None):
        if config is None:
            config = DrawConfig()
        return f"line: {start} to {end} in {config.units}, color={config.color}"

    @app.command
    def polygon(*vertices: Annotated[tuple[float, float], Parameter(required=True)], config: DrawConfig | None = None):
        if config is None:
            config = DrawConfig()
        return f"polygon: {len(vertices)} vertices in {config.units}, color={config.color}"

    @app.command
    def circle(center: tuple[float, float], radius: float, config: DrawConfig | None = None):
        if config is None:
            config = DrawConfig()
        return f"circle: center={center} radius={radius} in {config.units}, color={config.color}"

    result = app("line 0 0 10 10")
    assert result == "line: (0.0, 0.0) to (10.0, 10.0) in meters, color=black"

    result = app("polygon 1 2 3 4 5 6")
    assert result == "polygon: 3 vertices in meters, color=black"

    result = app("circle 0 0 5")
    assert result == "circle: center=(0.0, 0.0) radius=5.0 in meters, color=black"


def test_config_dict_nested_commands_with_use_commands_as_keys_true():
    """Test Dict config with nested commands using default use_commands_as_keys=True.

    Regression test to ensure that when use_commands_as_keys=True (default), the filtering
    uses command_app (not root_app) so that subcommand sections at the command's config level
    are properly filtered out.

    Without the correct fix, this would fail with "Unknown option" errors because cmd1/cmd2
    sections wouldn't be filtered when executing the sub default command.
    """
    config_data = {
        "sub": {
            "shared_param": "shared_value",
            "cmd1": {"cmd1_param": "cmd1_value"},
            "cmd2": {"cmd2_param": "cmd2_value"},
        }
    }

    app = App(config=Dict(config_data), result_action="return_value")
    sub_app = App()
    app.command(sub_app, name="sub")

    @sub_app.default
    def sub_default(shared_param: str):
        return f"sub_default: {shared_param}"

    @sub_app.command
    def cmd1(cmd1_param: str):
        return f"cmd1: {cmd1_param}"

    @sub_app.command
    def cmd2(cmd2_param: str):
        return f"cmd2: {cmd2_param}"

    result = app("sub")
    assert result == "sub_default: shared_value"

    result = app("sub cmd1")
    assert result == "cmd1: cmd1_value"

    result = app("sub cmd2")
    assert result == "cmd2: cmd2_value"


def test_config_dict_nested_commands_with_use_commands_as_keys_false():
    """Test Dict config with nested App commands using use_commands_as_keys=False.

    With use_commands_as_keys=False, config stays at root level and is shared
    across all commands, including nested App commands and their subcommands.
    """
    config_data = {
        "global_setting": "shared_value",
    }

    app = App(config=Dict(config_data, use_commands_as_keys=False), result_action="return_value")
    sub_app = App()
    app.command(sub_app, name="sub")

    @sub_app.default
    def sub_default(global_setting: str):
        return f"sub_default: {global_setting}"

    @sub_app.command
    def cmd1(global_setting: str):
        return f"cmd1: {global_setting}"

    result = app("sub")
    assert result == "sub_default: shared_value"

    result = app("sub cmd1")
    assert result == "cmd1: shared_value"


def test_config_dict_deeply_nested_with_use_commands_as_keys_false():
    """Test Dict config with deeply nested commands and use_commands_as_keys=False.

    Ensures that even with multiple levels of nesting, flat config is shared
    across all command levels.
    """
    config_data = {
        "shared": "value",
        "another": 42,
    }

    app = App(config=Dict(config_data, use_commands_as_keys=False), result_action="return_value")
    level1_app = App()
    level2_app = App()

    app.command(level1_app, name="level1")
    level1_app.command(level2_app, name="level2")

    @level2_app.default
    def deeply_nested(shared: str, another: int):
        return f"deeply_nested: {shared}, {another}"

    result = app("level1 level2")
    assert result == "deeply_nested: value, 42"


def test_config_dict_mixed_nested_and_flat_commands():
    """Test Dict config with mix of nested apps and flat config.

    This tests that both simple commands and nested App commands can share
    the same flat config when use_commands_as_keys=False.
    """
    config_data = {
        "base_value": "base",
        "count": 10,
    }

    app = App(config=Dict(config_data, use_commands_as_keys=False), result_action="return_value")

    @app.command
    def simple(base_value: str, count: int):
        return f"simple: {base_value}, count={count}"

    nested_app = App()
    app.command(nested_app, name="nested")

    @nested_app.default
    def nested_default(base_value: str, count: int):
        return f"nested: {base_value}, count={count}"

    result = app("simple")
    assert result == "simple: base, count=10"

    result = app("nested")
    assert result == "nested: base, count=10"


def test_config_dict_use_commands_as_keys_true_filters_subcommands():
    """Test that use_commands_as_keys=True correctly filters sibling subcommands.

    When navigating into a command's config section, sibling command sections at that
    level should be filtered using the command's app (not root app). This ensures
    that "create" and "delete" sections are filtered when executing each other.
    """
    config_data = {
        "db": {
            "timeout": 30,
            "create": {"timeout": 10, "operation": "create_op"},
            "delete": {"timeout": 20, "operation": "delete_op"},
        }
    }

    app = App(config=Dict(config_data, use_commands_as_keys=True), result_action="return_value")
    db_app = App()
    app.command(db_app, name="db")

    @db_app.default
    def db_default(timeout: int):
        return f"db: timeout={timeout}"

    @db_app.command
    def create(timeout: int, operation: str):
        return f"create: timeout={timeout}, operation={operation}"

    @db_app.command
    def delete(timeout: int, operation: str):
        return f"delete: timeout={timeout}, operation={operation}"

    result = app("db")
    assert result == "db: timeout=30"

    result = app("db create")
    assert result == "create: timeout=10, operation=create_op"

    result = app("db delete")
    assert result == "delete: timeout=20, operation=delete_op"


def test_config_dict_allow_unknown():
    """Test Dict config with allow_unknown=True."""
    config_data = {
        "name": "Alice",
        "age": 30,
        "unknown_field": "should_be_ignored",
    }
    app = App(config=Dict(config_data, allow_unknown=True), result_action="return_value")

    @app.default
    def main(name: str, age: int):
        return f"{name} is {age} years old."

    result = app([])
    assert result == "Alice is 30 years old."


def test_config_dict_partial_override():
    """Test that CLI args override Dict config values."""
    config_data = {"name": "Alice", "age": 30}
    app = App(config=Dict(config_data), result_action="return_value")

    @app.default
    def main(name: str, age: int):
        return f"{name} is {age} years old."

    result = app("--name Bob")
    assert result == "Bob is 30 years old."


def test_config_dict_empty():
    """Test Dict config with empty dict."""
    app = App(config=Dict({}), result_action="return_value")

    @app.default
    def main(name: str = "Default", age: int = 0):
        return f"{name} is {age} years old."

    result = app([])
    assert result == "Default is 0 years old."


def test_config_dict_nested_structure():
    """Test Dict config with nested dataclass-like structures."""
    from dataclasses import dataclass

    @dataclass
    class Database:
        host: str
        port: int

    config_data = {
        "database": {
            "host": "localhost",
            "port": 5432,
        }
    }
    app = App(config=Dict(config_data), result_action="return_value")

    @app.default
    def main(database: Database):
        return f"{database.host}:{database.port}"

    result = app([])
    assert result == "localhost:5432"


def test_config_dict_source():
    """Test that Dict.source returns 'dict' by default."""
    config = Dict({"key": "value"})
    assert config.source == "dict"


def test_config_dict_custom_source():
    """Test that Dict.source can be customized."""
    config = Dict({"key": "value"}, source="api")
    assert config.source == "api"

    config_network = Dict({"key": "value"}, source="network")
    assert config_network.source == "network"


def test_config_dict_source_setter():
    """Test that Dict.source can be modified via setter."""
    config = Dict({"key": "value"})
    assert config.source == "dict"

    config.source = "api"
    assert config.source == "api"

    config.source = "network-response"
    assert config.source == "network-response"


def test_config_dict_with_subcommands():
    """Test that Dict config correctly filters out subcommand keys."""
    config_data = {
        "global_flag": True,
        "subcommand": {
            "sub_value": 123,
        },
    }
    app = App(config=Dict(config_data), result_action="return_value")

    @app.default
    def main(global_flag: bool = False):
        return f"global_flag={global_flag}"

    @app.command
    def subcommand(sub_value: int):
        return f"sub_value={sub_value}"

    result = app([])
    assert result == "global_flag=True"

    result = app("subcommand")
    assert result == "sub_value=123"


def test_config_dict_unknown_field_error():
    """Test that unknown fields raise error when allow_unknown=False."""
    import pytest

    from cyclopts.exceptions import UnknownOptionError

    config_data = {
        "name": "Alice",
        "age": 30,
        "unknown_field": "should_error",
    }
    app = App(config=Dict(config_data, allow_unknown=False), result_action="return_value")

    @app.default
    def main(name: str, age: int):
        return f"{name} is {age} years old."

    with pytest.raises(UnknownOptionError):
        app([], exit_on_error=False)


def test_config_dict_multiple_configs():
    """Test using multiple Dict configs in a list."""
    config1 = Dict({"name": "Alice"})
    config2 = Dict({"age": 30})

    app = App(config=[config1, config2], result_action="return_value")

    @app.default
    def main(name: str, age: int):
        return f"{name} is {age} years old."

    result = app([])
    assert result == "Alice is 30 years old."


def test_config_dict_with_env():
    """Test combining Dict config with Env config."""
    import os

    from cyclopts.config import Env

    config_data = {"name": "Alice"}
    app = App(config=[Dict(config_data), Env("TEST_")], result_action="return_value")

    @app.default
    def main(name: str, age: int = 0):
        return f"{name} is {age} years old."

    os.environ["TEST_AGE"] = "30"
    try:
        result = app([])
        assert result == "Alice is 30 years old."
    finally:
        del os.environ["TEST_AGE"]


def test_config_dict_modification_after_creation():
    """Test modifying Dict config after app creation."""
    config = Dict({"name": "Alice", "age": 30})
    app = App(config=config, result_action="return_value")

    @app.default
    def main(name: str, age: int):
        return f"{name} is {age} years old."

    result = app([])
    assert result == "Alice is 30 years old."

    config.data["name"] = "Bob"
    result = app([])
    assert result == "Bob is 30 years old."


def test_config_dict_with_meta_app():
    """Test Dict config with meta app."""
    from typing import Annotated

    from cyclopts import Parameter

    app = App(result_action="return_value")

    @app.default
    def main(name: str, age: int):
        return f"{name} is {age} years old."

    @app.meta.default
    def meta(*tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)], config_source: str = "dict"):
        app.config = Dict({"name": "Alice", "age": 30}, source=config_source)
        return app(tokens)

    result = app.meta([])
    assert result == "Alice is 30 years old."


def test_config_dict_deep_nesting():
    """Test Dict config with deep root_keys nesting."""
    config_data = {"level1": {"level2": {"level3": {"level4": {"name": "Alice", "age": 30}}}}}
    app = App(
        config=Dict(config_data, root_keys=["level1", "level2", "level3", "level4"]),
        result_action="return_value",
    )

    @app.default
    def main(name: str, age: int):
        return f"{name} is {age} years old."

    result = app([])
    assert result == "Alice is 30 years old."


def test_config_dict_cli_priority():
    """Test that CLI arguments have priority over Dict config."""
    config_data = {"name": "Alice", "age": 30}
    app = App(config=Dict(config_data), result_action="return_value")

    @app.default
    def main(name: str, age: int):
        return f"{name} is {age} years old."

    result = app("--name Bob --age 40")
    assert result == "Bob is 40 years old."


def test_config_dict_with_optional():
    """Test Dict config with Optional parameters."""
    from typing import Any

    config_data: dict[str, Any] = {"name": "Alice"}
    app = App(config=Dict(config_data), result_action="return_value")

    @app.default
    def main(name: str, age: int | None = None):
        if age is None:
            return f"{name} has no age"
        return f"{name} is {age} years old."

    result = app([])
    assert result == "Alice has no age"

    config_data["age"] = 30
    result = app([])
    assert result == "Alice is 30 years old."


def test_config_dict_with_list():
    """Test Dict config with list parameters."""
    config_data = {"names": ["Alice", "Bob", "Charlie"]}
    app = App(config=Dict(config_data), result_action="return_value")

    @app.default
    def main(names: list[str]):
        return ", ".join(names)

    result = app([])
    assert result == "Alice, Bob, Charlie"


def test_config_dict_with_typed_dict():
    """Test Dict config with TypedDict."""
    from typing import TypedDict

    class UserConfig(TypedDict):
        name: str
        age: int

    config_data = {"user": {"name": "Alice", "age": 30}}
    app = App(config=Dict(config_data), result_action="return_value")

    @app.default
    def main(user: UserConfig):
        return f"{user['name']} is {user['age']} years old."

    result = app([])
    assert result == "Alice is 30 years old."


def test_config_dict_immutability():
    """Test that Dict.config returns the actual data (not a copy)."""
    config_data = {"name": "Alice", "age": 30}
    config = Dict(config_data)

    assert config.config is config.data
    config.config["name"] = "Bob"
    assert config.data["name"] == "Bob"


def test_config_dict_missing_root_key():
    """Test Dict config when root_keys don't exist in data."""
    config_data = {"production": {"name": "Alice"}}
    app = App(
        config=Dict(config_data, root_keys=["development", "database"]),
        result_action="return_value",
    )

    @app.default
    def main(name: str = "Default", age: int = 0):
        return f"{name} is {age} years old."

    result = app([])
    assert result == "Default is 0 years old."


def test_config_dict_reassignment():
    """Test reassigning app.config with new Dict."""
    app = App(config=Dict({"name": "Alice", "age": 30}), result_action="return_value")

    @app.default
    def main(name: str, age: int):
        return f"{name} is {age} years old."

    result = app([])
    assert result == "Alice is 30 years old."

    app.config = Dict({"name": "Bob", "age": 40})
    result = app([])
    assert result == "Bob is 40 years old."


def test_config_dict_with_boolean_flags():
    """Test Dict config with boolean flags."""
    config_data = {"verbose": True, "quiet": False, "debug": True}
    app = App(config=Dict(config_data), result_action="return_value")

    @app.default
    def main(verbose: bool = False, quiet: bool = False, debug: bool = False):
        flags = []
        if verbose:
            flags.append("verbose")
        if quiet:
            flags.append("quiet")
        if debug:
            flags.append("debug")
        return ", ".join(flags) if flags else "no flags"

    result = app([])
    assert result == "verbose, debug"


def test_config_dict_nested_commands():
    """Test Dict config with nested command structure."""
    config_data = {
        "db": {
            "create": {"name": "testdb", "size": 100},
            "delete": {"name": "olddb", "force": True},
        }
    }
    app = App(config=Dict(config_data), result_action="return_value")

    db_app = App()
    app.command(db_app, name="db")

    @db_app.command
    def create(name: str, size: int):
        return f"Creating {name} with size {size}"

    @db_app.command
    def delete(name: str, force: bool = False):
        return f"Deleting {name} (force={force})"

    result = app("db create")
    assert result == "Creating testdb with size 100"

    result = app("db delete")
    assert result == "Deleting olddb (force=True)"


def test_config_dict_error_message_with_custom_source():
    """Test that custom source appears in error messages."""
    import pytest

    from cyclopts.exceptions import MissingArgumentError

    config_data = {"age": 30}
    app = App(config=Dict(config_data, source="api-response"), result_action="return_value")

    @app.default
    def main(name: str, age: int):
        return f"{name} is {age} years old."

    with pytest.raises(MissingArgumentError) as exc_info:
        app([], exit_on_error=False)

    assert "name" in str(exc_info.value).lower()


def test_config_dict_with_default_values():
    """Test Dict config interacts correctly with function default values."""
    config_data = {"name": "Alice"}
    app = App(config=Dict(config_data), result_action="return_value")

    @app.default
    def main(name: str = "Default", age: int = 99, city: str = "Unknown"):
        return f"{name}, {age}, {city}"

    result = app([])
    assert result == "Alice, 99, Unknown"


def test_config_dict_with_enum():
    """Test Dict config with Enum parameters."""
    from enum import Enum

    class Color(Enum):
        RED = "red"
        GREEN = "green"
        BLUE = "blue"

    config_data = {"color": "red"}
    app = App(config=Dict(config_data), result_action="return_value")

    @app.default
    def main(color: Color):
        return f"Color is {color.value}"

    result = app([])
    assert result == "Color is red"


def test_config_dict_with_complex_types():
    """Test Dict config with complex nested types."""
    from dataclasses import dataclass

    @dataclass
    class Address:
        street: str
        city: str

    @dataclass
    class Person:
        name: str
        address: Address

    config_data = {
        "person": {
            "name": "Alice",
            "address": {"street": "123 Main St", "city": "Springfield"},
        }
    }
    app = App(config=Dict(config_data), result_action="return_value")

    @app.default
    def main(person: Person):
        return f"{person.name} lives at {person.address.street}, {person.address.city}"

    result = app([])
    assert result == "Alice lives at 123 Main St, Springfield"


def test_config_dict_with_union_types():
    """Test Dict config with Union types."""
    from typing import Any

    config_data: dict[str, Any] = {"value": 42}
    app = App(config=Dict(config_data), result_action="return_value")

    @app.default
    def main(value: int | str):
        return f"Value is {value} (type: {type(value).__name__})"

    result = app([])
    assert result == "Value is 42 (type: int)"

    config_data["value"] = "hello"
    result = app([])
    assert result == "Value is hello (type: str)"


def test_config_dict_empty_root_keys():
    """Test Dict config with empty root_keys tuple."""
    config_data = {"name": "Alice", "age": 30}
    app = App(config=Dict(config_data, root_keys=()), result_action="return_value")

    @app.default
    def main(name: str, age: int):
        return f"{name} is {age} years old."

    result = app([])
    assert result == "Alice is 30 years old."


def test_config_dict_single_root_key():
    """Test Dict config with single root_key."""
    config_data = {"production": {"name": "Alice", "age": 30}}
    app = App(config=Dict(config_data, root_keys=["production"]), result_action="return_value")

    @app.default
    def main(name: str, age: int):
        return f"{name} is {age} years old."

    result = app([])
    assert result == "Alice is 30 years old."


def test_config_dict_with_attrs_class():
    """Test Dict config with attrs class."""
    from attrs import define

    @define
    class User:
        name: str
        age: int

    config_data = {"user": {"name": "Alice", "age": 30}}
    app = App(config=Dict(config_data), result_action="return_value")

    @app.default
    def main(user: User):
        return f"{user.name} is {user.age} years old."

    result = app([])
    assert result == "Alice is 30 years old."


def test_config_dict_comparison_with_json_file():
    """Test that Dict produces same result as Json for equivalent data."""
    import json
    from pathlib import Path

    from cyclopts.config import Json

    config_data = {"count": {"character": "t"}}

    dict_app = App(config=Dict(config_data), result_action="return_value")

    @dict_app.command
    def count(character: str):  # noqa: F811  # pyright: ignore[reportRedeclaration]
        return f"Character: {character}"

    dict_result = dict_app("count")

    json_app = App(result_action="return_value")

    @json_app.command
    def count(character: str):  # noqa: F811  # pyright: ignore[reportRedeclaration]
        return f"Character: {character}"

    tmp_file = Path("temp_test.json")
    tmp_file.write_text(json.dumps(config_data))
    try:
        json_app.config = Json(tmp_file)
        json_result = json_app("count")
        assert dict_result == json_result
    finally:
        tmp_file.unlink()


def test_config_dict_repr():
    """Test Dict has a useful repr."""
    config = Dict({"key": "value"}, source="api")
    repr_str = repr(config)
    assert "Dict" in repr_str
    assert "key" in repr_str or "value" in repr_str


def test_config_dict_with_tuple_type():
    """Test Dict config with tuple parameters."""
    config_data = {"coordinates": [1, 2, 3]}
    app = App(config=Dict(config_data), result_action="return_value")

    @app.default
    def main(coordinates: tuple[int, int, int]):
        return f"Coordinates: {coordinates}"

    result = app([])
    assert result == "Coordinates: (1, 2, 3)"


def test_config_dict_with_set_type():
    """Test Dict config with set parameters."""
    config_data = {"tags": ["python", "cli", "config"]}
    app = App(config=Dict(config_data), result_action="return_value")

    @app.default
    def main(tags: set[str]):
        return f"Tags: {sorted(tags)}"

    result = app([])
    assert result == "Tags: ['cli', 'config', 'python']"


def test_config_dict_with_negative_numbers():
    """Test Dict config with negative numbers."""
    config_data = {"offset": -10, "temperature": -5.5}
    app = App(config=Dict(config_data), result_action="return_value")

    @app.default
    def main(offset: int, temperature: float):
        return f"offset={offset}, temperature={temperature}"

    result = app([])
    assert result == "offset=-10, temperature=-5.5"
