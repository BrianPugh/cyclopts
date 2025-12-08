from textwrap import dedent
from typing import Annotated

import pytest

from cyclopts import App, Group, Parameter, UnknownOptionError


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
    subapp = App(console=console, result_action="return_value")

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

    app = App(name="test_app", console=console, result_action="return_value")
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
        │ subapp       This is subapp's help.                                │
        │ --help (-h)  Display this message and exit.                        │
        │ --version    Display application version.                          │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected
    assert not queue


def test_meta_app_nested_subapp_help(nested_meta_app, console, queue):
    """
    Classical command chain
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
        Usage: test_app subapp COMMAND

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
        Usage: test_app subapp foo VALUE

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
    app.meta.group_parameters = Group("Global options", sort_key=0)

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
        │ --help (-h)  Display this message and exit.                        │
        │ --version    Display application version.                          │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Global options ───────────────────────────────────────────────────╮
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
        ╭─ Global options ───────────────────────────────────────────────────╮
        │ --flag1  [default: False]                                          │
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


def test_meta_app_help_inconsistency_with_argument_order(app, console):
    """Test for issue #551: Inconsistent help page display with different argument orders.

    The issue is that when meta app parameters come before the command name,
    the help display is different than when they come after the command name.
    Both should display the same help page for the foo command.
    """
    app["--help"].group = "Global options"
    app["--version"].group = "Global options"
    app.meta.group_parameters = Group("Global options", sort_key=0)

    @app.command
    def foo(loops: int, *, user: Annotated[str, Parameter(parse=False)]):
        print(f"Hello {user}")
        for i in range(loops):
            print(f"Looping! {i}")

    @app.meta.default
    def my_app_launcher(*tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)], user: str):
        command, bound, ignored = app.parse_args(tokens)
        return command(*bound.args, **bound.kwargs, user=user)

    expected = dedent(
        """\
        Usage: test_meta foo LOOPS

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  LOOPS --loops  [required]                                       │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Global options ───────────────────────────────────────────────────╮
        │ *  --user  [required]                                              │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    # Test help with --user before command
    with console.capture() as capture:
        app.meta(["--user", "test", "foo", "--help"], console=console)

    help_user_before_foo = capture.get()
    assert help_user_before_foo == expected

    # Test help with --user after command
    with console.capture() as capture:
        app.meta(["foo", "--user", "test", "--help"], console=console)

    help_user_after_foo = capture.get()

    assert help_user_after_foo == expected


def test_issue_680_nested_meta_command_resolution(app, queue):
    """Test for issue #680: Commands parsed at wrong level with multiple meta apps."""

    @app.meta.meta.default
    def meta_meta_default(
        *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
    ):
        queue.append("meta_meta_default")
        command, bound, _ignored = app.meta.parse_args(tokens)
        command(*bound.args, **bound.kwargs)

    @app.meta.default
    def meta_default(
        *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
        meta_param: str = "default",
    ):
        queue.append(f"meta_default({meta_param})")
        app(tokens)

    @app.default
    def default():
        queue.append("default")

    @app.command
    def command():
        queue.append("command")

    # Test 1: No command, no parameters
    queue.clear()
    app.meta.meta([])
    assert queue == ["meta_meta_default", "meta_default(default)", "default"]

    # Test 2: Command without meta parameter (this was the bug case)
    queue.clear()
    app.meta.meta(["command"])
    assert queue == ["meta_meta_default", "meta_default(default)", "command"]

    # Test 3: Command with meta parameter
    queue.clear()
    app.meta.meta(["--meta-param", "value", "command"])
    assert queue == ["meta_meta_default", "meta_default(value)", "command"]


def test_nested_meta_app_command_help(console):
    """Test that --help works for commands in nested meta-apps (issue-680)."""
    app = App(console=console, result_action="return_value")

    @app.meta.meta.default
    def meta_meta_default(
        *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
    ):
        command, bound, _ignored = app.meta.parse_args(tokens)
        command(*bound.args, **bound.kwargs)

    @app.meta.meta.command
    def foo(value: str):
        """Test command in nested meta-app.

        Parameters
        ----------
        value : str
            A test value.
        """
        pass

    @app.meta.default
    def meta_default(
        *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
        meta_param: str = "default",
    ):
        app(tokens)

    @app.default
    def default():
        """Default command."""
        pass

    @app.command
    def command():
        """Regular command."""
        pass

    # This should not raise a KeyError
    with console.capture() as capture:
        app.meta.meta(["foo", "--help"])

    actual = capture.get()

    # Should show help for foo command
    assert "foo" in actual.lower()
    assert "value" in actual.lower()
