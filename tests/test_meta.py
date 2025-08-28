from textwrap import dedent
from typing import Annotated

import pytest

from cyclopts import App, Parameter, UnknownOptionError


@pytest.mark.parametrize(
    "cmd_str",
    [
        "1 --b 2 --c=c-value-manual --meta-flag",
        "1 --b=2 --c=c-value-manual --meta-flag",
        "1 --b=2 --c c-value-manual --meta-flag",
    ],
)
def test_meta_basic(app, cmd_str):
    @app.default
    def foo(a: int, b: int, c="c-value"):
        assert a == 1
        assert b == 2
        assert c == "c-value-manual"

    @app.meta.default
    def meta(*tokens: Annotated[str, Parameter(allow_leading_hyphen=True)], meta_flag: bool = False):
        assert meta_flag
        app(tokens)

    app.meta(cmd_str)


def test_meta_app_config_inheritance(app):
    app.config = ("foo", "bar")
    assert app.meta.config == ("foo", "bar")


@pytest.fixture
def queue():
    return []


@pytest.fixture
def nested_meta_app(queue, console):
    subapp = App(console=console)

    @subapp.meta.default
    def subapp_meta(*tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)]) -> None:
        """This is subapp's help."""
        queue.append("subapp meta")
        subapp(tokens)

    @subapp.command
    def foo(value: int) -> None:
        """Subapp foo help string.

        Parameters
        ----------
        value: int
            The value a user inputted.
        """
        queue.append(f"subapp foo body {value}")

    app = App(name="test_app", console=console)
    app.command(subapp.meta, name="subapp")

    @app.meta.default
    def meta(*tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)]):
        queue.append("root meta")
        app(tokens)

    return app


def test_meta_app_nested_root_help(nested_meta_app, console, queue):
    with console.capture() as capture:
        nested_meta_app.meta(["--help"])

    actual = capture.get()

    expected = dedent(
        """\
        Usage: test_app COMMAND

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ subapp     This is subapp's help.                                  │
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected
    assert not queue


def test_meta_app_nested_subapp_help(nested_meta_app, console, queue):
    """
    classical command chain
    app.meta -> app     -> subapp.meta -> subapp -> help
    0        -> MISSING -> 1           -> MISSING -> help

    hierarchy-command-chain.
    app      -> app.meta -> subapp -> subapp.meta -> help
    """
    with console.capture() as capture:
        nested_meta_app.meta(["subapp", "--help"])

    actual = capture.get()

    expected = dedent(
        """\
        Usage: test_app subapp COMMAND [ARGS]

        This is subapp's help.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ foo  Subapp foo help string.                                       │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected
    assert not queue


def test_meta_app_nested_subapp_foo_help(nested_meta_app, console, queue):
    with console.capture() as capture:
        nested_meta_app.meta(["subapp", "foo", "--help"])

    actual = capture.get()

    expected = dedent(
        """\
        Usage: test_app subapp foo [ARGS] [OPTIONS]

        Subapp foo help string.

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  VALUE --value  The value a user inputted. [required]            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected
    assert not queue


@pytest.mark.parametrize(
    "cmd_str,expected",
    [
        ("", ["root meta"]),
        ("subapp", ["root meta", "subapp meta"]),
        ("subapp foo 5", ["root meta", "subapp meta", "subapp foo body 5"]),
    ],
)
def test_meta_app_nested_exec(nested_meta_app, queue, cmd_str, expected):
    nested_meta_app.meta(cmd_str)
    assert queue == expected


def test_meta_app_inheriting_root_default_parameter(app, console):
    """Confirms that default_parameter gets inherited root_app->meta_app (as well as to subapps when a meta app is used)."""
    app.default_parameter = Parameter(negative=[])

    @app.meta.default
    def meta(
        *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
        flag1: bool = False,
    ):
        app(tokens)

    @app.command
    def foo(*, flag2: bool = False):
        pass

    with console.capture() as capture:
        app.meta(["--help"], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_meta COMMAND

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ foo                                                                │
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ --flag1  [default: False]                                          │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected

    with console.capture() as capture:
        app.meta(["foo", "--help"], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_meta foo [OPTIONS]

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ --flag2  [default: False]                                          │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_nested_meta_app_inheriting_root_default_parameter(app, console):
    app.default_parameter = Parameter(negative=[])

    @app.meta.default
    def meta(
        *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
        flag1: bool = False,
    ):
        return app(tokens)

    foo_app = App(name="foo")

    @foo_app.meta.default
    def foo_meta(
        *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
        flag2: bool = False,
    ):
        return foo_app(tokens)

    @foo_app.default
    def foo_app_default(
        *,
        flag3: bool = False,
    ):
        return flag3

    app.command(foo_app.meta, name="foo")

    assert app.meta("foo --flag3") is True

    with pytest.raises(UnknownOptionError):
        app.meta("foo --no-flag3", exit_on_error=False)
