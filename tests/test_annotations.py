import inspect
from collections import namedtuple
from typing import Annotated, Any, Literal, Optional, Union

import pytest

from cyclopts.annotations import contains_hint, get_hint_name, resolve


def test_resolve_annotated():
    type_ = Annotated[Literal["foo", "bar"], "fizz"]
    res = resolve(type_)
    assert res == Literal["foo", "bar"]


def test_resolve_empty():
    res = resolve(inspect.Parameter.empty)
    assert res is str


def test_get_hint_name_string():
    assert get_hint_name("str") == "str"


def test_get_hint_name_any():
    assert get_hint_name(Any) == "Any"


def test_get_hint_name_union():
    assert get_hint_name(Union[int, str]) == "int|str"


def test_get_hint_name_class_with_name():
    class TestClass:
        pass

    assert get_hint_name(TestClass) == "TestClass"


def test_get_hint_name_typing_with_name():
    assert get_hint_name(list) == "list"


def test_get_hint_name_generic_type():
    assert get_hint_name(list[int]) == "list[int]"


def test_get_hint_name_nested_generic_type():
    assert get_hint_name(dict[str, list[int]]) == "dict[str, list[int]]"


def test_get_hint_name_optional_type():
    assert get_hint_name(Optional[int]) == "int|None"


def test_get_hint_name_namedtuple():
    TestTuple = namedtuple("TestTuple", ["field1", "field2"])
    assert get_hint_name(TestTuple) == "TestTuple"


def test_get_hint_name_complex_union():
    complex_type = Union[int, str, list[dict[str, Any]]]
    assert get_hint_name(complex_type) == "int|str|list[dict[str, Any]]"


def test_get_hint_name_fallback_str():
    class NoNameClass:
        def __str__(self):
            return "NoNameClass"

    assert get_hint_name(NoNameClass()) == "NoNameClass"


class CustomStr(str):
    """Dummy subclass of ``str``."""


@pytest.mark.parametrize(
    "hint,target_type,expected",
    [
        (str, str, True),
        (CustomStr, str, True),
        (Union[int, str], str, True),
        (Annotated[int | str, 1], str, True),
        (Annotated[Annotated[int, 1] | Annotated[str, 1], 1], str, True),
        (int, str, False),
    ],
)
def test_contains_hint(hint, target_type, expected):
    assert contains_hint(hint, target_type) == expected
