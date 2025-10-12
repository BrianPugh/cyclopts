from textwrap import dedent

import pytest

from cyclopts.exceptions import ValidationError
from cyclopts.types import HexUInt, HexUInt8, HexUInt16, HexUInt32, HexUInt64, UInt8


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
    def default(color: list[tuple[UInt8, UInt8, UInt8]] | None = None):
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


@pytest.mark.parametrize(
    "type_hint, expected",
    [
        (HexUInt, "0xAF"),
        (HexUInt8, "0xAF"),
        (HexUInt16, "0x00AF"),
        (HexUInt32, "0x000000AF"),
        (HexUInt64, "0x00000000000000AF"),
    ],
)
def test_hexuint_help(app, console, type_hint, expected):
    @app.command
    def foo(a: type_hint = 0xAF):  # pyright: ignore[reportInvalidTypeForm]
        pass

    with console.capture() as capture:
        app.help_print("foo", console=console)

    actual = capture.get()

    assert expected in actual


def test_hexuint_help_no_default(app, console):
    """Do not show the default, do not error out.

    Checks for bug identified in:
        https://github.com/BrianPugh/cyclopts/issues/437
    """

    @app.command
    def foo(a: HexUInt32):
        pass

    with console.capture() as capture:
        app.help_print("foo", console=console)

    actual = capture.get()

    expected = dedent(
        """\
        Usage: test_types_number foo A

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  A --a  [required]                                               │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert expected == actual
