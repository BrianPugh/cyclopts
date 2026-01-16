from pathlib import Path
from typing import Annotated, Literal

import pytest

from cyclopts import Parameter

# Case variations of "none" and "null" strings that should be parsed as None
NONE_STRINGS = ["none", "null", "NONE", "NULL", "None", "Null"]


def test_bind_negative_none(app, assert_parse_args):
    @app.default
    def default(path: Annotated[Path | None, Parameter(negative_none="default-")]):
        pass

    assert_parse_args(default, "--default-path", None)


def test_bind_negative_none_multi_token(app, assert_parse_args):
    """Test negative_none works with multi-token types like tuple[int, int]."""

    @app.default
    def default(value: Annotated[tuple[int, int] | None, Parameter(negative_none="no-")] = None):
        pass

    # With values
    assert_parse_args(default, "1 2", (1, 2))

    # Omitting uses default
    assert_parse_args(default, "")

    # Negative flag sets to None
    assert_parse_args(default, "--no-value", None)


@pytest.mark.parametrize("none_str", NONE_STRINGS)
def test_bind_none_string_int_or_none(app, assert_parse_args, none_str):
    """Test that 'none' and 'null' strings are converted to None for int | None."""

    @app.default
    def default(value: int | None = 2):
        pass

    assert_parse_args(default, f"--value={none_str}", None)


@pytest.mark.parametrize("none_str", NONE_STRINGS)
def test_bind_none_string_none_or_path(app, assert_parse_args, none_str):
    """Test that 'none' and 'null' strings are converted to None for None | Path.

    Union ordering matters: None comes before Path, so 'none' becomes None.
    """

    @app.default
    def default(path: None | Path):
        pass

    assert_parse_args(default, f"--path={none_str}", None)


@pytest.mark.parametrize("none_str", NONE_STRINGS)
def test_bind_none_string_path_or_none(app, assert_parse_args, none_str):
    """Test that 'none' and 'null' strings become Path for Path | None.

    Union ordering matters: Path comes before None, and Path("none") is valid.
    """

    @app.default
    def default(path: Path | None):
        pass

    assert_parse_args(default, f"--path={none_str}", Path(none_str))


@pytest.mark.parametrize("none_str", NONE_STRINGS)
def test_bind_none_string_none_first_in_union(app, assert_parse_args, none_str):
    """When None comes before str in union, 'none' should become None."""

    @app.default
    def default(value: None | str):
        pass

    assert_parse_args(default, f"--value={none_str}", None)


def test_bind_none_string_str_first_in_union(app, assert_parse_args):
    """When str comes before None in union, 'none' should stay as string 'none'."""

    @app.default
    def default(value: str | None):
        pass

    assert_parse_args(default, "--value=none", "none")


@pytest.mark.parametrize("none_str", NONE_STRINGS)
def test_bind_none_string_int_none_str_union(app, assert_parse_args, none_str):
    """For int | None | str, 'none' should become None (int fails, None succeeds)."""

    @app.default
    def default(value: int | None | str):
        pass

    assert_parse_args(default, f"--value={none_str}", None)


def test_bind_none_string_int_str_none_union(app, assert_parse_args):
    """For int | str | None, 'none' should become 'none' string (int fails, str succeeds)."""

    @app.default
    def default(value: int | str | None):
        pass

    assert_parse_args(default, "--value=none", "none")


@pytest.mark.parametrize("none_str", NONE_STRINGS)
def test_bind_none_string_positional(app, assert_parse_args, none_str):
    """Test that 'none' works for positional arguments too."""

    @app.default
    def default(value: int | None):
        pass

    assert_parse_args(default, none_str, None)


@pytest.mark.parametrize("none_str", NONE_STRINGS)
def test_bind_list_int_none_inner(app, assert_parse_args, none_str):
    """Test list[int | None]: elements can be int or None."""

    @app.default
    def default(values: list[int | None]):
        pass

    # Mixed int and None values
    assert_parse_args(default, f"1 {none_str} 3", [1, None, 3])


@pytest.mark.parametrize("none_str", NONE_STRINGS)
def test_bind_list_int_none_inner_and_outer(app, assert_parse_args, none_str):
    """Test list[int | None] | None: outer None for default, inner None for elements."""

    @app.default
    def default(values: list[int | None] | None = None):
        pass

    # No args uses default
    assert_parse_args(default, "")

    # Multiple int values
    assert_parse_args(default, "1 2 3", [1, 2, 3])

    # Mixed int and None values
    assert_parse_args(default, f"1 {none_str} 3", [1, None, 3])

    # Single "none" becomes [None] (element is None, not the whole list)
    assert_parse_args(default, none_str, [None])

    # Multiple "none" strings become list of Nones
    assert_parse_args(default, "none null", [None, None])


@pytest.mark.parametrize("none_str", NONE_STRINGS)
def test_bind_none_or_list_int_none(app, assert_parse_args, none_str):
    """Test None | list[int | None]: union ordering matters.

    When None comes first in the union, "none"/"null" tokens match the None type
    before the list is considered. To get a list with None elements, put list first.
    """

    @app.default
    def default(values: None | list[int | None] = None):
        pass

    # "none" matches the None type (comes first in union) -> None
    assert_parse_args(default, none_str, None)


@pytest.mark.parametrize(
    "type_hint,expected_single,expected_multi",
    [
        # When list comes first: str accepts "none" as a valid string -> ["none"]
        (list[str] | None, lambda s: [s], ["a", "b"]),
        # When list comes first: Path accepts "none" as a valid path -> [Path("none")]
        (list[Path] | None, lambda s: [Path(s)], [Path("a"), Path("b")]),
    ],
    ids=["list[str]|None", "list[Path]|None"],
)
@pytest.mark.parametrize("none_str", NONE_STRINGS)
def test_bind_list_first_optional(app, assert_parse_args, type_hint, expected_single, expected_multi, none_str):
    """Test list[T] | None: list comes first, so it gets the tokens."""

    @app.default
    def default(values: type_hint = None):  # pyright: ignore[reportInvalidTypeForm]
        pass

    # Single "none" becomes a list with one element (the element type determines the value)
    expected = expected_single(none_str) if callable(expected_single) else expected_single
    assert_parse_args(default, none_str, expected)

    # Multiple values work
    assert_parse_args(default, "a b", expected_multi)


@pytest.mark.parametrize(
    "type_hint,expected_multi",
    [
        # When None comes first: "none" matches None, not the list
        (None | list[str], ["a", "b"]),
        (None | list[Path], [Path("a"), Path("b")]),
    ],
    ids=["None|list[str]", "None|list[Path]"],
)
@pytest.mark.parametrize("none_str", NONE_STRINGS)
def test_bind_none_first_optional_list(app, assert_parse_args, type_hint, expected_multi, none_str):
    """Test None | list[T]: None comes first, so 'none' matches None type."""

    @app.default
    def default(values: type_hint = None):  # pyright: ignore[reportInvalidTypeForm]
        pass

    # "none" matches the None type (comes first in union) -> None
    assert_parse_args(default, none_str, None)

    # Non-none values still work with the list
    assert_parse_args(default, "a b", expected_multi)


@pytest.mark.parametrize("none_str", NONE_STRINGS)
def test_bind_none_string_multi_token_none_first(app, assert_parse_args, none_str):
    """Test None | tuple[int, int]: 'none' works because None comes first in union.

    Token-aware token_count detects the none-string and returns 1 instead of 2.
    """

    @app.default
    def default(value: None | tuple[int, int] = None):
        pass

    # Normal tuple parsing still works
    assert_parse_args(default, "1 2", (1, 2))

    # Omitting uses default
    assert_parse_args(default, "")

    # "none" string becomes None (token-aware handling)
    assert_parse_args(default, none_str, None)


def test_bind_none_string_multi_token_tuple_first(app, assert_parse_args):
    """Test tuple[int, int] | None: 'none' works because None can handle it.

    Even though tuple comes first, it needs 2 tokens and we only have 1.
    The algorithm skips tuple and finds that None can convert 'none'.
    """

    @app.default
    def default(value: tuple[int, int] | None = None):
        pass

    # Normal tuple parsing still works
    assert_parse_args(default, "1 2", (1, 2))

    # "none" works - tuple needs 2 tokens but we have 1, so skip to None which handles it
    assert_parse_args(default, "none", None)


# Tests for Literal + multi-token type unions


@pytest.mark.parametrize(
    "type_hint,literal_values",
    [
        # Literal must come before multi-token types for matching to work
        (Literal["preset1", "preset2"] | tuple[int, int], ["preset1", "preset2"]),
        (Literal["a", "b"] | Literal["c", "d"] | tuple[int, int], ["a", "b", "c", "d"]),
    ],
    ids=["Literal|tuple", "Literal|Literal|tuple"],
)
def test_bind_literal_or_tuple(app, assert_parse_args, type_hint, literal_values):
    """Test Literal + multi-token unions. Literal must come first for matching to work."""

    @app.default
    def default(config: type_hint):  # pyright: ignore[reportInvalidTypeForm]
        pass

    # All literal values work
    for val in literal_values:
        assert_parse_args(default, val, val)

    # Tuple fallback works
    assert_parse_args(default, "10 20", (10, 20))


def test_bind_tuple_or_literal_order_matters(app, assert_parse_args):
    """Test tuple[int, int] | Literal["preset"]: both work based on token availability.

    Tuple needs 2 tokens, Literal needs 1. If only 1 token is provided and it
    matches the Literal, the Literal is used (tuple is skipped due to insufficient tokens).
    """

    @app.default
    def default(config: tuple[int, int] | Literal["preset"]):  # pyright: ignore[reportInvalidTypeForm]
        pass

    # Tuple works with 2 tokens
    assert_parse_args(default, "10 20", (10, 20))

    # Literal works - tuple needs 2 tokens but we have 1, so skip to Literal which matches
    assert_parse_args(default, "preset", "preset")


def test_bind_literal_none_or_tuple(app, assert_parse_args):
    """Test Literal["auto"] | None | tuple[int, int]: combines Literal, None, and multi-token."""

    @app.default
    def default(config: Literal["auto"] | None | tuple[int, int] = None):
        pass

    assert_parse_args(default, "auto", "auto")  # Literal
    assert_parse_args(default, "none", None)  # None sentinel
    assert_parse_args(default, "10 20", (10, 20))  # Tuple fallback
    assert_parse_args(default, "")  # Default


def test_bind_literal_case_sensitive(app, assert_parse_args):
    """Test that Literal matching is case-sensitive."""
    from cyclopts.exceptions import CoercionError

    @app.default
    def default(config: Literal["Preset"] | tuple[int, int]):
        pass

    assert_parse_args(default, "Preset", "Preset")

    # Wrong case fails - Literal doesn't match (case-sensitive), tuple needs 2 tokens
    # but we have 1, so no type can handle the input → CoercionError
    with pytest.raises(CoercionError):
        app.parse_args(["preset"], exit_on_error=False)


def test_bind_int_or_tuple_coercion(app, assert_parse_args):
    """Test int | tuple[str, int]: first token coercion determines token count.

    When first token can be coerced to int, consume 1 token.
    When first token cannot be coerced to int, fall back to tuple (2 tokens).
    """

    @app.default
    def default(value: int | tuple[str, int] = 5):
        pass

    # Int works - single token
    assert_parse_args(default, "42", 42)

    # Non-int first token triggers tuple fallback - two tokens
    assert_parse_args(default, "foo 10", ("foo", 10))

    # Default works
    assert_parse_args(default, "")


def test_bind_str_or_tuple(app, assert_parse_args):
    """Test str | tuple[int, int]: str can accept any string, so always uses 1 token."""

    @app.default
    def default(value: str | tuple[int, int]):
        pass

    # str accepts "foo" - single token
    assert_parse_args(default, "foo", "foo")

    # str also accepts "10" - single token (str comes first)
    assert_parse_args(default, "10", "10")


# Tests for multi-token type unions with different token counts


def test_bind_tuple_different_sizes(app, assert_parse_args):
    """Test tuple[int, int] | tuple[str, int, int]: left-to-right priority."""
    from cyclopts.exceptions import UnusedCliTokensError

    @app.default
    def default(values: tuple[int, int] | tuple[str, int, int] = (1, 2)):
        pass

    # 2 int tokens → tuple[int, int] (first type succeeds)
    assert_parse_args(default, "1 2", (1, 2))

    # 3 tokens with non-int first → tuple[str, int, int]
    # tuple[int, int] fails because "foo" can't convert to int
    assert_parse_args(default, "foo 3 4", ("foo", 3, 4))

    # 3 int tokens → tuple[int, int] takes first 2, leaves "5" unused
    # Left-to-right priority: first successful type wins
    with pytest.raises(UnusedCliTokensError):
        app.parse_args(["3", "4", "5"], exit_on_error=False)

    # Default works
    assert_parse_args(default, "")


def test_bind_tuple_sizes_order_matters(app, assert_parse_args):
    """Test tuple[str, int, int] | tuple[int, int]: larger tuple first."""

    @app.default
    def default(values: tuple[str, int, int] | tuple[int, int]):
        pass

    # 3 tokens → tuple[str, int, int] (comes first, can consume all)
    assert_parse_args(default, "foo 3 4", ("foo", 3, 4))

    # 2 int tokens → tuple[str, int, int] fails (needs 3), tuple[int, int] succeeds
    assert_parse_args(default, "1 2", (1, 2))


def test_bind_list_or_tuple(app, assert_parse_args):
    """Test list[int] | tuple[str, int]: consume_all vs fixed-count."""

    @app.default
    def default(values: list[int] | tuple[str, int]):
        pass

    # All ints → list[int] (consume_all)
    assert_parse_args(default, "1 2 3", [1, 2, 3])

    # Non-int first → list[int] fails, tuple[str, int] succeeds
    assert_parse_args(default, "foo 42", ("foo", 42))


def test_bind_tuple_or_list(app, assert_parse_args):
    """Test tuple[str, int] | list[int]: left-to-right priority."""
    from cyclopts.exceptions import UnusedCliTokensError

    @app.default
    def default(values: tuple[str, int] | list[int]):
        pass

    # 2 tokens with non-int first → tuple[str, int]
    assert_parse_args(default, "foo 42", ("foo", 42))

    # 2 int tokens → tuple[str, int] succeeds (left-to-right priority)
    # "1" converts to str, "2" converts to int
    assert_parse_args(default, "1 2", ("1", 2))

    # 3 ints → tuple[str, int] takes first 2, leaves "3" unused
    # Left-to-right priority: first successful type wins
    with pytest.raises(UnusedCliTokensError):
        app.parse_args(["1", "2", "3"], exit_on_error=False)


def test_bind_nested_union(app, assert_parse_args):
    """Test (int | str) | tuple[int, int]: nested union handling with left-to-right priority."""
    from cyclopts.exceptions import UnusedCliTokensError

    @app.default
    def default(value: (int | str) | tuple[int, int]):  # pyright: ignore[reportInvalidTypeForm]
        pass

    # Single int token → int (from inner union)
    assert_parse_args(default, "42", 42)

    # Single non-int token → str (from inner union)
    assert_parse_args(default, "foo", "foo")

    # Two int tokens → int succeeds on first token, leaves second unused
    # Left-to-right priority: int comes first in the flattened union
    with pytest.raises(UnusedCliTokensError):
        app.parse_args(["1", "2"], exit_on_error=False)


def test_bind_same_count_tuples(app, assert_parse_args):
    """Test tuple[int, int] | tuple[str, str]: left-to-right tiebreaker for same token count."""

    @app.default
    def default(value: tuple[int, int] | tuple[str, str]):
        pass

    # Both tuples need 2 tokens. "1 2" can convert to both.
    # Left-to-right priority: tuple[int, int] wins
    assert_parse_args(default, "1 2", (1, 2))

    # "foo bar" can only convert to tuple[str, str]
    assert_parse_args(default, "foo bar", ("foo", "bar"))

    # "1 foo" - tuple[int, int] fails (can't convert "foo" to int)
    # tuple[str, str] succeeds
    assert_parse_args(default, "1 foo", ("1", "foo"))


def test_bind_not_enough_tokens_for_any_type(app):
    """Test union where no type has enough tokens."""
    from cyclopts.exceptions import CoercionError

    @app.default
    def default(value: tuple[int, int, int] | tuple[str, int, int]):
        pass

    # Only 1 token provided, both types need 3
    # Results in CoercionError since no type can handle the input
    with pytest.raises(CoercionError):
        app.parse_args(["1"], exit_on_error=False)


def test_bind_validation_error_in_union(app, assert_parse_args):
    """Test validator behavior on inner union members.

    Validators on inner union members (like Annotated[int, Parameter(validator=...)])
    do not run during union type resolution. The union picks the first type that
    can CONVERT successfully, regardless of whether validators would pass.
    """
    from cyclopts import Parameter, validators

    @app.default
    def default(value: Annotated[int, Parameter(validator=validators.Number(gt=10))] | str):
        pass

    # "5" converts to int successfully - validator doesn't block union resolution
    # This documents current behavior: validators on inner union members
    # don't participate in union type selection
    assert_parse_args(default, "5", 5)

    # "foo" can't convert to int, falls through to str
    assert_parse_args(default, "foo", "foo")


def test_bind_union_with_annotated_parameter(app, assert_parse_args):
    """Test union types with Annotated and Parameter."""

    @app.default
    def default(value: Annotated[tuple[int, int] | None, Parameter(negative_none="no-")] = None):
        pass

    # Normal tuple parsing
    assert_parse_args(default, "1 2", (1, 2))

    # "none" string
    assert_parse_args(default, "none", None)

    # Negative flag
    assert_parse_args(default, "--no-value", None)

    # Default
    assert_parse_args(default, "")


def test_bind_enum_in_union(app, assert_parse_args):
    """Test enum type in union with other types."""
    from enum import Enum

    class Color(Enum):
        RED = "red"
        GREEN = "green"
        BLUE = "blue"

    @app.default
    def default(value: Color | int):
        pass

    # Enum value matches
    assert_parse_args(default, "red", Color.RED)
    assert_parse_args(default, "GREEN", Color.GREEN)

    # Not an enum value, falls through to int
    assert_parse_args(default, "42", 42)


@pytest.mark.parametrize(
    "cli_input,expected_result",
    [
        ("21", 42),
        ("hello", "HELLO"),
        ("none", "NONE"),  # Custom converter handles everything, including "none"
    ],
)
def test_bind_union_custom_converter(app, assert_parse_args, mocker, cli_input, expected_result):
    """Test custom converter with union type including None.

    When a custom converter is provided, it takes full responsibility for conversion.
    The converter receives the resolved type (int | str, with None stripped).
    """

    def _my_converter(type_, tokens):
        token = tokens[0] if isinstance(tokens, (list, tuple)) else tokens
        value = token.value if hasattr(token, "value") else str(token)
        # Try int conversion, fall back to uppercase string
        try:
            return int(value) * 2
        except ValueError:
            return value.upper()

    my_converter = mocker.Mock(side_effect=_my_converter)

    @app.default
    def default(value: Annotated[int | None | str, Parameter(converter=my_converter)]):
        pass

    assert_parse_args(default, cli_input, expected_result)
    my_converter.assert_called_once()


def test_bind_optional_custom_converter_receives_resolved_type(app, assert_parse_args, mocker):
    """Test that custom converters receive the resolved Optional type.

    For `int | None`, the converter should receive `int`, not `int | None`.
    This keeps user converters simple - they don't need to handle None.
    """

    def _my_converter(type_, tokens):
        token = tokens[0] if isinstance(tokens, (list, tuple)) else tokens
        value = token.value if hasattr(token, "value") else str(token)
        return int(value) * 2

    my_converter = mocker.Mock(side_effect=_my_converter)

    @app.default
    def default(value: Annotated[int | None, Parameter(converter=my_converter)]):
        pass

    assert_parse_args(default, "21", 42)

    # Converter should receive `int`, not `int | None`
    my_converter.assert_called_once_with(int, mocker.ANY)


def test_bind_validation_error_propagation_in_union(app):
    """Test that ValidationError is properly propagated during union probing.

    When a union member successfully converts but fails validation,
    the ValidationError should be raised (not swallowed).
    """
    from cyclopts import validators
    from cyclopts.exceptions import ValidationError

    @app.default
    def default(value: Annotated[int, Parameter(validator=validators.Number(gt=100))] | None):
        pass

    # Value 50 converts to int but fails validation (not > 100)
    # ValidationError should propagate
    with pytest.raises(ValidationError):
        app.parse_args(["50"], exit_on_error=False)
