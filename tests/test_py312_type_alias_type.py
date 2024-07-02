import sys
from typing import Annotated, Literal, TypeAlias

import pytest

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
