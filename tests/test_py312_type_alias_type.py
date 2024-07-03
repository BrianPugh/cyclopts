import sys
from typing import Annotated, Literal, TypeAlias

import pytest

from cyclopts.help import _get_choices

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


type FontSingleFormat = Literal["otf", "woff2", "ttf", "bdf", "pcf"]
type FontCollectionFormat = Literal["otc", "ttc"]
FontPixelFormat: TypeAlias = Literal["bmp"]


@pytest.mark.parametrize(
    "type_, expected",
    [
        (FontPixelFormat, "bmp"),
        (FontSingleFormat, "otf,woff2,ttf,bdf,pcf"),
        (FontSingleFormat | FontPixelFormat, "otf,woff2,ttf,bdf,pcf,bmp"),
        (FontSingleFormat | FontCollectionFormat, "otf,woff2,ttf,bdf,pcf,otc,ttc"),
        (FontSingleFormat | FontCollectionFormat | None, "otf,woff2,ttf,bdf,pcf,otc,ttc"),
        (list[FontSingleFormat | FontCollectionFormat] | None, "otf,woff2,ttf,bdf,pcf,otc,ttc"),
    ],
)
def test_py312_type_alias_type_help_get_choices(type_, expected):
    assert expected == _get_choices(type_, lambda x: x)
