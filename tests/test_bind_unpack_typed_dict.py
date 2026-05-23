"""Tests for PEP-692 ``**kwargs: Unpack[SomeTypedDict]`` support.

See https://github.com/BrianPugh/cyclopts/issues/817.
"""

import sys
from pathlib import Path
from typing import Annotated, TypedDict

import pytest

from cyclopts import MissingArgumentError, Parameter
from cyclopts.exceptions import UnknownOptionError

if sys.version_info < (3, 12):  # pragma: no cover
    pytest.skip("PEP 692 Unpack[TypedDict] for **kwargs requires Python 3.12+", allow_module_level=True)

from typing import NotRequired, Required, Unpack  # noqa: E402


class KwArgs(TypedDict, total=False):
    output_file: Path
    verbose: bool


class RequiredKwArgs(TypedDict):
    name: str
    count: NotRequired[int]


class MixedKwArgs(TypedDict, total=False):
    name: Required[str]
    count: int


def test_kwargs_unpack_typed_dict_basic(app, assert_parse_args):
    @app.default
    def run(*input_files: Path, **kwargs: Unpack[KwArgs]) -> None:
        pass

    assert_parse_args(
        run,
        "a.txt b.txt --output-file out.txt --verbose",
        Path("a.txt"),
        Path("b.txt"),
        output_file=Path("out.txt"),
        verbose=True,
    )


def test_kwargs_unpack_typed_dict_no_kwargs(app, assert_parse_args):
    @app.default
    def run(*input_files: Path, **kwargs: Unpack[KwArgs]) -> None:
        pass

    assert_parse_args(run, "a.txt b.txt", Path("a.txt"), Path("b.txt"))


def test_kwargs_unpack_typed_dict_only_one_field(app, assert_parse_args):
    @app.default
    def run(*input_files: Path, **kwargs: Unpack[KwArgs]) -> None:
        pass

    assert_parse_args(
        run,
        "a.txt --verbose",
        Path("a.txt"),
        verbose=True,
    )


def test_kwargs_unpack_typed_dict_rejects_unknown_option(app):
    @app.default
    def run(**kwargs: Unpack[KwArgs]) -> None:
        pass

    with pytest.raises(UnknownOptionError):
        app.parse_args("--unknown-flag value", print_error=False, exit_on_error=False)


def test_kwargs_unpack_typed_dict_required_field_missing(app):
    @app.default
    def run(**kwargs: Unpack[RequiredKwArgs]) -> None:
        pass

    with pytest.raises(MissingArgumentError):
        app.parse_args("", print_error=False, exit_on_error=False)


def test_kwargs_unpack_typed_dict_required_field_provided(app, assert_parse_args):
    @app.default
    def run(**kwargs: Unpack[RequiredKwArgs]) -> None:
        pass

    assert_parse_args(run, "--name alice", name="alice")
    assert_parse_args(run, "--name alice --count 3", name="alice", count=3)


def test_kwargs_unpack_typed_dict_mixed_required(app, assert_parse_args):
    """total=False overridden by Required[...] on individual fields."""

    @app.default
    def run(**kwargs: Unpack[MixedKwArgs]) -> None:
        pass

    assert_parse_args(run, "--name alice", name="alice")
    with pytest.raises(MissingArgumentError):
        app.parse_args("--count 3", print_error=False, exit_on_error=False)


def test_kwargs_unpack_typed_dict_annotated(app, assert_parse_args):
    """``Annotated[Unpack[K], ...]`` must be seen through, not treated as ``dict[str, Annotated[...]]``."""

    @app.default
    def run(**kwargs: Annotated[Unpack[KwArgs], Parameter(show=True)]) -> None:  # pyright: ignore[reportGeneralTypeIssues]
        pass

    assert_parse_args(run, "--verbose", verbose=True)


def test_kwargs_unpack_non_typeddict_raises(app):
    """``Unpack[X]`` where X is not a TypedDict should raise a clear TypeError."""

    class NotATypedDict:
        x: int

    with pytest.raises(TypeError, match="Unpack"):

        @app.default
        def run(**kwargs: Unpack[NotATypedDict]) -> None:  # pyright: ignore[reportGeneralTypeIssues]
            pass

        # Trigger argument-collection build:
        app.parse_args("", print_error=False, exit_on_error=False)


def test_kwargs_unpack_empty_typeddict_help(app, console):
    """Empty TypedDict should not render a blank Parameters row."""

    class Empty(TypedDict):
        pass

    @app.default
    def run(**kwargs: Unpack[Empty]) -> None:
        pass

    with console.capture() as capture:
        app("--help", console=console, exit_on_error=False)

    output = capture.get()
    assert "--[KEYWORD]" not in output
    # A blank "│ │" row from a nameless argument would appear inside a Parameters panel; ensure no Parameters panel at all.
    assert "Parameters" not in output
