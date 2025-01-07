from typing import Optional

import pytest

from cyclopts.exceptions import ValidationError
from cyclopts.types import UInt8


def test_nested_annotated_validator(app, assert_parse_args):
    @app.default
    def default(color: tuple[UInt8, UInt8, UInt8] = (0x00, 0x00, 0x00)):
        pass

    assert_parse_args(default, "0x12 0x34 0x56", (0x12, 0x34, 0x56))

    with pytest.raises(ValidationError) as e:
        app.parse_args("100 200 300", exit_on_error=False)
    assert str(e.value) == 'Invalid value "300" for "COLOR". Must be <= 255.'

    with pytest.raises(ValidationError) as e:
        app.parse_args("--color 100 200 300", exit_on_error=False)
    assert str(e.value) == 'Invalid value "300" for "--color". Must be <= 255.'


def test_nested_list_annotated_validator(app, assert_parse_args):
    @app.default
    def default(color: Optional[list[tuple[UInt8, UInt8, UInt8]]] = None):
        pass

    assert_parse_args(
        default,
        "0x12 0x34 0x56 0x78 0x90 0xAB",
        [(0x12, 0x34, 0x56), (0x78, 0x90, 0xAB)],
    )

    with pytest.raises(ValidationError) as e:
        app.parse_args("100 200 300", exit_on_error=False)
    assert str(e.value) == 'Invalid value "300" for "COLOR". Must be <= 255.'

    with pytest.raises(ValidationError) as e:
        app.parse_args("--color 100 200 300", exit_on_error=False)
    assert str(e.value) == 'Invalid value "300" for "--color". Must be <= 255.'
