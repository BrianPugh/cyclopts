from enum import Enum
from typing import Annotated, Literal, TypeAlias

import pytest

from cyclopts import Parameter
from cyclopts.argument import _get_choices_from_hint

FontSize: TypeAlias = Literal[10, 12, 16]
type BoxSize = Literal[10, 12, 16]


def test_py312_type_alias_type(app, assert_parse_args):
    """Support for python3.12 :obj:`TypeAliasType`.

    https://github.com/BrianPugh/cyclopts/issues/190
    """

    @app.default
    def main(
        font_size: FontSize,
        box_size: BoxSize,
        box_size_2: Annotated[BoxSize, "foo"],
    ):
        pass

    assert_parse_args(main, "10 12 16", 10, 12, 16)


class CompSciProblem(Enum):
    fizz = "bleep bloop blop"
    buzz = "blop bleep bloop"


type AnnotatedEnum = Annotated[CompSciProblem, Parameter(name="foo")]
type AnnotatedOptionalEnum = Annotated[CompSciProblem | None, Parameter(name="foo")]

type FontSingleFormat = Literal["otf", "woff2", "ttf", "bdf", "pcf"]
type FontCollectionFormat = Literal["otc", "ttc"]
FontPixelFormat: TypeAlias = Literal["bmp"]


@pytest.mark.parametrize(
    "type_, expected",
    [
        (AnnotatedEnum, ["fizz", "buzz"]),
        (AnnotatedOptionalEnum, ["fizz", "buzz"]),
        (FontPixelFormat, ["bmp"]),
        (FontSingleFormat, ["otf", "woff2", "ttf", "bdf", "pcf"]),
        (FontSingleFormat | FontPixelFormat, ["otf", "woff2", "ttf", "bdf", "pcf", "bmp"]),
        (FontSingleFormat | FontCollectionFormat, ["otf", "woff2", "ttf", "bdf", "pcf", "otc", "ttc"]),
        (FontSingleFormat | FontCollectionFormat | None, ["otf", "woff2", "ttf", "bdf", "pcf", "otc", "ttc"]),
        (list[FontSingleFormat | FontCollectionFormat] | None, ["otf", "woff2", "ttf", "bdf", "pcf", "otc", "ttc"]),
    ],
)
def test_py312_type_alias_type_help_get_choices(type_, expected):
    assert expected == _get_choices_from_hint(type_, lambda x: x)


type Numbers = tuple[int, str]


def test_py312_type_alias_type_tuple_token_count(app, assert_parse_args):
    """Ensure that TypeAliasType can handle multi-token types.

    https://github.com/BrianPugh/cyclopts/issues/413
    """

    @app.default
    def main(foo: Numbers):
        pass

    assert_parse_args(main, "1 one", (1, "one"))
