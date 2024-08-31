from enum import Enum, auto
from textwrap import dedent
from typing import Annotated

import pytest

from cyclopts import App, Parameter, default_name_transform


@pytest.mark.parametrize(
    "before,after",
    [
        ("FOO", "foo"),
        ("_FOO", "foo"),
        ("_FOO_", "foo"),
        ("_F_O_O_", "f-o-o"),
    ],
)
def test_default_name_transform(before, after):
    assert default_name_transform(before) == after


def test_app_name_transform_default(app):
    @app.command
    def _F_O_O_():  # noqa: N802
        pass

    assert "f-o-o" in app


def test_app_name_transform_custom(app):
    def name_transform(s: str) -> str:
        return "my-custom-name-transform"

    app.name_transform = name_transform

    @app.command
    def foo():
        pass

    assert "my-custom-name-transform" in app


def test_subapp_name_transform_custom(app):
    """A subapp with an explicitly set ``name_transform`` should NOT inherit from parent."""

    def name_transform_1(s: str) -> str:
        return "my-custom-name-transform-1"

    def name_transform_2(s: str) -> str:
        return "my-custom-name-transform-2"

    app.name_transform = name_transform_1

    app.command(subapp := App(name="bar", name_transform=name_transform_2))

    @subapp.command
    def foo():
        pass

    assert "my-custom-name-transform-2" in subapp


def test_subapp_name_transform_custom_inherited(app):
    """A subapp without an explicitly set ``name_transform`` should inherit it from the first parent."""

    def name_transform(s: str) -> str:
        return "my-custom-name-transform"

    app.name_transform = name_transform

    app.command(subapp := App(name="bar"))

    @subapp.command
    def foo():
        pass

    assert "my-custom-name-transform" in subapp


def test_parameter_name_transform_default(app, assert_parse_args):
    @app.default
    def foo(*, b_a_r: int):
        pass

    assert_parse_args(foo, "--b-a-r 5", b_a_r=5)


def test_parameter_name_transform_custom(app, assert_parse_args):
    app.default_parameter = Parameter(name_transform=lambda s: s)

    @app.default
    def foo(*, b_a_r: int):
        pass

    assert_parse_args(foo, "--b_a_r 5", b_a_r=5)


def test_parameter_name_transform_custom_name_override(app, assert_parse_args):
    app.default_parameter = Parameter(name_transform=lambda s: s)

    @app.default
    def foo(*, b_a_r: Annotated[int, Parameter(name="--buzz")]):
        pass

    assert_parse_args(foo, "--buzz 5", b_a_r=5)


def test_parameter_name_transform_custom_enum(app, assert_parse_args):
    """name_transform should also be applied to enum options."""
    app.default_parameter = Parameter(name_transform=lambda s: s)

    class SoftwareEnvironment(Enum):
        DEV = auto()
        STAGING = auto()
        PROD = auto()
        _PROD_OLD = auto()

    @app.default
    def foo(*, b_a_r: SoftwareEnvironment = SoftwareEnvironment.STAGING):
        pass

    assert_parse_args(foo, "--b_a_r PROD", b_a_r=SoftwareEnvironment.PROD)


def test_parameter_name_transform_help(app, console):
    app.default_parameter = Parameter(name_transform=lambda s: s)

    @app.default
    def foo(*, b_a_r: int):
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: foo COMMAND [OPTIONS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help,-h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  --b_a_r  [required]                                             │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_parameter_name_transform_help_enum(app, console):
    """name_transform should also be applied to enum options on help page."""
    app.default_parameter = Parameter(name_transform=lambda s: s)

    class CompSciProblem(Enum):
        FIZZ = "bleep bloop blop"
        BUZZ = "blop bleep bloop"

    @app.command
    def cmd(
        foo: Annotated[CompSciProblem, Parameter(help="Docstring for foo.")] = CompSciProblem.FIZZ,
        bar: Annotated[CompSciProblem, Parameter(help="Docstring for bar.")] = CompSciProblem.BUZZ,
    ):
        pass

    with console.capture() as capture:
        app.help_print(["cmd"], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_name_transform cmd [ARGS] [OPTIONS]

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO,--foo  Docstring for foo. [choices: FIZZ,BUZZ] [default: FIZZ] │
        │ BAR,--bar  Docstring for bar. [choices: FIZZ,BUZZ] [default: BUZZ] │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected
