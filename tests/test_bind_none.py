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
    """Test tuple[int, int] | None: 'none' fails because tuple comes first and expects 2 tokens."""
    import pytest as pt

    from cyclopts.exceptions import MissingArgumentError

    @app.default
    def default(value: tuple[int, int] | None = None):
        pass

    # Normal tuple parsing still works
    assert_parse_args(default, "1 2", (1, 2))

    # "none" fails - tuple expects 2 tokens, we only gave 1
    # This raises MissingArgumentError at the binding stage (not CoercionError)
    with pt.raises(MissingArgumentError):
        app.parse_args(["none"], exit_on_error=False)


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
    """Test tuple[int, int] | Literal["a"]: tuple comes first, so Literal won't match."""
    from cyclopts.exceptions import MissingArgumentError

    @app.default
    def default(config: tuple[int, int] | Literal["preset"]):  # pyright: ignore[reportInvalidTypeForm]
        pass

    # Tuple works
    assert_parse_args(default, "10 20", (10, 20))

    # Literal fails - tuple comes first and expects 2 tokens
    with pytest.raises(MissingArgumentError):
        app.parse_args(["preset"], exit_on_error=False)


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
    from cyclopts.exceptions import MissingArgumentError

    @app.default
    def default(config: Literal["Preset"] | tuple[int, int]):
        pass

    assert_parse_args(default, "Preset", "Preset")

    # Wrong case fails (tries tuple, which needs 2 tokens)
    with pytest.raises(MissingArgumentError):
        app.parse_args(["preset"], exit_on_error=False)
