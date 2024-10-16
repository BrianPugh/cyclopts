import inspect
import sys
from enum import Enum, auto
from pathlib import Path
from typing import Annotated, Any, Iterable, List, Literal, Optional, Sequence, Set, Tuple, Union
from unittest.mock import Mock

import pytest

from cyclopts import CoercionError, Token
from cyclopts._convert import convert, token_count


def _assert_tuple(expected, actual):
    assert type(actual) is tuple
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


def test_token_count_sequence():
    assert (1, True) == token_count(Sequence[int])
    assert (2, True) == token_count(Sequence[Tuple[int, int]])


def test_token_count_list_generic():
    assert (1, True) == token_count(list)


def test_token_count_list_direct():
    assert (1, True) == token_count(list[int])  # pyright: ignore


def test_token_count_list_of_tuple():
    assert (3, True) == token_count(List[Tuple[int, int, int]])


def test_token_count_list_of_tuple_nested():
    assert (4, True) == token_count(List[Tuple[Tuple[int, int], int, int]])


def test_token_count_iterable():
    assert (1, True) == token_count(Iterable[int])
    assert (2, True) == token_count(Iterable[Tuple[int, int]])


def test_token_count_union():
    assert (1, False) == token_count(Union[int, str, float])


def test_token_count_union_error():
    with pytest.raises(ValueError):
        assert (1, False) == token_count(Union[int, Tuple[int, int]])


def test_coerce_no_tokens():
    with pytest.raises(ValueError):
        convert(int, [])


def test_coerce_bool():
    assert True is convert(bool, ["true"])
    assert False is convert(bool, ["false"])


def test_coerce_error():
    with pytest.raises(CoercionError):
        convert(bool, ["foo"])


def test_coerce_int():
    assert 123 == convert(int, ["123"])


def test_coerce_annotated_int():
    assert [123, 456] == convert(Annotated[int, "foo"], ["123", "456"])
    assert [123, 456] == convert(Annotated[List[int], "foo"], ["123", "456"])


def test_coerce_optional_annotated_int():
    assert [123, 456] == convert(Optional[Annotated[int, "foo"]], ["123", "456"])
    assert [123, 456] == convert(Optional[Annotated[List[int], "foo"]], ["123", "456"])


def test_coerce_annotated_union_str_secondary_choice():
    assert 123 == convert(Union[None, int, str], ["123"])
    assert "foo" == convert(Union[None, int, str], ["foo"])

    with pytest.raises(CoercionError):
        convert(Union[None, int, float], ["invalid-choice"])


def test_coerce_annotated_nested_union_str_secondary_choice():
    assert 123 == convert(Union[None, Union[int, str]], ["123"])
    assert "foo" == convert(Union[None, Union[int, str]], ["foo"])


def test_coerce_annotated_union_int():
    assert 123 == convert(Annotated[Union[None, int, float], "foo"], ["123"])
    assert [123, 456] == convert(Annotated[int, "foo"], ["123", "456"])
    assert [123, 456] == convert(Annotated[Union[None, int, float], "foo"], ["123", "456"])


def test_coerce_enum():
    class SoftwareEnvironment(Enum):
        DEV = auto()
        STAGING = auto()
        PROD = auto()
        _PROD_OLD = auto()

    # tests case-insensitivity
    assert SoftwareEnvironment.STAGING == convert(SoftwareEnvironment, ["staging"])

    # tests underscore/hyphen support
    assert SoftwareEnvironment._PROD_OLD == convert(SoftwareEnvironment, ["prod_old"])
    assert SoftwareEnvironment._PROD_OLD == convert(SoftwareEnvironment, ["prod-old"])

    with pytest.raises(CoercionError):
        convert(SoftwareEnvironment, ["invalid-choice"])


def test_coerce_tuple_basic_single():
    _assert_tuple((1,), convert(Tuple[int], ["1"]))


def test_coerce_tuple_str_single():
    _assert_tuple(("foo",), convert(Tuple[str], ["foo"]))


def test_coerce_tuple_basic_double():
    _assert_tuple((1, 2.0), convert(Tuple[int, Union[None, float, int]], ["1", "2"]))


def test_coerce_tuple_typing_no_inner_types():
    _assert_tuple(("1", "2"), convert(Tuple, ["1", "2"]))


def test_coerce_tuple_builtin_no_inner_types():
    _assert_tuple(("1", "2"), convert(tuple, ["1", "2"]))


def test_coerce_tuple_nested():
    _assert_tuple(
        (1, (2.0, "foo")),
        convert(Tuple[int, Tuple[float, Union[None, str, int]]], ["1", "2", "foo"]),
    )


def test_coerce_tuple_len_mismatch_underflow():
    with pytest.raises(CoercionError):
        convert(Tuple[int, int], ["1"])


def test_coerce_tuple_len_mismatch_overflow():
    with pytest.raises(CoercionError):
        convert(Tuple[int, int], ["1", "2", "3"])


@pytest.mark.skipif(sys.version_info < (3, 11), reason="Typing")
def test_coerce_tuple_ellipsis_too_many_inner_types():
    with pytest.raises(ValueError):  # This is a ValueError because it happens prior to runtime.
        # Only 1 inner type annotation allowed
        convert(Tuple[int, int, ...], ["1", "2"])  # pyright: ignore


def test_coerce_tuple_ellipsis_non_divisible():
    with pytest.raises(CoercionError):
        convert(Tuple[Tuple[int, int], ...], ["1", "2", "3"])


def test_coerce_list():
    assert [123, 456] == convert(int, ["123", "456"])
    assert [123, 456] == convert(List[int], ["123", "456"])
    assert [123] == convert(List[int], ["123"])


def test_coerce_list_of_tuple_str_single_1():
    res = convert(List[Tuple[str]], ["foo"])
    assert isinstance(res, list)
    assert len(res) == 1
    _assert_tuple(("foo",), res[0])


def test_coerce_list_of_tuple_str_single_2():
    res = convert(List[Tuple[str]], ["foo", "bar"])
    assert isinstance(res, list)
    assert len(res) == 2
    _assert_tuple(("foo",), res[0])
    _assert_tuple(("bar",), res[1])


def test_coerce_bare_list():
    # Implicit element type: str
    assert ["123", "456"] == convert(list, ["123", "456"])


def test_coerce_iterable():
    assert [123, 456] == convert(Iterable[int], ["123", "456"])
    assert [123] == convert(Iterable[int], ["123"])


def test_coerce_set():
    assert {"123", "456"} == convert(Set[str], ["123", "456"])
    assert {123, 456} == convert(Set[Union[int, str]], ["123", "456"])


def test_coerce_frozenset():
    assert frozenset({"123", "456"}) == convert(frozenset[str], ["123", "456"])
    assert frozenset({123, 456}) == convert(frozenset[Union[int, str]], ["123", "456"])


def test_coerce_literal():
    assert "foo" == convert(Literal["foo", "bar", 3], ["foo"])
    assert "bar" == convert(Literal["foo", "bar", 3], ["bar"])
    assert 3 == convert(Literal["foo", "bar", 3], ["3"])


def assert_convert_coercion_error(*args, msg, **kwargs):
    mock_argument = Mock()
    mock_argument.name = "mocked_argument_name"
    with pytest.raises(CoercionError) as e:
        try:
            convert(*args, **kwargs)
        except CoercionError as coercion_error:
            coercion_error.argument = mock_argument
            raise
    exception_message = str(e.value).split("\n", 1)[1]
    assert exception_message == msg


def test_coerce_literal_invalid_choice():
    assert_convert_coercion_error(
        Literal["foo", "bar", 3],
        ["invalid-choice"],
        msg="""Invalid value for "mocked_argument_name": unable to convert "invalid-choice" into one of {'foo', 'bar', 3}.""",
    )


def test_coerce_literal_invalid_choice_keyword():
    assert_convert_coercion_error(
        Literal["foo", "bar", 3],
        [Token(keyword="--MY_KEYWORD", value="invalid-choice")],
        msg="""Invalid value for "--MY_KEYWORD": unable to convert "invalid-choice" into one of {'foo', 'bar', 3}.""",
    )


def test_coerce_literal_invalid_choice_non_cli_token():
    assert_convert_coercion_error(
        Literal["foo", "bar", 3],
        [Token(value="invalid-choice", source="TEST")],
        msg="""Invalid value for "mocked_argument_name" from TEST: unable to convert "invalid-choice" into one of {'foo', 'bar', 3}.""",
    )


def test_coerce_literal_invalid_choice_keyword_non_cli_token():
    assert_convert_coercion_error(
        Literal["foo", "bar", 3],
        [Token(keyword="--MY-KEYWORD", value="invalid-choice", source="TEST")],
        msg="""Invalid value for "--MY-KEYWORD" from TEST: unable to convert "invalid-choice" into one of {'foo', 'bar', 3}.""",
    )


def test_coerce_path():
    assert Path("foo") == convert(Path, ["foo"])


def test_coerce_any():
    assert "foo" == convert(Any, ["foo"])


def test_coerce_bytes():
    assert b"foo" == convert(bytes, ["foo"])
    assert [b"foo", b"bar"] == convert(bytes, ["foo", "bar"])


def test_coerce_bytearray():
    res = convert(bytearray, ["foo"])
    assert isinstance(res, bytearray)
    assert bytearray(b"foo") == res

    assert [bytearray(b"foo"), bytearray(b"bar")] == convert(bytearray, ["foo", "bar"])


def test_coerce_parameter_kind_empty():
    assert "foo" == convert(inspect.Parameter.empty, ["foo"])
