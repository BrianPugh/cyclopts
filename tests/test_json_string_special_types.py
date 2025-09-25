"""Test JSON parsing behavior with special string types.

This module tests JSON parsing with:
- String subclasses (CustomStr)
- NewType wrapping str
- Union types containing str
- Optional[str] (which is Union[str, None])

Key principle: If a type can accept str, then a JSON string is already
a valid value for that type, so JSON parsing should be disabled.
"""

from dataclasses import dataclass
from typing import NewType, Optional, Union

import pytest


class CustomStr(str):
    """A custom string subclass."""


MyStr = NewType("MyStr", str)


@dataclass
class User:
    name: str
    age: int


@dataclass
class UserWithCustomStr:
    name: CustomStr
    age: int


@dataclass
class UserWithNewType:
    name: MyStr
    age: int


@dataclass
class UserWithUnion:
    name: Union[str, int]
    age: int


# =============================================================================
# Tests for string subclasses and NewType
# =============================================================================


@pytest.mark.parametrize(
    "type_hint,expected_value",
    [
        (CustomStr, CustomStr('{"name": "Alice"}')),
        (MyStr, MyStr('{"name": "Alice"}')),
    ],
    ids=["CustomStr", "NewType"],
)
def test_json_not_parsed_for_str_like_types(app, assert_parse_args, type_hint, expected_value):
    """JSON should NOT be parsed for string subclasses or NewType(str)."""

    @app.default
    def main(value: type_hint):  # type: ignore
        pass

    assert_parse_args(
        main,
        ["--value", '{"name": "Alice"}'],
        expected_value,
    )


@pytest.mark.parametrize(
    "type_hint,wrapper",
    [
        (list[CustomStr], CustomStr),
        (list[MyStr], MyStr),
    ],
    ids=["list[CustomStr]", "list[NewType]"],
)
def test_json_list_not_parsed_for_str_like_types(app, assert_parse_args, type_hint, wrapper):
    """JSON arrays should NOT be parsed for list of string-like types."""

    @app.default
    def main(values: type_hint):  # type: ignore
        pass

    assert_parse_args(
        main,
        ["--values", '["hello", "world"]'],
        [wrapper('["hello", "world"]')],
    )


# =============================================================================
# Tests for Union types containing str
# =============================================================================


@pytest.mark.parametrize(
    "type_hint,json_input,expected",
    [
        # Union[str, int] - JSON not parsed
        (list[Union[str, int]], "[1, 2, 3]", ["[1, 2, 3]"]),
        (list[Union[str, int]], '["hello", "world"]', ['["hello", "world"]']),
        # Optional[str] - JSON not parsed
        (list[Optional[str]], '["hello", null, "world"]', ['["hello", null, "world"]']),
        # Optional[int] - JSON IS parsed (no str in union)
        (list[Optional[int]], "[1, null, 3]", [1, None, 3]),
    ],
    ids=["Union[str,int]-ints", "Union[str,int]-strings", "Optional[str]", "Optional[int]"],
)
def test_json_list_parsing_with_unions(app, assert_parse_args, type_hint, json_input, expected):
    """Test JSON array parsing behavior with Union types.

    When Union contains str, JSON parsing is disabled since the JSON string
    is a valid str value.
    """

    @app.default
    def main(values: type_hint):  # type: ignore
        pass

    assert_parse_args(
        main,
        ["--values", json_input],
        expected,
    )


def test_union_with_str_no_json_parsing(app, assert_parse_args):
    """JSON should NOT be parsed when type is Union[str, ...]."""

    @app.default
    def main(value: Union[str, int]):
        pass

    assert_parse_args(
        main,
        ["--value", '{"name": "Alice"}'],
        '{"name": "Alice"}',
    )


# =============================================================================
# Tests for dataclasses with special string fields
# =============================================================================


@pytest.mark.parametrize(
    "dataclass_type,expected",
    [
        (UserWithCustomStr, UserWithCustomStr(CustomStr("Alice"), 30)),
        (UserWithNewType, UserWithNewType(MyStr("Alice"), 30)),
    ],
    ids=["CustomStr-field", "NewType-field"],
)
def test_json_dataclass_with_special_str_fields(app, assert_parse_args, dataclass_type, expected):
    """JSON object parsing works for dataclasses with special string field types."""

    @app.default
    def main(user: dataclass_type):  # type: ignore
        pass

    assert_parse_args(
        main,
        ["--user", '{"name": "Alice", "age": 30}'],
        expected,
    )


def test_json_dataclass_with_union_field(app, assert_parse_args):
    """JSON object parsing works for dataclasses with Union fields."""

    @app.default
    def main(user: UserWithUnion):
        pass

    # String value in union field
    assert_parse_args(
        main,
        ["--user", '{"name": "Alice", "age": 30}'],
        UserWithUnion("Alice", 30),
    )

    # Integer value in union field - gets converted to string since str is first in Union
    assert_parse_args(
        main,
        ["--user", '{"name": 123, "age": 30}'],
        UserWithUnion("123", 30),  # 123 becomes "123" due to Union coercion order
    )


@pytest.mark.parametrize(
    "dataclass_type,expected_type,name_wrapper",
    [
        (UserWithCustomStr, UserWithCustomStr, CustomStr),
        (UserWithNewType, UserWithNewType, MyStr),
    ],
    ids=["list[CustomStr-dataclass]", "list[NewType-dataclass]"],
)
def test_json_list_of_dataclass_with_special_fields(
    app, assert_parse_args, dataclass_type, expected_type, name_wrapper
):
    """JSON array parsing works for list of dataclasses with special string fields."""

    @app.default
    def main(users: list[dataclass_type]):  # type: ignore
        pass

    assert_parse_args(
        main,
        ["--users", '[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 40}]'],
        [expected_type(name_wrapper("Alice"), 30), expected_type(name_wrapper("Bob"), 40)],
    )


@pytest.mark.parametrize(
    "type_hint,cmd_args,expected",
    [
        # Regular dataclass - JSON IS parsed
        (
            list[User],
            ["--values", '{"name": "Alice", "age": 30}', "--values", '{"name": "Bob", "age": 40}'],
            [User("Alice", 30), User("Bob", 40)],
        ),
        # CustomStr - JSON NOT parsed
        (
            list[CustomStr],
            ["--values", '{"name": "Alice"}', "--values", '{"name": "Bob"}'],
            [CustomStr('{"name": "Alice"}'), CustomStr('{"name": "Bob"}')],
        ),
    ],
    ids=["list[Dataclass]-parses", "list[CustomStr]-no-parse"],
)
def test_multiple_json_objects(app, assert_parse_args, type_hint, cmd_args, expected):
    """Test multiple individual JSON objects for lists."""

    @app.default
    def main(values: type_hint):  # type: ignore
        pass

    assert_parse_args(main, cmd_args, expected)
