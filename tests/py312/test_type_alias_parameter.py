"""Tests for Python 3.12+ TypeAliasType with Parameter metadata.

Regression tests for https://github.com/BrianPugh/cyclopts/issues/669
"""

from typing import Annotated, Optional

import pytest

from cyclopts import Parameter
from cyclopts.annotations import resolve, resolve_annotated, resolve_optional

# Define type aliases using Python 3.12 'type' statement
type IntWithAlias = Annotated[int, Parameter(alias="-f")]
type OptionalIntWithAlias = Optional[Annotated[int, Parameter(alias="-f")]]
type BoolAlias = bool
type AnnotatedIntWithMetadata = Annotated[int, "metadata"]
type OptionalInt = Optional[int]


@pytest.mark.parametrize(
    "cmd_str,expected",
    [
        ("--foo 10", 10),
        ("-f 10", 10),
    ],
)
def test_type_alias_with_parameter_alias(app, assert_parse_args, cmd_str, expected):
    """Test that type statement (TypeAliasType) works with Parameter alias."""

    @app.default
    def main(foo: IntWithAlias):
        pass

    assert_parse_args(main, cmd_str, foo=expected)


@pytest.mark.parametrize(
    "cmd_str,expected",
    [
        ("--foo 10", 10),
        ("-f 10", 10),
    ],
)
def test_type_alias_optional_with_parameter_alias(app, assert_parse_args, cmd_str, expected):
    """Test that Optional TypeAliasType works with Parameter alias."""

    @app.default
    def main(foo: OptionalIntWithAlias = None):
        pass

    assert_parse_args(main, cmd_str, foo=expected)


def test_parameter_get_negatives_with_type_alias():
    """Test that Parameter.get_negatives works with TypeAliasType."""
    p = Parameter(name=("--foo", "--bar"))
    assert ("--no-foo", "--no-bar") == p.get_negatives(BoolAlias)


def test_parameter_from_annotation_type_alias():
    """Test that Parameter.from_annotation works with TypeAliasType."""
    result_type, result_param = Parameter.from_annotation(IntWithAlias, Parameter())
    assert result_type is int
    assert result_param.alias == ("-f",)


@pytest.mark.parametrize(
    "type_alias,resolve_func,expected",
    [
        (AnnotatedIntWithMetadata, resolve, int),
        (OptionalInt, resolve, int),
        (AnnotatedIntWithMetadata, resolve_annotated, int),
        (OptionalInt, resolve_optional, int),
    ],
    ids=[
        "resolve(Annotated[int])",
        "resolve(Optional[int])",
        "resolve_annotated(Annotated[int])",
        "resolve_optional(Optional[int])",
    ],
)
def test_resolve_functions_with_type_alias(type_alias, resolve_func, expected):
    """Test that resolve functions handle TypeAliasType automatically."""
    res = resolve_func(type_alias)
    assert res is expected


def test_type_alias_in_help(capsys):
    """Test that TypeAliasType appears correctly in help text."""
    from cyclopts import App

    app = App()

    @app.default
    def main(foo: IntWithAlias):
        """Test command.

        Parameters
        ----------
        foo : int
            A parameter with alias.
        """
        pass

    try:
        app(["--help"])
    except SystemExit:
        pass

    captured = capsys.readouterr()
    help_text = captured.out
    assert "--foo" in help_text
    assert "-f" in help_text
