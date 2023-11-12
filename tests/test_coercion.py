import inspect
from enum import Enum, auto
from pathlib import Path
from typing import List, Literal, Optional, Set, Tuple, Union

import pytest
from typing_extensions import Annotated

from cyclopts.coercion import coerce, token_count


def _assert_tuple(expected, actual):
    assert type(actual) == tuple
    assert len(expected) == len(actual)
    for e, a in zip(expected, actual):
        assert type(e) == type(a)
        assert e == a


def test_token_count_tuple():
    assert 3 == token_count(Tuple[int, int, int])


def test_token_union():
    assert 1 == token_count(Union[None, int])


def test_token_count_standard():
    assert 1 == token_count(int)


def test_token_count_bool():
    assert 0 == token_count(bool)


def test_token_count_list():
    assert 1 == token_count(List[int])


def test_coerce_bool():
    assert True is coerce(bool, "true")
    assert False is coerce(bool, "false")


def test_coerce_int():
    assert [123, 456] == coerce(int, "123", "456")
    assert [123, 456] == coerce(List[int], "123", "456")


def test_coerce_annotated_int():
    assert 1 == coerce(int, "1")
    assert [123, 456] == coerce(Annotated[int, "foo"], "123", "456")
    assert [123, 456] == coerce(Annotated[List[int], "foo"], "123", "456")


def test_coerce_enum():
    class SoftwareEnvironment(Enum):
        DEV = auto()
        STAGING = auto()
        PROD = auto()

    assert SoftwareEnvironment.STAGING == coerce(SoftwareEnvironment, "staging")
    _assert_tuple((1, 2.0), coerce(Tuple[int, Union[None, float, int]], "1", "2"))


def test_coerce_set():
    assert {"123", "456"} == coerce(Set[str], "123", "456")
    assert {123, 456} == coerce(Set[Union[int, str]], "123", "456")


def test_coerce_literal():
    assert "foo" == coerce(Literal["foo", "bar", 3], "foo")
    assert "bar" == coerce(Literal["foo", "bar", 3], "bar")
    assert 3 == coerce(Literal["foo", "bar", 3], "3")


def test_coerce_path():
    assert Path("foo") == coerce(Path, "foo")


def test_coerce_bytes():
    assert b"foo" == coerce(bytes, "foo")
    assert [b"foo", b"bar"] == coerce(bytes, "foo", "bar")


def test_coerce_bytearray():
    assert bytearray(b"foo") == coerce(bytes, "foo")
    assert [bytearray(b"foo"), bytearray(b"bar")] == coerce(bytes, "foo", "bar")
