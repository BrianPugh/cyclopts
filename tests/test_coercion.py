import inspect
import sys
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional, Set, Tuple, Union

import pytest

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated

from cyclopts import CoercionError
from cyclopts.coercion import coerce, resolve, token_count


def _assert_tuple(expected, actual):
    assert type(actual) == tuple
    assert len(expected) == len(actual)
    for e, a in zip(expected, actual):
        assert type(e) == type(a)
        assert e == a


def test_token_count_tuple_basic():
    assert (3, False) == token_count(Tuple[int, int, int])


def test_token_count_tuple_no_inner_type():
    assert (1, True) == token_count(Tuple)
    assert (1, True) == token_count(tuple)


def test_token_count_tuple_nested():
    assert (4, False) == token_count(Tuple[Tuple[int, int], int, int])


def test_token_count_tuple_ellipsis():
    assert (1, True) == token_count(Tuple[int, ...])


def test_token_count_tuple_ellipsis_nested():
    assert (2, True) == token_count(Tuple[Tuple[int, int], ...])


def test_token_union():
    assert (1, False) == token_count(Union[None, int])


def test_token_count_standard():
    assert (1, False) == token_count(int)


def test_token_count_bool():
    assert (0, False) == token_count(bool)


def test_token_count_list():
    assert (1, True) == token_count(List[int])


def test_token_count_list_generic():
    assert (1, True) == token_count(list)


@pytest.mark.skipif(sys.version_info < (3, 9), reason="Native Typing")
def test_token_count_list_direct():
    assert (1, True) == token_count(list[int])  # pyright: ignore


def test_token_count_list_of_tuple():
    assert (3, True) == token_count(List[Tuple[int, int, int]])


def test_token_count_list_of_tuple_nested():
    assert (4, True) == token_count(List[Tuple[Tuple[int, int], int, int]])


def test_token_count_iterable():
    assert (1, True) == token_count(Iterable[int])
    assert (2, True) == token_count(Iterable[Tuple[int, int]])


def test_coerce_bool():
    assert True is coerce(bool, "true")
    assert False is coerce(bool, "false")


def test_coerce_int():
    assert 123 == coerce(int, "123")


def test_coerce_annotated_int():
    assert [123, 456] == coerce(Annotated[int, "foo"], "123", "456")
    assert [123, 456] == coerce(Annotated[List[int], "foo"], "123", "456")


def test_coerce_optional_annotated_int():
    assert [123, 456] == coerce(Optional[Annotated[int, "foo"]], "123", "456")
    assert [123, 456] == coerce(Optional[Annotated[List[int], "foo"]], "123", "456")


def test_coerce_annotated_union_str_secondary_choice():
    assert 123 == coerce(Union[None, int, str], "123")
    assert "foo" == coerce(Union[None, int, str], "foo")

    with pytest.raises(CoercionError):
        coerce(Union[None, int, float], "invalid-choice")


def test_coerce_annotated_nested_union_str_secondary_choice():
    assert 123 == coerce(Union[None, Union[int, str]], "123")
    assert "foo" == coerce(Union[None, Union[int, str]], "foo")


def test_coerce_annotated_union_int():
    assert 123 == coerce(Annotated[Union[None, int, float], "foo"], "123")
    assert [123, 456] == coerce(Annotated[int, "foo"], "123", "456")
    assert [123, 456] == coerce(Annotated[Union[None, int, float], "foo"], "123", "456")


def test_coerce_enum():
    class SoftwareEnvironment(Enum):
        DEV = auto()
        STAGING = auto()
        PROD = auto()
        _PROD_OLD = auto()

    assert SoftwareEnvironment.STAGING == coerce(SoftwareEnvironment, "staging")
    assert SoftwareEnvironment._PROD_OLD == coerce(SoftwareEnvironment, "prod_old")
    assert SoftwareEnvironment._PROD_OLD == coerce(SoftwareEnvironment, "prod-old")

    with pytest.raises(CoercionError):
        coerce(SoftwareEnvironment, "invalid-choice")


def test_coerce_dict_error():
    with pytest.raises(TypeError):
        coerce(dict, "this-doesnt-matter")

    with pytest.raises(TypeError):
        coerce(Dict, "this-doesnt-matter")

    with pytest.raises(TypeError):
        coerce(Annotated[dict, "foo"], "this-doesnt-matter")


def test_coerce_tuple_basic_single():
    _assert_tuple((1,), coerce(Tuple[int], "1"))


def test_coerce_tuple_basic_double():
    _assert_tuple((1, 2.0), coerce(Tuple[int, Union[None, float, int]], "1", "2"))


def test_coerce_tuple_no_inner_types():
    _assert_tuple(("1", "2"), coerce(Tuple, "1", "2"))


def test_coerce_tuple_nested():
    _assert_tuple(
        (1, (2.0, "foo")),
        coerce(Tuple[int, Tuple[float, Union[None, str, int]]], "1", "2", "foo"),
    )


def test_coerce_tuple_len_mismatch():
    with pytest.raises(ValueError):
        coerce(Tuple[int, int], "1")


def test_coerce_list():
    assert [123, 456] == coerce(int, "123", "456")
    assert [123, 456] == coerce(List[int], "123", "456")
    assert [123] == coerce(List[int], "123")


def test_coerce_bare_list():
    # Implicit element type: str
    assert ["123", "456"] == coerce(list, "123", "456")


def test_coerce_iterable():
    assert [123, 456] == coerce(Iterable[int], "123", "456")
    assert [123] == coerce(Iterable[int], "123")


def test_coerce_set():
    assert {"123", "456"} == coerce(Set[str], "123", "456")
    assert {123, 456} == coerce(Set[Union[int, str]], "123", "456")


def test_coerce_literal():
    assert "foo" == coerce(Literal["foo", "bar", 3], "foo")
    assert "bar" == coerce(Literal["foo", "bar", 3], "bar")
    assert 3 == coerce(Literal["foo", "bar", 3], "3")

    with pytest.raises(CoercionError):
        coerce(Literal["foo", "bar", 3], "invalid-choice")


def test_coerce_path():
    assert Path("foo") == coerce(Path, "foo")


def test_coerce_any():
    assert "foo" == coerce(Any, "foo")


def test_coerce_bytes():
    assert b"foo" == coerce(bytes, "foo")
    assert [b"foo", b"bar"] == coerce(bytes, "foo", "bar")


def test_coerce_bytearray():
    res = coerce(bytearray, "foo")
    assert isinstance(res, bytearray)
    assert bytearray(b"foo") == res

    assert [bytearray(b"foo"), bytearray(b"bar")] == coerce(bytearray, "foo", "bar")


def test_coerce_empty():
    assert "foo" == coerce(inspect.Parameter.empty, "foo")


def test_resolve_annotated():
    type_ = Annotated[Literal["foo", "bar"], "fizz"]
    res = resolve(type_)
    assert res == Literal["foo", "bar"]


def test_resolve_empty():
    res = resolve(inspect.Parameter.empty)
    assert res == str
