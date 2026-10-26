"""Tests for Python 3.12+ TypeAliasType with Parameter metadata.

Regression tests for https://github.com/BrianPugh/cyclopts/issues/669
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Optional

import pytest

from cyclopts import Parameter
from cyclopts import types as ct
from cyclopts.annotations import resolve, resolve_annotated, resolve_optional

# Define type aliases using Python 3.12 'type' statement
type IntWithAlias = Annotated[int, Parameter(alias="-f")]
type OptionalIntWithAlias = Optional[Annotated[int, Parameter(alias="-f")]]
type BoolAlias = bool
type AnnotatedIntWithMetadata = Annotated[int, "metadata"]
type OptionalInt = Optional[int]
# A 'type' alias over a cyclopts.types converter type (which is itself Annotated).
# https://github.com/BrianPugh/cyclopts/issues/836
type ResolvedPathAlias = ct.ResolvedPath
# A generic 'type' alias, subscripted at the use site.
# https://github.com/BrianPugh/cyclopts/issues/1028
type Flattened[T] = Annotated[T, Parameter(name="*")]
type Same[T] = T
type Swapped[A, B] = tuple[B, A]
type Ignored[T] = int


@dataclass(frozen=True, kw_only=True)
class Upper:
    upper: bool = False


@dataclass(frozen=True, kw_only=True)
class Lower:
    lower: bool = False


@dataclass(frozen=True, kw_only=True)
class Opts:
    test: bool = False


@Parameter(name="*")
@dataclass(frozen=True, kw_only=True)
class StarOpts:
    test: bool = False


# 'type' aliases that carry Parameter(name="*"), directly or through another alias or a decorated class.
# https://github.com/BrianPugh/cyclopts/issues/1029
type OptsStar = Annotated[Opts, Parameter(name="*")]
type OptsStarAlias = OptsStar
type StarOptsAlias = StarOpts


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


def test_type_alias_over_cyclopts_type_bare(app, assert_parse_args):
    """A 'type' alias over a cyclopts.types converter type keeps the converter."""

    @app.default
    def main(foo: ResolvedPathAlias):
        pass

    assert_parse_args(main, "bar", Path("bar").resolve())


def test_generic_type_alias_with_parameter_name_star(app, assert_parse_args):
    """A subscripted generic 'type' alias keeps its ``Parameter(name="*")``."""

    @app.default
    def main(*, upper: Flattened[Upper] = Upper(), lower: Flattened[Lower] = Lower()):
        pass

    assert_parse_args(main, "--upper --lower", upper=Upper(upper=True), lower=Lower(lower=True))


def test_generic_type_alias_of_bare_type_parameter(app, assert_parse_args):
    """A generic 'type' alias whose value is the type parameter itself."""

    @app.default
    def main(foo: Same[int]):
        pass

    assert_parse_args(main, "3", 3)


def test_generic_type_alias_substitutes_by_parameter_order(app, assert_parse_args):
    """Type arguments bind to the alias's own parameters, not to their order in its value."""

    @app.default
    def main(foo: Swapped[str, int]):
        pass

    assert_parse_args(main, "1 a", (1, "a"))


def test_generic_type_alias_with_unused_type_parameter(app, assert_parse_args):
    """A generic 'type' alias whose value doesn't use its type parameter."""

    @app.default
    def main(foo: Ignored[str]):
        pass

    assert_parse_args(main, "3", 3)


def test_type_alias_over_cyclopts_type_optional(app, assert_parse_args):
    """A 'type' alias over a cyclopts.types converter type, made optional, keeps the converter."""

    @app.default
    def main(foo: Annotated[Optional[ResolvedPathAlias], Parameter()]):
        pass

    assert_parse_args(main, "bar", Path("bar").resolve())


@pytest.mark.parametrize(
    "hint,class_name",
    [
        (OptsStar, "Opts"),
        (OptsStarAlias, "Opts"),
        (StarOptsAlias, "StarOpts"),
    ],
)
def test_type_alias_star_parameter_without_default_raises(app, hint, class_name):
    """A 'type' alias with ``Parameter(name="*")`` gets the same setup-time error as the inline hint."""

    def cmd(opts: hint):  # pyright: ignore[reportInvalidTypeForm]
        pass

    with pytest.raises(ValueError, match=rf'providing a default value "opts: {class_name} = {class_name}\(\)"'):
        app.default(cmd)


def test_type_alias_star_parameter_with_default(app, assert_parse_args):
    """A 'type' alias with ``Parameter(name="*")`` and a default value parses its fields as flags."""

    @app.default
    def main(opts: OptsStar = Opts()):
        pass

    assert_parse_args(main, "--test", opts=Opts(test=True))
