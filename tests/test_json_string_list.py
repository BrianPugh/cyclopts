from dataclasses import dataclass
from typing import Annotated, Iterable, Optional, Sequence

import pytest

from cyclopts import CycloptsError, Parameter

LIST_STR_LIKE_TYPES = [list, list[str], Sequence, Sequence[str], Iterable, Iterable[str]]


@dataclass
class User:
    name: str
    age: int


@pytest.mark.parametrize(
    "cmd_str",
    [
        "--values=[1,2,3]",
        "--values [1,2,3]",
        "--values [1,2] --values [3]",
        "--values [1] --values '[2, 3]'",
        "--values 1 --values [2,3]",
        "--values [1] --values [2] --values [3]",
    ],
)
@pytest.mark.parametrize("json_list", [None, True])
def test_json_list_cli_str(app, assert_parse_args, cmd_str, json_list):
    @app.default
    def main(values: Annotated[list[int], Parameter(json_list=json_list)]):
        pass

    assert_parse_args(main, cmd_str, [1, 2, 3])


@pytest.mark.parametrize("annotation", LIST_STR_LIKE_TYPES)
def test_json_list_str_none(app, assert_parse_args, annotation):
    """A ``list`` or ``list[str]`` annotation should **not** be set-able via json-string by default.

    May change in v4.
    """

    @app.default
    def main(values: annotation):  # pyright: ignore
        pass

    assert_parse_args(main, ['["foo", "bar"]'], ['["foo", "bar"]'])


def test_json_list_optional_int(app, assert_parse_args):
    @app.default
    def main(values: list[Optional[int]]):  # pyright: ignore
        pass

    assert_parse_args(main, ["[1, null, 2]"], [1, None, 2])


@pytest.mark.parametrize("annotation", LIST_STR_LIKE_TYPES)
def test_json_list_str_cli_str_true(app, assert_parse_args, annotation):
    @app.default
    def main(values: Annotated[annotation, Parameter(json_list=True)]):  # pyright: ignore
        pass

    assert_parse_args(main, ['["foo", "bar"]'], ["foo", "bar"])


@pytest.mark.parametrize("annotation", [list, list[str]])
def test_json_list_str_cli_str_false(app, assert_parse_args, annotation):
    @app.default
    def main(values: Annotated[annotation, Parameter(json_list=False)]):  # pyright: ignore
        pass

    assert_parse_args(main, ['["foo", "bar"]'], ['["foo", "bar"]'])


@pytest.mark.parametrize(
    "env_str",
    [
        "[1,2,3]",
        "[1, 2, 3]",
    ],
)
@pytest.mark.parametrize("json_list", [None, True])
def test_json_list_env_str(app, assert_parse_args, env_str, monkeypatch, json_list):
    monkeypatch.setenv("VALUES", env_str)

    @app.default
    def main(values: Annotated[list[int], Parameter(env_var="VALUES", json_list=json_list)]):
        pass

    assert_parse_args(main, "", [1, 2, 3])


def test_json_list_of_dataclass_array(app, assert_parse_args):
    """Test JSON array input for list of dataclasses."""

    @app.default
    def main(values: list[User]):
        pass

    assert_parse_args(
        main,
        ["--values", '[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 40}]'],
        [User("Alice", 30), User("Bob", 40)],
    )


def test_json_list_of_dataclass_individual(app, assert_parse_args):
    """Test multiple individual JSON objects for list of dataclasses."""

    @app.default
    def main(values: list[User]):
        pass

    assert_parse_args(
        main,
        ["--values", '{"name": "Alice", "age": 30}', "--values", '{"name": "Bob", "age": 40}'],
        [User("Alice", 30), User("Bob", 40)],
    )


def test_json_list_of_dataclass_mixed(app, assert_parse_args):
    """Test mixing individual JSON objects with JSON arrays."""

    @app.default
    def main(values: list[User]):
        pass

    assert_parse_args(
        main,
        [
            "--values",
            '{"name": "Alice", "age": 30}',
            "--values",
            '[{"name": "Bob", "age": 40}, {"name": "Charlie", "age": 50}]',
            "--values",
            '{"name": "David", "age": 60}',
        ],
        [User("Alice", 30), User("Bob", 40), User("Charlie", 50), User("David", 60)],
    )


def test_json_list_of_dataclass_empty_array(app, assert_parse_args):
    """Test empty JSON array for list of dataclasses."""

    @app.default
    def main(values: Optional[list[User]] = None):  # pyright: ignore
        pass

    assert_parse_args(main, ["--values", "[]"], [])


def test_json_list_of_dataclass_single_element_array(app, assert_parse_args):
    """Test single-element JSON array."""

    @app.default
    def main(values: list[User]):
        pass

    assert_parse_args(
        main,
        ["--values", '[{"name": "Alice", "age": 30}]'],
        [User("Alice", 30)],
    )


# =============================================================================
# Error Cases
# =============================================================================


def test_json_list_malformed_json_array(app):
    """Test that malformed JSON array raises appropriate error."""

    @app.default
    def main(values: list[User]):
        pass

    # Missing closing bracket
    with pytest.raises(CycloptsError):
        app(["--values", '[{"name": "Alice", "age": 30}'], exit_on_error=False)


def test_json_list_malformed_json_object(app):
    """Test that malformed JSON object raises appropriate error."""

    @app.default
    def main(values: list[User]):
        pass

    # Missing closing brace
    with pytest.raises(CycloptsError):
        app(["--values", '{"name": "Alice", "age": 30'], exit_on_error=False)


def test_json_list_invalid_json_syntax(app):
    """Test that invalid JSON syntax raises appropriate error with helpful message."""

    @app.default
    def main(values: list[User]):
        pass

    # Invalid JSON - single quotes instead of double quotes
    with pytest.raises(CycloptsError) as exc_info:
        app(["--values", "{'name': 'Alice', 'age': 30}"], exit_on_error=False)

    # Should show it's invalid JSON with context
    error_str = str(exc_info.value)
    assert "Invalid JSON for User" in error_str
    assert "'" in error_str  # Should show the problematic quote
    assert "^" in error_str  # Should have error marker
    assert "Hint: JSON requires double quotes" in error_str  # Should provide hint


def test_json_list_python_style_booleans(app):
    """Test that Python-style booleans (True/False) in JSON raise appropriate error.

    JSON requires lowercase 'true' and 'false', not Python's 'True' and 'False'.
    This test ensures we properly handle this common mistake with clear, specific error messages.
    """

    @dataclass
    class Item:
        enabled: bool
        disabled: bool
        name: str

    @app.default
    def main(values: list[Item]):
        pass

    # Test Python-style True - should fail with specific message
    with pytest.raises(CycloptsError) as exc_info:
        app(["--values", '{"enabled": True, "disabled": false, "name": "test"}'], exit_on_error=False)

    error_str = str(exc_info.value)
    assert "Invalid JSON for Item" in error_str
    assert "True" in error_str  # Should show the problematic part
    assert "^" in error_str  # Should have error marker
    assert "Hint: Use lowercase 'true' instead of Python's True" in error_str

    # Test Python-style False - should fail with specific message
    with pytest.raises(CycloptsError) as exc_info:
        app(["--values", '{"enabled": true, "disabled": False, "name": "test"}'], exit_on_error=False)

    error_str = str(exc_info.value)
    assert "Invalid JSON for Item" in error_str
    assert "False" in error_str  # Should show the problematic part
    assert "^" in error_str  # Should have error marker
    assert "Hint: Use lowercase 'false' instead of Python's False" in error_str

    # Valid JSON with lowercase booleans should work correctly
    _, bound, _ = app.parse_args(["--values", '{"enabled": true, "disabled": false, "name": "test"}'])
    assert bound.arguments["values"] == [Item(enabled=True, disabled=False, name="test")]


def test_json_list_python_none(app):
    """Test that Python's None in JSON raises appropriate error with specific hint."""

    @dataclass
    class Config:
        name: str
        value: Optional[int]

    @app.default
    def main(values: list[Config]):
        pass

    # Python-style None should fail (invalid JSON)
    with pytest.raises(CycloptsError) as exc_info:
        app(["--values", '{"name": "test", "value": None}'], exit_on_error=False)

    # The error message should provide specific hint for None
    error_str = str(exc_info.value)
    assert "Invalid JSON for Config" in error_str
    assert "None" in error_str  # Should show the problematic part
    assert "^" in error_str  # Should have error marker
    assert "Hint: Use 'null' instead of Python's None" in error_str

    # Valid JSON with null should work correctly
    _, bound, _ = app.parse_args(["--values", '{"name": "test", "value": null}'])
    assert bound.arguments["values"] == [Config(name="test", value=None)]


def test_json_list_type_mismatch_in_field(app):
    """Test that type mismatches in JSON fields now raise errors consistently.

    After the fix, both single dataclasses and lists of dataclasses
    perform type conversion and validation on JSON fields.
    """

    @app.default
    def main(values: list[User]):
        pass

    # Age should be int, "thirty" can't be converted
    with pytest.raises(CycloptsError):
        app(["--values", '{"name": "Alice", "age": "thirty"}'], exit_on_error=False)


def test_json_list_type_conversion_success(app, assert_parse_args):
    """Test that valid type conversions work for JSON fields in lists.

    String "25" should be converted to int 25.
    """

    @app.default
    def main(values: list[User]):
        pass

    # Age "25" should be converted to int 25
    assert_parse_args(
        main,
        ["--values", '{"name": "Alice", "age": "25"}'],
        [User("Alice", 25)],  # age is converted to int
    )


def test_json_list_missing_required_field(app):
    """Test that missing required fields in JSON raise appropriate errors."""

    @app.default
    def main(values: list[User]):
        pass

    # Missing required 'age' field
    with pytest.raises(CycloptsError):
        app(["--values", '{"name": "Alice"}'], exit_on_error=False)


def test_json_list_extra_field_ignored(app, assert_parse_args):
    """Test that extra fields in JSON are silently ignored.

    The implementation only processes fields that exist in the dataclass,
    so extra fields are ignored rather than causing an error.
    """

    @app.default
    def main(values: list[User]):
        pass

    # Extra field 'city' is ignored
    assert_parse_args(
        main,
        ["--values", '{"name": "Alice", "age": 30, "city": "NYC"}'],
        [User("Alice", 30)],
    )


def test_json_list_null_value_in_array(app):
    """Test that null values in JSON array are handled appropriately."""

    @app.default
    def main(values: list[User]):
        pass

    # Null is not a valid User object
    with pytest.raises(CycloptsError):
        app(["--values", '[{"name": "Alice", "age": 30}, null]'], exit_on_error=False)


def test_json_list_wrong_type_in_array(app):
    """Test that wrong types in JSON array are caught."""

    @app.default
    def main(values: list[User]):
        pass

    # String instead of object
    with pytest.raises(CycloptsError):
        app(["--values", '["Alice", "Bob"]'], exit_on_error=False)


def test_json_list_nested_array_produces_empty_list(app, assert_parse_args):
    """Test that nested arrays result in an empty list.

    The current implementation skips non-dict elements in JSON arrays,
    so a nested array (which contains a list, not a dict) results in
    no valid dataclass objects being created.
    """

    @app.default
    def main(values: list[User]):
        pass

    # Nested array structure results in empty list
    assert_parse_args(
        main,
        ["--values", '[[{"name": "Alice", "age": 30}]]'],
        [],
    )


# =============================================================================
# Single Dataclass JSON Error Cases
# =============================================================================


def test_json_single_dataclass_malformed(app):
    """Test that malformed JSON for single dataclass raises error."""

    @app.default
    def main(user: User):
        pass

    # Missing closing brace
    with pytest.raises(CycloptsError):
        app(["--user", '{"name": "Alice", "age": 30'], exit_on_error=False)


def test_json_single_dataclass_type_mismatch(app):
    """Test that type mismatches in single dataclass JSON raise errors.

    Cyclopts attempts to convert dataclass field values to their proper types
    after JSON parsing. If a value can't be converted (e.g., "thirty" to int),
    an error is raised.
    """

    @app.default
    def main(user: User):
        pass

    # Age should be int, "thirty" can't be converted
    with pytest.raises(CycloptsError):
        app(["--user", '{"name": "Alice", "age": "thirty"}'], exit_on_error=False)


def test_json_single_dataclass_type_conversion_success(app, assert_parse_args):
    """Test that valid type conversions work for JSON fields in single dataclass.

    String "25" should be converted to int 25, matching list behavior.
    """

    @app.default
    def main(user: User):
        pass

    # Age "25" should be converted to int 25
    assert_parse_args(
        main,
        ["--user", '{"name": "Bob", "age": "25"}'],
        User("Bob", 25),  # age is converted to int
    )


def test_json_single_dataclass_missing_field(app):
    """Test that missing required fields in single dataclass JSON raise errors."""

    @app.default
    def main(user: User):
        pass

    # Missing required 'age' field
    with pytest.raises(CycloptsError):
        app(["--user", '{"name": "Alice"}'], exit_on_error=False)


# =============================================================================
# Edge Cases for Type Conversion Consistency
# =============================================================================


def test_json_list_with_float_to_int_conversion(app, assert_parse_args):
    """Test that float values in JSON are handled properly for int fields."""

    @app.default
    def main(values: list[User]):
        pass

    # 30.0 should work (converts to 30)
    assert_parse_args(
        main,
        ["--values", '{"name": "Alice", "age": 30.0}'],
        [User("Alice", 30)],
    )


def test_json_list_with_bool_field(app, assert_parse_args):
    """Test dataclass with boolean field conversion."""

    @dataclass
    class Config:
        enabled: bool
        count: int

    @app.default
    def main(configs: list[Config]):
        pass

    # Test various boolean representations
    assert_parse_args(
        main,
        ["--configs", '[{"enabled": true, "count": 5}, {"enabled": false, "count": 10}]'],
        [Config(True, 5), Config(False, 10)],
    )


def test_json_mixed_list_and_single_objects(app, assert_parse_args):
    """Test that mixed JSON arrays and objects work correctly with type conversion."""

    @app.default
    def main(values: list[User]):
        pass

    # Mix of array and individual objects with string ages that need conversion
    assert_parse_args(
        main,
        [
            "--values",
            '[{"name": "Alice", "age": "30"}]',
            "--values",
            '{"name": "Bob", "age": "25"}',
        ],
        [User("Alice", 30), User("Bob", 25)],
    )
