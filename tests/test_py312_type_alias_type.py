import sys

import pytest

if sys.version_info >= (3, 12):
    from typing import Annotated, Literal, TypeAlias

    FontSize: TypeAlias = Literal[10, 12, 16]
    type BoxSize = Literal[10, 12, 16]


@pytest.mark.skipif(sys.version_info < (3, 11), reason="Typing")
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
