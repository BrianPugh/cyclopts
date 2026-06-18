"""Tests that ``cyclopts.types`` converters/validators survive being wrapped in
additional ``Annotated`` / ``Optional`` / ``NewType`` layers.

Regression tests for https://github.com/BrianPugh/cyclopts/issues/836

The ``cyclopts.types.*`` aliases are themselves ``Annotated[..., Parameter(...)]``.
Wrapping them again (e.g. ``Annotated[ResolvedPath | None, Parameter()]``) used to
drop the inner ``Parameter`` -- and with it the converter/validator.
"""

from pathlib import Path
from typing import Annotated, NewType, Optional, Union

import pytest

from cyclopts import Parameter
from cyclopts import types as ct
from cyclopts.exceptions import ValidationError


def test_types_resolved_optional_no_outer_param(app, assert_parse_args):
    """Converter type inside ``Optional`` with no extra outer ``Parameter``."""

    @app.default
    def main(foo: ct.ResolvedPath | None):
        pass

    assert_parse_args(main, "bar", Path("bar").resolve())


def test_types_resolved_optional_with_outer_param(app, assert_parse_args):
    """https://github.com/BrianPugh/cyclopts/issues/836 (the original report)."""

    @app.default
    def main(foo: Annotated[ct.ResolvedPath | None, Parameter()]):
        pass

    assert_parse_args(main, "bar", Path("bar").resolve())


def test_types_resolved_optional_typing_optional_spelling(app, assert_parse_args):
    """``Optional[...]`` spelling behaves the same as ``... | None``."""

    @app.default
    def main(foo: Annotated[Optional[ct.ResolvedPath], Parameter()]):
        pass

    assert_parse_args(main, "bar", Path("bar").resolve())


def test_types_resolved_optional_union_spelling(app, assert_parse_args):
    """``Union[..., None]`` spelling behaves the same as ``... | None``."""

    @app.default
    def main(foo: Annotated[Union[ct.ResolvedPath, None], Parameter()]):
        pass

    assert_parse_args(main, "bar", Path("bar").resolve())


def test_types_resolved_file_optional_converter_applies(app, assert_parse_args):
    """``ResolvedFile`` triple-nests (Annotated[Annotated[Annotated[...]]]); converter still fires."""

    @app.default
    def main(foo: Annotated[ct.ResolvedFile | None, Parameter()]):
        pass

    assert_parse_args(main, "foo.bin", Path("foo.bin").resolve())


def test_types_resolved_file_optional_validator_still_fires(app, tmp_path):
    """The inner validator (file-only) must not be lost when wrapped/optional."""

    @app.default
    def main(foo: Annotated[ct.ResolvedFile | None, Parameter()]):
        pass

    with pytest.raises(ValidationError):
        app([str(tmp_path)], exit_on_error=False)  # a directory should be rejected


def test_types_existing_file_optional_validator_fires(app):
    """Validator-based type inside ``Annotated[... | None, Parameter()]``."""

    @app.default
    def main(foo: Annotated[ct.ExistingFile | None, Parameter()]):
        pass

    with pytest.raises(ValidationError):
        app(["this-file-does-not-exist"], exit_on_error=False)


def test_types_positive_int_optional_validator_fires(app):
    @app.default
    def main(foo: Annotated[ct.PositiveInt | None, Parameter()]):
        pass

    with pytest.raises(ValidationError):
        app(["-5"], exit_on_error=False)


def test_types_positive_int_optional_ok(app, assert_parse_args):
    @app.default
    def main(foo: Annotated[ct.PositiveInt | None, Parameter()]):
        pass

    assert_parse_args(main, "5", 5)


def test_types_hexuint_optional_converter_applies(app, assert_parse_args):
    @app.default
    def main(foo: Annotated[ct.HexUInt | None, Parameter()]):
        pass

    assert_parse_args(main, "0xff", 255)


def test_types_list_of_optional_resolved(app, assert_parse_args):
    """Converter applies element-wise through a list of the optional-annotated type."""

    @app.default
    def main(foo: list[Annotated[ct.ResolvedPath | None, Parameter()]]):
        pass

    assert_parse_args(main, ["a", "b"], [Path("a").resolve(), Path("b").resolve()])


def test_types_double_optional_annotated(app, assert_parse_args):
    """Doubly-wrapped Optional/Annotated nesting."""

    @app.default
    def main(foo: Annotated[Annotated[ct.ResolvedPath | None, Parameter()] | None, Parameter()]):
        pass

    assert_parse_args(main, "bar", Path("bar").resolve())


def test_types_outer_converter_overrides_inner(app, assert_parse_args):
    """An outer ``Parameter(converter=...)`` keeps higher priority than the inner one."""

    @app.default
    def main(foo: Annotated[ct.ResolvedPath | None, Parameter(converter=lambda type_, tokens: "OVERRIDDEN")]):
        pass

    assert_parse_args(main, "bar", "OVERRIDDEN")


def test_types_newtype_resolved_bare(app, assert_parse_args):
    """A ``NewType`` over a converter type keeps the converter.

    ``NewType`` over an ``Annotated`` alias is valid at runtime but flagged statically,
    hence the ``pyright: ignore`` comments.
    """
    MyPath = NewType("MyPath", ct.ResolvedPath)  # pyright: ignore[reportGeneralTypeIssues]

    @app.default
    def main(foo: MyPath):  # pyright: ignore[reportInvalidTypeForm]
        pass

    assert_parse_args(main, "bar", Path("bar").resolve())


def test_types_newtype_resolved_optional(app, assert_parse_args):
    """A ``NewType`` over a converter type, made optional, keeps the converter."""
    MyPath = NewType("MyPath", ct.ResolvedPath)  # pyright: ignore[reportGeneralTypeIssues]

    @app.default
    def main(foo: Annotated[Optional[MyPath], Parameter()]):  # pyright: ignore[reportInvalidTypeForm]
        pass

    assert_parse_args(main, "bar", Path("bar").resolve())


def test_types_nested_newtype_resolved_optional(app, assert_parse_args):
    """A ``NewType`` over a ``NewType`` over a converter type, made optional."""
    MyPath = NewType("MyPath", ct.ResolvedPath)  # pyright: ignore[reportGeneralTypeIssues]
    DeepPath = NewType("DeepPath", MyPath)  # pyright: ignore[reportGeneralTypeIssues]

    @app.default
    def main(foo: Annotated[Optional[DeepPath], Parameter()]):  # pyright: ignore[reportInvalidTypeForm]
        pass

    assert_parse_args(main, "bar", Path("bar").resolve())
