import inspect
import sys
from collections.abc import Iterable, Sequence
from collections.abc import MutableSequence as AbcMutableSequence
from collections.abc import MutableSet as AbcMutableSet
from collections.abc import Set as AbcSet
from datetime import date, datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Annotated, Any, Literal, Optional, Union
from unittest.mock import Mock

import pytest

from cyclopts import CoercionError, Token
from cyclopts._convert import convert, token_count
from cyclopts.utils import default_name_transform


def _assert_tuple(expected, actual):
    assert type(actual) is tuple
    assert len(expected) == len(actual)
    for e, a in zip(expected, actual, strict=False):
        assert type(e) is type(a)
        assert e == a


def test_token_count_tuple_basic():
    assert (3, False) == token_count(tuple[int, int, int])


def test_token_count_tuple_no_inner_type():
    assert (1, True) == token_count(tuple)
    assert (1, True) == token_count(tuple)


def test_token_count_tuple_nested():
    assert (4, False) == token_count(tuple[tuple[int, int], int, int])


def test_token_count_tuple_ellipsis():
    assert (1, True) == token_count(tuple[int, ...])


def test_token_count_tuple_ellipsis_nested():
    assert (2, True) == token_count(tuple[tuple[int, int], ...])


def test_token_union():
    assert (1, False) == token_count(Union[None, int])


def test_token_count_standard():
    assert (1, False) == token_count(int)


def test_token_count_bool():
    assert (0, False) == token_count(bool)


def test_token_count_list():
    assert (1, True) == token_count(list[int])


def test_token_count_sequence():
    assert (1, True) == token_count(Sequence[int])
    assert (2, True) == token_count(Sequence[tuple[int, int]])


def test_token_count_list_generic():
    assert (1, True) == token_count(list)


def test_token_count_list_direct():
    assert (1, True) == token_count(list[int])  # pyright: ignore


def test_token_count_list_of_tuple():
    assert (3, True) == token_count(list[tuple[int, int, int]])


def test_token_count_list_of_tuple_nested():
    assert (4, True) == token_count(list[tuple[tuple[int, int], int, int]])


def test_token_count_iterable():
    assert (1, True) == token_count(Iterable[int])
    assert (2, True) == token_count(Iterable[tuple[int, int]])


def test_token_count_union():
    assert (1, False) == token_count(Union[int, str, float])


def test_token_count_union_error():
    with pytest.raises(ValueError):
        assert (1, False) == token_count(Union[int, tuple[int, int]])


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
    assert [123, 456] == convert(Annotated[list[int], "foo"], ["123", "456"])


def test_coerce_optional_annotated_int():
    assert [123, 456] == convert(Optional[Annotated[int, "foo"]], ["123", "456"])
    assert [123, 456] == convert(Optional[Annotated[list[int], "foo"]], ["123", "456"])


def test_coerce_annotated_union_str_secondary_choice():
    assert 123 == convert(Union[None, int, str], ["123"])
    assert "foo" == convert(Union[None, int, str], ["foo"])

    with pytest.raises(CoercionError):
        convert(Union[None, int, float], ["invalid-choice"])


def test_coerce_annotated_nested_union_str_secondary_choice():
    assert 123 == convert(Union[None, int | str], ["123"])
    assert "foo" == convert(Union[None, int | str], ["foo"])


def test_coerce_annotated_union_int():
    assert 123 == convert(Annotated[None | int | float, "foo"], ["123"])
    assert [123, 456] == convert(Annotated[int, "foo"], ["123", "456"])
    assert [123, 456] == convert(Annotated[None | int | float, "foo"], ["123", "456"])


def test_coerce_enum():
    class SoftwareEnvironment(Enum):
        DEV = auto()
        STAGING = auto()
        PROD = auto()
        _PROD_OLD = (
            auto()
        )  # test that leading underscores are stripped and then hyphens can be used instead of underscores.

        DEVELOPMENT = DEV  # Tests that aliases resolve

    # tests case-insensitivity
    assert SoftwareEnvironment.STAGING == convert(SoftwareEnvironment, ["staging"])

    # tests underscore/hyphen support
    assert SoftwareEnvironment._PROD_OLD == convert(SoftwareEnvironment, ["prod_old"])
    assert SoftwareEnvironment._PROD_OLD == convert(SoftwareEnvironment, ["prod-old"])

    # Test aliases
    assert SoftwareEnvironment.DEV == convert(SoftwareEnvironment, ["development"])

    with pytest.raises(CoercionError):
        convert(SoftwareEnvironment, ["invalid-choice"])


def test_coerce_enum_invalid_choice():
    class GroupedConstants(Enum):
        FOO = auto()
        BAR = auto()

    assert_convert_coercion_error(
        GroupedConstants,
        ["invalid-choice"],
        msg="""Invalid value for "MOCKED_ARGUMENT_NAME": unable to convert "invalid-choice" into one of {'foo', 'bar'}.""",
    )


def test_coerce_enum_invalid_choice_name_transform():
    class SoftwareEnvironment(Enum):
        DEV_LOCAL = 1
        STAGING_US = 2
        PROD_WEST = 3

    assert_convert_coercion_error(
        SoftwareEnvironment,
        ["invalid"],
        msg="""Invalid value for "MOCKED_ARGUMENT_NAME": unable to convert "invalid" into one of {'dev-local', 'staging-us', 'prod-west'}.""",
    )


def test_coerce_enum_invalid_choice_custom_name_transform():
    class SoftwareEnvironment(Enum):
        dev_local = 1
        staging_us = 2

    assert_convert_coercion_error(
        SoftwareEnvironment,
        ["invalid"],
        name_transform=str.upper,
        msg="""Invalid value for "MOCKED_ARGUMENT_NAME": unable to convert "invalid" into one of {'DEV_LOCAL', 'STAGING_US'}.""",
    )


def test_coerce_tuple_basic_single():
    _assert_tuple((1,), convert(tuple[int], ["1"]))


def test_coerce_tuple_str_single():
    _assert_tuple(("foo",), convert(tuple[str], ["foo"]))


def test_coerce_tuple_basic_double():
    _assert_tuple((1, 2.0), convert(tuple[int, None | float | int], ["1", "2"]))


def test_coerce_tuple_typing_no_inner_types():
    _assert_tuple(("1", "2"), convert(tuple, ["1", "2"]))


def test_coerce_tuple_builtin_no_inner_types():
    _assert_tuple(("1", "2"), convert(tuple, ["1", "2"]))


def test_coerce_tuple_nested():
    _assert_tuple(
        (1, (2.0, "foo")),
        convert(tuple[int, tuple[float, None | str | int]], ["1", "2", "foo"]),
    )


def test_coerce_tuple_len_mismatch_underflow():
    with pytest.raises(CoercionError):
        convert(tuple[int, int], ["1"])


def test_coerce_tuple_len_mismatch_overflow():
    with pytest.raises(CoercionError):
        convert(tuple[int, int], ["1", "2", "3"])


@pytest.mark.skipif(sys.version_info < (3, 11), reason="Typing")
def test_coerce_tuple_ellipsis_too_many_inner_types():
    with pytest.raises(ValueError):  # This is a ValueError because it happens prior to runtime.
        # Only 1 inner type annotation allowed
        convert(tuple[int, int, ...], ["1", "2"])  # pyright: ignore


def test_coerce_tuple_ellipsis_non_divisible():
    with pytest.raises(CoercionError):
        convert(tuple[tuple[int, int], ...], ["1", "2", "3"])


def test_coerce_list():
    assert [123, 456] == convert(int, ["123", "456"])
    assert [123, 456] == convert(list[int], ["123", "456"])
    assert [123] == convert(list[int], ["123"])


def test_coerce_list_of_tuple_str_single_1():
    res = convert(list[tuple[str]], ["foo"])
    assert isinstance(res, list)
    assert len(res) == 1
    _assert_tuple(("foo",), res[0])


def test_coerce_list_of_tuple_str_single_2():
    res = convert(list[tuple[str]], ["foo", "bar"])
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
    assert {"123", "456"} == convert(set[str], ["123", "456"])
    assert {123, 456} == convert(set[int | str], ["123", "456"])


def test_coerce_frozenset():
    assert frozenset({"123", "456"}) == convert(frozenset[str], ["123", "456"])
    assert frozenset({123, 456}) == convert(frozenset[int | str], ["123", "456"])


@pytest.mark.parametrize(
    "hint,expected",
    [
        (AbcSet[str], {"123", "456"}),
        (AbcMutableSet[str], {"123", "456"}),
        (AbcMutableSequence[str], ["123", "456"]),
        (AbcSet, {"123", "456"}),
        (AbcMutableSet, {"123", "456"}),
        (AbcMutableSequence, ["123", "456"]),
    ],
)
def test_coerce_abstract_collection_types(hint, expected):
    """Test that collections.abc abstract types are supported (issue #702).

    Tests both parameterized types (e.g., Set[str]) and bare types (e.g., Set).
    Bare abstract types should default to [str] like bare concrete types do.
    """
    result = convert(hint, ["123", "456"])
    assert expected == result


def test_coerce_literal():
    assert "foo" == convert(Literal["foo", "bar", 3], ["foo"])
    assert "bar" == convert(Literal["foo", "bar", 3], ["bar"])
    assert 3 == convert(Literal["foo", "bar", 3], ["3"])


def assert_convert_coercion_error(*args, msg, name_transform=None, **kwargs):
    if name_transform is None:
        name_transform = default_name_transform
    mock_argument = Mock()
    mock_argument.name = "mocked_argument_name"
    mock_argument.parameter.name_transform = name_transform
    kwargs.setdefault("name_transform", name_transform)
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
        msg="""Invalid value for "MOCKED_ARGUMENT_NAME": unable to convert "invalid-choice" into one of {'foo', 'bar', 3}.""",
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
        msg="""Invalid value for "MOCKED_ARGUMENT_NAME" from TEST: unable to convert "invalid-choice" into one of {'foo', 'bar', 3}.""",
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


def test_coerce_date():
    expected = date(year=1956, month=1, day=31)
    assert expected == convert(date, ["1956-01-31"])


@pytest.mark.skipif(sys.version_info < (3, 11), reason="Not implemented in stdlib")
def test_coerce_date_other_iso_formats():
    expected = date(year=2021, month=1, day=4)
    assert expected == convert(date, ["2021-W01-1"])


@pytest.mark.parametrize(
    "input_string, format_str",
    [
        ("1956-01-31", "%Y-%m-%d"),  # ISO 8601 date only
        ("1956-01-31T10:00:00", "%Y-%m-%dT%H:%M:%S"),  # ISO 8601 with time
        ("1956-01-31 10:00:00", "%Y-%m-%d %H:%M:%S"),  # Space separator
        ("1956-01-31T10:00:00.123456", "%Y-%m-%dT%H:%M:%S.%f"),  # With microseconds
    ],
)
def test_coerce_datetime(input_string, format_str):
    """Test that various datetime formats are supported."""
    expected = datetime.strptime(input_string, format_str)
    assert expected == convert(datetime, [input_string])


@pytest.mark.parametrize(
    "input_string, expected_output",
    [
        # Basic single unit tests
        ("30s", timedelta(seconds=30)),
        ("5m", timedelta(minutes=5)),
        ("2h", timedelta(hours=2)),
        ("1d", timedelta(days=1)),
        ("3w", timedelta(weeks=3)),
        ("6M", timedelta(days=30 * 6)),  # Approximation: 1 month = 30 days
        ("1y", timedelta(days=365)),  # Approximation: 1 year = 365 days
        # Combined duration tests
        ("1h30m", timedelta(hours=1, minutes=30)),
        ("1d12h", timedelta(days=1, hours=12)),
        ("2d5h30m", timedelta(days=2, hours=5, minutes=30)),
        ("1w2d", timedelta(weeks=1, days=2)),
        ("3h45m20s", timedelta(hours=3, minutes=45, seconds=20)),
        # Zero and small values
        ("0s", timedelta(seconds=0)),
        ("1s", timedelta(seconds=1)),
        # Large values
        ("100d", timedelta(days=100)),
        ("10000s", timedelta(seconds=10000)),
        # Mixed order (should still work)
        ("30m1h", timedelta(hours=1, minutes=30)),
        ("45s2h", timedelta(hours=2, seconds=45)),
        # Repeated units (should add them)
        ("1h1h", timedelta(hours=2)),
        ("1d1d1d", timedelta(days=3)),
        # Negative duration
        ("-1h", timedelta(hours=-1)),
        # Decimal duration
        ("1.5h", timedelta(hours=1.5)),
    ],
)
def test_parse_timedelta_valid(input_string, expected_output):
    """Test that valid duration strings are parsed correctly."""
    assert convert(timedelta, [input_string]) == expected_output


@pytest.mark.parametrize(
    "invalid_input",
    [
        "",  # Empty string
        "abc",  # No numbers or units
        "1",  # Number without unit
        "1x",  # Invalid unit
        "h1",  # Unit before number
        "3 days",  # Full unit names with spaces not supported
    ],
)
def test_parse_timedelta_invalid(invalid_input):
    with pytest.raises(CoercionError):
        convert(timedelta, [invalid_input])


def test_coerce_date_invalid_format():
    """Test that invalid date format raises CoercionError."""
    with pytest.raises(CoercionError):
        convert(date, ["not-a-date"])


def test_coerce_datetime_invalid_format():
    """Test that invalid datetime format raises CoercionError."""
    with pytest.raises(CoercionError):
        convert(datetime, ["not-a-date"])


def test_parse_timedelta_equivalence():
    """Test that equivalent timedelta formats produce the same result."""
    assert convert(timedelta, ["1h"]) == convert(timedelta, ["60m"])
    assert convert(timedelta, ["1d"]) == convert(timedelta, ["24h"])
    assert convert(timedelta, ["1w"]) == convert(timedelta, ["7d"])
    assert convert(timedelta, ["1h30m"]) == convert(timedelta, ["90m"])
    assert convert(timedelta, ["1d12h"]) == convert(timedelta, ["36h"])
