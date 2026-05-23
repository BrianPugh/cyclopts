"""Tests for PEP-692 ``**kwargs: Unpack[SomeTypedDict]`` support.

See https://github.com/BrianPugh/cyclopts/issues/817.
"""

import sys
from pathlib import Path
from typing import TypedDict

import pytest

if sys.version_info < (3, 12):  # pragma: no cover
    pytest.skip("PEP 692 Unpack[TypedDict] for **kwargs requires Python 3.12+", allow_module_level=True)

from typing import Unpack  # noqa: E402


class KwArgs(TypedDict, total=False):
    output_file: Path
    verbose: bool


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
