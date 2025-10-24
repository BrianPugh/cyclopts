from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from functools import partial
from textwrap import dedent
from typing import Annotated, Literal

import pytest

from cyclopts import App, Group, Parameter
from cyclopts.argument import ArgumentCollection
from cyclopts.exceptions import CoercionError, MissingArgumentError
from cyclopts.group_extractors import RegisteredCommand
from cyclopts.help import (
    HelpPanel,
    create_parameter_help_panel,
    format_command_entries,
    format_usage,
)
from cyclopts.help.formatters import DefaultFormatter, PlainFormatter


@pytest.fixture
def app():
    return App(
        name="app",
        help="App Help String Line 1.",
        result_action="return_value",
    )


def test_empty_help_panel_rich_silent(console):
    help_panel = HelpPanel(format="command", title="test")
    formatter = DefaultFormatter()
    rendered = formatter._render_panel(help_panel, console, console.options)

    with console.capture() as capture:
        console.print(rendered)

    actual = capture.get()
    assert actual == ""


def test_help_mutable_default(app):
    """Ensures it doesn't crash; see issue #215."""

    @app.default
    def main(users: list[str] = ["a", "b"]) -> None:  # noqa: B006
        print(users)

    app(["--help"])


def test_help_default_action(app, console):
    """No command should default to help."""
    with console.capture() as capture:
        app([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app

        App Help String Line 1.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_custom_usage(app, console):
    app.usage = "My custom usage."
    with console.capture() as capture:
        app([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        My custom usage.

        App Help String Line 1.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_custom_usage_subapp(app, console):
    """Intentionally do not print --help/--version flags in subapp help."""
    app.command(App(name="foo", usage="My custom usage."))

    with console.capture() as capture:
        app(["foo", "--help"], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        My custom usage.

        """
    )
    assert actual == expected


def test_help_default_help_flags(console):
    """Standard help flags."""
    app = App(name="app", help="App Help String Line 1.", result_action="return_value")
    with console.capture() as capture:
        app(["--help"], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app

        App Help String Line 1.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_help_format_usage_empty(console):
    app = App(
        name="app",
        help="App Help String Line 1.",
        help_flags=[],
        version_flags=[],
    )

    with console.capture() as capture:
        console.print(format_usage(app, []))
    actual = capture.get()
    assert actual == "Usage: app\n\n"


def test_help_format_usage_command(app, console):
    @app.command
    def foo():
        pass

    with console.capture() as capture:
        console.print(format_usage(app, []))
    actual = capture.get()
    assert actual == "Usage: app COMMAND\n\n"


def test_format_commands_docstring(app, console):
    @app.command
    def foo():
        """Docstring for foo.

        This should not be shown.
        """

    panel = HelpPanel(title="Commands", format="command")
    panel.entries.extend(format_command_entries((RegisteredCommand(("foo",), app["foo"]),), format="restructuredtext"))
    formatter = DefaultFormatter()
    rendered = formatter._render_panel(panel, console, console.options)
    with console.capture() as capture:
        console.print(rendered)

    actual = capture.get()
    assert actual == (
        "╭─ Commands ─────────────────────────────────────────────────────────╮\n"
        "│ foo  Docstring for foo.                                            │\n"
        "╰────────────────────────────────────────────────────────────────────╯\n"
    )


def test_format_commands_docstring_multi_line_pep0257(app, console):
    """
    PEP-0257 says that the short_description and long_description should be separated by an empty newline.
    We hijack the docstring parsing a little bit to have the following properties:
        * The first block of text is ALWAYS the short-description.
        * There cannot be a long-description without a short-description.

    See:
        * https://github.com/BrianPugh/cyclopts/issues/74
        * https://github.com/BrianPugh/cyclopts/issues/393
        * https://github.com/BrianPugh/cyclopts/issues/402
    """

    @app.command
    def foo():
        """
        This function doesn't have a
        long description.
        """  # noqa: D404

    panel = HelpPanel(title="Commands", format="command")
    panel.entries.extend(format_command_entries((RegisteredCommand(("foo",), app["foo"]),), format="restructuredtext"))
    formatter = DefaultFormatter()
    rendered = formatter._render_panel(panel, console, console.options)
    with console.capture() as capture:
        console.print(rendered)

    actual = capture.get()
    assert actual == dedent(
        """\
        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ foo  This function doesn't have a long description.                │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )


def test_format_commands_no_show(app, console, assert_parse_args):
    @app.command
    def foo():
        """Docstring for foo."""
        pass

    @app.command(show=False)
    def bar():
        """Should not be shown."""
        pass

    assert_parse_args(foo, "foo")
    assert_parse_args(bar, "bar")

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app COMMAND

        App Help String Line 1.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ foo        Docstring for foo.                                      │
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_format_commands_explicit_help(app, console):
    @app.command(help="Docstring for foo.")
    def foo():
        """Should not be shown."""
        pass

    panel = HelpPanel(title="Commands", format="command")
    panel.entries.extend(format_command_entries((RegisteredCommand(("foo",), app["foo"]),), format="restructuredtext"))
    formatter = DefaultFormatter()
    rendered = formatter._render_panel(panel, console, console.options)
    with console.capture() as capture:
        console.print(rendered)

    actual = capture.get()
    assert actual == (
        "╭─ Commands ─────────────────────────────────────────────────────────╮\n"
        "│ foo  Docstring for foo.                                            │\n"
        "╰────────────────────────────────────────────────────────────────────╯\n"
    )


def test_format_commands_explicit_name(app, console):
    @app.command(name="bar")
    def foo():
        """Docstring for bar.

        This should not be shown.
        """
        pass

    panel = HelpPanel(title="Commands", format="command")
    panel.entries.extend(format_command_entries((RegisteredCommand(("bar",), app["bar"]),), format="restructuredtext"))
    formatter = DefaultFormatter()
    rendered = formatter._render_panel(panel, console, console.options)
    with console.capture() as capture:
        console.print(rendered)

    actual = capture.get()
    assert actual == (
        "╭─ Commands ─────────────────────────────────────────────────────────╮\n"
        "│ bar  Docstring for bar.                                            │\n"
        "╰────────────────────────────────────────────────────────────────────╯\n"
    )


def test_help_functools_partial_1(app, console):
    def foo(a: int, b: int, c: int):
        """Docstring for foo."""

    partial_foo = partial(foo, c=3)
    app.command(partial_foo)

    with console.capture() as capture:
        app.help_print(console=console)
    actual = capture.get()
    expected = dedent(
        """\
        Usage: app COMMAND

        App Help String Line 1.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ foo        Docstring for foo.                                      │
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_functools_partial_2(app, console):
    """Test help docstring resolution for :class:`functools.partial` functions.

    The argument ``c`` with ``parse=False`` should not be shown in the help page.

    The argument ``b`` should be shown with its :class:`functools.partial` default value.
    """

    def foo(a: int, b: int, c: Annotated[int, Parameter(parse=False)]):
        """Docstring for foo.

        Parameters
        ----------
        a: int
            Docstring for a.
        b: int
            Docstring for b.
        c: int
            Docstring for c.
        """

    partial_foo = partial(foo, b=2, c=3)
    app.command(partial_foo)

    with console.capture() as capture:
        app.help_print("foo", console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app foo [OPTIONS] A

        Docstring for foo.

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  A --a  Docstring for a. [required]                              │
        │    --b    Docstring for b. [default: 2]                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_empty(console):
    app = App(name="foo", version_flags=[], help_flags=[])

    with console.capture() as capture:
        app.help_print(console=console)
    actual = capture.get()

    assert actual == "Usage: foo\n\n"


def test_format_choices_rich_format(app, console, assert_parse_args):
    app.help_format = "rich"

    @app.default
    def foo(region: Literal["us", "ca"]):
        """Docstring for foo."""
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app REGION

        App Help String Line 1.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  REGION --region  [choices: us, ca] [required]                   │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


@pytest.fixture
def capture_format_group_parameters(console, default_function_groups):
    def inner(cmd):
        argument_collection = ArgumentCollection._from_callable(
            cmd,
            None,
            parse_docstring=True,
        )

        with console.capture() as capture:
            group = argument_collection.groups[0]
            group_argument_collection = argument_collection.filter_by(group=group)
            panel = create_parameter_help_panel(group, group_argument_collection, "restructuredtext")
            formatter = DefaultFormatter()
            rendered = formatter._render_panel(panel, console, console.options)
            console.print(rendered)

        return capture.get()

    return inner


def test_help_format_group_parameters_empty(capture_format_group_parameters):
    def cmd(
        foo: Annotated[str, Parameter(show=False)],
    ):
        pass

    actual = capture_format_group_parameters(cmd)
    expected = ""
    assert actual == expected


def test_help_format_group_parameters(capture_format_group_parameters):
    def cmd(
        foo: Annotated[str, Parameter(help="Docstring for foo.")],
        bar: Annotated[str, Parameter(help="Docstring for bar.")],
    ):
        pass

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  FOO --foo  Docstring for foo. [required]                        │
        │ *  BAR --bar  Docstring for bar. [required]                        │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_short_name(capture_format_group_parameters):
    def cmd(
        foo: Annotated[str, Parameter(name=["--foo", "-f"], help="Docstring for foo.")],
    ):
        pass

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  FOO --foo -f  Docstring for foo. [required]                     │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_from_docstring(capture_format_group_parameters):
    def cmd(foo: str, bar: str):
        """

        Parameters
        ----------
        foo: str
            Docstring for foo.
        bar: str
            Docstring for bar.
        """
        pass

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  FOO --foo  Docstring for foo. [required]                        │
        │ *  BAR --bar  Docstring for bar. [required]                        │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_sphinx_directives(capture_format_group_parameters):
    def cmd(foo: str, bar: float = 1.0, baz: int = 5):
        """
        Command with Sphinx directives.

        Parameters
        ----------
        foo: str
            Foo parameter
        bar: float
            Bar parameter

            .. versionadded:: 0.47
        baz: int
            Baz parameter

            .. deprecated:: 2.0
                Use something else instead
        """

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  FOO --foo  Foo parameter [required]                             │
        │    BAR --bar  Bar parameter [Added in v0.47] [default: 1.0]        │
        │    BAZ --baz  Baz parameter [⚠ Deprecated in v2.0] Use something   │
        │               else instead [default: 5]                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_sphinx_versionchanged(capture_format_group_parameters):
    def cmd(foo: str):
        """
        Command with versionchanged directive.

        Parameters
        ----------
        foo: str
            Foo parameter

            .. versionchanged:: 1.5
        """

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  FOO --foo  Foo parameter [Changed in v1.5] [required]           │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_sphinx_note_warning_seealso(capture_format_group_parameters):
    def cmd(foo: str, bar: str, baz: str):
        """
        Command with note, warning, and seealso directives.

        Parameters
        ----------
        foo: str
            Foo parameter

            .. note:: This is important
        bar: str
            Bar parameter

            .. warning:: Be careful here
        baz: str
            Baz parameter

            .. seealso:: Related function
        """

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  FOO --foo  Foo parameter                                        │
        │                                                                    │
        │               Note: This is important [required]                   │
        │ *  BAR --bar  Bar parameter                                        │
        │                                                                    │
        │               ⚠ Warning: Be careful here [required]                │
        │ *  BAZ --baz  Baz parameter                                        │
        │                                                                    │
        │               See also: Related function [required]                │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_sphinx_multiple_directives(capture_format_group_parameters):
    def cmd(foo: str):
        """
        Command with multiple directives on one parameter.

        Parameters
        ----------
        foo: str
            Foo parameter

            .. versionadded:: 1.0

            .. versionchanged:: 2.0

            .. note:: Important note
        """

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  FOO --foo  Foo parameter [Added in v1.0] [Changed in v2.0]      │
        │                                                                    │
        │               Note: Important note [required]                      │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_sphinx_deprecated_no_content(capture_format_group_parameters):
    def cmd(foo: str):
        """
        Command with deprecated directive without content.

        Parameters
        ----------
        foo: str
            Foo parameter

            .. deprecated:: 3.0
        """

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  FOO --foo  Foo parameter [⚠ Deprecated in v3.0] [required]      │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_bool_flag(capture_format_group_parameters):
    def cmd(
        foo: Annotated[bool, Parameter(help="Docstring for foo.")] = True,
    ):
        pass

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO --foo --no-foo  Docstring for foo. [default: True]             │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


@pytest.mark.parametrize("negative_str", ["--yesnt-foo", "yesnt-foo"])
def test_help_format_group_parameters_bool_flag_custom_negative(capture_format_group_parameters, negative_str):
    def cmd(
        foo: Annotated[bool, Parameter(negative=negative_str, help="Docstring for foo.")] = True,
    ):
        pass

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO --foo --yesnt-foo  Docstring for foo. [default: True]          │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_list_flag(capture_format_group_parameters):
    def cmd(
        foo: Annotated[list[int] | None, Parameter(help="Docstring for foo.")] = None,
    ):
        pass

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO --foo --empty-foo  Docstring for foo.                          │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_defaults(capture_format_group_parameters):
    def cmd(
        foo: Annotated[str, Parameter(help="Docstring for foo.")] = "fizz",
        bar: Annotated[str, Parameter(help="Docstring for bar.")] = "buzz",
    ):
        pass

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO --foo  Docstring for foo. [default: fizz]                      │
        │ BAR --bar  Docstring for bar. [default: buzz]                      │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_defaults_no_show(capture_format_group_parameters):
    def cmd(
        foo: Annotated[str, Parameter(show_default=False, help="Docstring for foo.")] = "fizz",
        bar: Annotated[str, Parameter(help="Docstring for bar.")] = "buzz",
    ):
        pass

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO --foo  Docstring for foo.                                      │
        │ BAR --bar  Docstring for bar. [default: buzz]                      │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_dataclass_default_parameter_negative_propagation(app, console):
    app.default_parameter = Parameter(negative=())

    @Parameter(name="*")
    @dataclass
    class Common:
        force: bool

    @app.default
    def default(common: Common):
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app FORCE

        App Help String Line 1.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  FORCE --force  [required]                                       │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_dataclass_decorated_parameter_negative_propagation(app, console):
    @Parameter(name="*", negative=())
    @dataclass
    class Common:
        force: bool

    @app.default
    def default(common: Common):
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app FORCE

        App Help String Line 1.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  FORCE --force  [required]                                       │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_choices_literal_no_show(capture_format_group_parameters):
    def cmd(
        foo: Annotated[Literal["fizz", "buzz"], Parameter(show_choices=False, help="Docstring for foo.")] = "fizz",
        bar: Annotated[Literal["fizz", "buzz"], Parameter(help="Docstring for bar.")] = "buzz",
    ):
        pass

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO --foo  Docstring for foo. [default: fizz]                      │
        │ BAR --bar  Docstring for bar. [choices: fizz, buzz] [default:      │
        │            buzz]                                                   │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_choices_literal_union(capture_format_group_parameters):
    def cmd(
        foo: Annotated[int | Literal["fizz", "buzz"] | Literal["bar"], Parameter(help="Docstring for foo.")] = "fizz",
    ):
        pass

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO --foo  Docstring for foo. [choices: fizz, buzz, bar] [default: │
        │            fizz]                                                   │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_choices_literal_union_python310_syntax_0(capture_format_group_parameters):
    def cmd(
        foo: Annotated[
            Literal["fizz", "buzz"] | Literal["bar"], Parameter(help="Docstring for foo.")  # pyright: ignore
        ] = "fizz",
    ):
        pass

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO --foo  Docstring for foo. [choices: fizz, buzz, bar] [default: │
        │            fizz]                                                   │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_choices_literal_union_python310_syntax_1(capture_format_group_parameters):
    def cmd(foo: Literal["fizz", "buzz"] | Literal["bar"] = "fizz"):  # pyright: ignore
        pass

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO --foo  [choices: fizz, buzz, bar] [default: fizz]              │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_choices_enum(capture_format_group_parameters):
    class CompSciProblem(Enum):
        fizz = "bleep bloop blop"
        buzz = "blop bleep bloop"

    def cmd(
        foo: Annotated[CompSciProblem, Parameter(help="Docstring for foo.")] = CompSciProblem.fizz,
        bar: Annotated[CompSciProblem, Parameter(help="Docstring for bar.")] = CompSciProblem.buzz,
    ):
        pass

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO --foo  Docstring for foo. [choices: fizz, buzz] [default:      │
        │            fizz]                                                   │
        │ BAR --bar  Docstring for bar. [choices: fizz, buzz] [default:      │
        │            buzz]                                                   │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_choices_enum_list(capture_format_group_parameters):
    class CompSciProblem(Enum):
        fizz = "bleep bloop blop"
        buzz = "blop bleep bloop"

        fizz_alias = fizz

    def cmd(
        foo: Annotated[
            list[CompSciProblem] | None,  # pyright: ignore
            Parameter(help="Docstring for foo.", negative_iterable=(), show_default=False, show_choices=True),
        ] = None,
    ):
        pass

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO --foo  Docstring for foo. [choices: fizz, buzz, fizz-alias]    │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_choices_enum_list_typing(capture_format_group_parameters):
    class CompSciProblem(Enum):
        fizz = "bleep bloop blop"
        buzz = "blop bleep bloop"

    def cmd(
        foo: Annotated[
            list[CompSciProblem] | None,
            Parameter(help="Docstring for foo.", negative_iterable=(), show_default=False, show_choices=True),
        ] = None,
    ):
        pass

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO --foo  Docstring for foo. [choices: fizz, buzz]                │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_choices_enum_sequence(capture_format_group_parameters):
    class CompSciProblem(Enum):
        fizz = "bleep bloop blop"
        buzz = "blop bleep bloop"

    def cmd(
        foo: Annotated[
            Sequence[CompSciProblem] | None,  # pyright: ignore
            Parameter(help="Docstring for foo.", negative_iterable=(), show_default=False, show_choices=True),
        ] = None,
    ):
        pass

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO --foo  Docstring for foo. [choices: fizz, buzz]                │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_choices_literal_sequence(capture_format_group_parameters):
    def cmd(
        steps_to_skip: Annotated[
            Sequence[Literal["build", "deploy"]] | None,  # pyright: ignore
            Parameter(help="Docstring for steps_to_skip.", negative_iterable=(), show_default=False, show_choices=True),
        ] = None,
    ):
        pass

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ STEPS-TO-SKIP      Docstring for steps_to_skip. [choices: build,   │
        │   --steps-to-skip  deploy]                                         │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    print(expected)
    assert actual == expected


def test_help_format_group_parameters_choices_literal_set(capture_format_group_parameters):
    def cmd(
        steps_to_skip: Annotated[
            set[Literal["build", "deploy"]] | None,  # pyright: ignore
            Parameter(help="Docstring for steps_to_skip.", negative_iterable=(), show_default=False, show_choices=True),
        ] = None,
    ):
        pass

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ STEPS-TO-SKIP      Docstring for steps_to_skip. [choices: build,   │
        │   --steps-to-skip  deploy]                                         │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    print(expected)
    assert actual == expected


def test_help_parameter_string_annotation(capture_format_group_parameters):
    def cmd(number: "Annotated[int,Parameter(name=['--number','-n'])]"):
        """Print number.

        Args:
            number (int): A number to print.
        """
        pass

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  NUMBER --number -n  A number to print. [required]               │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    print(actual)
    print(expected)
    assert actual == expected


def test_help_format_group_parameters_choices_literal_set_typing(capture_format_group_parameters):
    def cmd(
        steps_to_skip: Annotated[
            set[Literal["build", "deploy"]] | None,
            Parameter(help="Docstring for steps_to_skip.", negative_iterable=(), show_default=False, show_choices=True),
        ] = None,
    ):
        pass

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ STEPS-TO-SKIP      Docstring for steps_to_skip. [choices: build,   │
        │   --steps-to-skip  deploy]                                         │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_choices_literal_tuple(capture_format_group_parameters):
    def cmd(
        steps_to_skip: Annotated[
            tuple[Literal["build", "deploy"]] | None,  # pyright: ignore
            Parameter(help="Docstring for steps_to_skip.", negative_iterable=(), show_default=False, show_choices=True),
        ] = None,
    ):
        pass

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ STEPS-TO-SKIP      Docstring for steps_to_skip. [choices: build,   │
        │   --steps-to-skip  deploy]                                         │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    print(actual)
    assert actual == expected


def test_help_format_group_parameters_choices_literal_tuple_typing(capture_format_group_parameters):
    def cmd(
        steps_to_skip: Annotated[
            tuple[Literal["build", "deploy"]],
            Parameter(help="Docstring for steps_to_skip.", negative_iterable=(), show_choices=True),
        ] = ("build",),
    ):
        pass

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ STEPS-TO-SKIP      Docstring for steps_to_skip. [choices: build,   │
        │   --steps-to-skip  deploy] [default: ('build',)]                   │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_choices_literal_tuple_variadic_typing(capture_format_group_parameters):
    def cmd(
        steps_to_skip: Annotated[
            tuple[Literal["build", "deploy"], ...],
            Parameter(help="Docstring for steps_to_skip.", negative_iterable=(), show_choices=True),
        ] = (),
    ):
        pass

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ STEPS-TO-SKIP      Docstring for steps_to_skip. [choices: build,   │
        │   --steps-to-skip  deploy] [default: ()]                           │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_choices_literal_tuple_variadic(capture_format_group_parameters):
    def cmd(
        steps_to_skip: Annotated[
            tuple[Literal["build", "deploy"], ...],  # pyright: ignore
            Parameter(help="Docstring for steps_to_skip.", negative_iterable=(), show_choices=True),
        ] = ("build",),
    ):
        pass

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ STEPS-TO-SKIP      Docstring for steps_to_skip. [choices: build,   │
        │   --steps-to-skip  deploy] [default: ('build',)]                   │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    print(actual)
    assert actual == expected


def test_help_format_group_parameters_env_var(capture_format_group_parameters):
    def cmd(
        foo: Annotated[int, Parameter(env_var=["FOO", "BAR"], help="Docstring for foo.")] = 123,
    ):
        pass

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO --foo  Docstring for foo. [env var: FOO, BAR] [default: 123]   │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_print_function(app, console):
    @app.command(help="Cmd help string.")
    def cmd(
        foo: Annotated[str, Parameter(help="Docstring for foo.")],
        *,
        bar: Annotated[str, Parameter(help="Docstring for bar.")],
    ):
        pass

    with console.capture() as capture:
        app.help_print(["cmd"], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app cmd --bar STR FOO

        Cmd help string.

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  FOO --foo  Docstring for foo. [required]                        │
        │ *  --bar      Docstring for bar. [required]                        │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_print_parameter_required(app, console):
    """
    Notes
    -----
        * The default value should not show up in the help-page.
    """

    @app.command(help="Cmd help string.")
    def cmd(
        foo: Annotated[str, Parameter(required=False, help="Docstring for foo.")],
        *,
        bar: Annotated[str, Parameter(required=True, help="Docstring for bar.")] = "some-default-value",
    ):
        pass

    with console.capture() as capture:
        app.help_print(["cmd"], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app cmd --bar STR [ARGS]

        Cmd help string.

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │    FOO --foo  Docstring for foo.                                   │
        │ *  --bar      Docstring for bar. [required]                        │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected

    with pytest.raises(MissingArgumentError):
        app.parse_args("cmd value1", exit_on_error=False)


def test_help_print_function_defaults(app, console):
    @app.command(help="Cmd help string.")
    def cmd(
        *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
        bar: Annotated[str, Parameter(help="Docstring for bar.")] = "bar-value",
        baz: Annotated[str, Parameter(help="Docstring for bar.", env_var="BAZ")] = "baz-value",
    ):
        pass

    with console.capture() as capture:
        app.help_print(["cmd"], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app cmd [OPTIONS]

        Cmd help string.

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ --bar  Docstring for bar. [default: bar-value]                     │
        │ --baz  Docstring for bar. [env var: BAZ] [default: baz-value]      │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_print_function_no_parse(app, console):
    @app.command(help="Cmd help string.")
    def cmd(
        foo: Annotated[str, Parameter(help="Docstring for foo.")],
        *,
        bar: Annotated[str, Parameter(parse=False)],
    ):
        pass

    with console.capture() as capture:
        app.help_print(["cmd"], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app cmd FOO

        Cmd help string.

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  FOO --foo  Docstring for foo. [required]                        │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_print_parameter_group_description(app, console):
    @app.command(group_parameters=Group("Custom Title", help="Parameter description."))
    def cmd(
        foo: Annotated[str, Parameter(help="Docstring for foo.")],
        *,
        bar: Annotated[str, Parameter(parse=False)],
    ):
        pass

    with console.capture() as capture:
        app.help_print(["cmd"], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app cmd FOO

        ╭─ Custom Title ─────────────────────────────────────────────────────╮
        │ Parameter description.                                             │
        │                                                                    │
        │ *  FOO --foo  Docstring for foo. [required]                        │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_help_print_parameter_group_no_show(app, console):
    no_show_group = Group("Custom Title", help="Parameter description.", show=False)

    @app.command
    def cmd(
        foo: Annotated[str, Parameter(help="Docstring for foo.")],
        bar: Annotated[str, Parameter(help="Docstring for foo.", group=no_show_group)],
    ):
        pass

    with console.capture() as capture:
        app.help_print(["cmd"], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app cmd FOO BAR

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  FOO --foo  Docstring for foo. [required]                        │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_help_print_command_group_description(app, console):
    @app.command(group=Group("Custom Title", help="Command description."))
    def cmd(
        foo: Annotated[str, Parameter(help="Docstring for foo.")],
        *,
        bar: Annotated[str, Parameter(parse=False)],
    ):
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app COMMAND

        App Help String Line 1.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Custom Title ─────────────────────────────────────────────────────╮
        │ Command description.                                               │
        │                                                                    │
        │ cmd                                                                │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_help_print_command_group_no_show(app, console):
    no_show_group = Group("Custom Title", show=False)

    @app.command(group=no_show_group)
    def cmd1():
        pass

    @app.command()
    def cmd2():
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app COMMAND

        App Help String Line 1.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ cmd2                                                               │
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_help_print_combined_parameter_command_group(app, console):
    group = Group("Custom Title")

    app["--help"].group = group

    @app.default
    def default(value1: Annotated[int, Parameter(group=group)]):
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app VALUE1

        App Help String Line 1.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Custom Title ─────────────────────────────────────────────────────╮
        │ *  VALUE1 --value1  [required]                                     │
        │    --help -h        Display this message and exit.                 │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_help_print_commands(app, console):
    @app.command(help="Cmd1 help string.")
    def cmd1():
        pass

    @app.command(help="Cmd2 help string.")
    def cmd2():
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app COMMAND

        App Help String Line 1.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ cmd1       Cmd1 help string.                                       │
        │ cmd2       Cmd2 help string.                                       │
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_print_commands_group_sort_key(app, console):
    @app.command(group=Group("4", sort_key=5))
    def cmd1():
        pass

    @app.command(group=Group("3", sort_key=lambda x: 10))
    def cmd2():
        pass

    @app.command(group=Group("2", sort_key=lambda x: None))
    def cmd3():
        pass

    @app.command(group=Group("1"))
    def cmd4():
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app COMMAND

        App Help String Line 1.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ 4 ────────────────────────────────────────────────────────────────╮
        │ cmd1                                                               │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ 3 ────────────────────────────────────────────────────────────────╮
        │ cmd2                                                               │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ 1 ────────────────────────────────────────────────────────────────╮
        │ cmd4                                                               │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ 2 ────────────────────────────────────────────────────────────────╮
        │ cmd3                                                               │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_print_commands_and_function(app, console):
    @app.command(help="Cmd1 help string.")
    def cmd1():
        pass

    @app.command(help="Cmd2 help string.")
    def cmd2():
        pass

    @app.default()
    def default(
        foo: Annotated[str, Parameter(help="Docstring for foo.")],
        *,
        bar: Annotated[str, Parameter(help="Docstring for bar.")],
    ):
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app COMMAND --bar STR FOO

        App Help String Line 1.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ cmd1       Cmd1 help string.                                       │
        │ cmd2       Cmd2 help string.                                       │
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  FOO --foo  Docstring for foo. [required]                        │
        │ *  --bar      Docstring for bar. [required]                        │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_print_commands_special_flag_reassign(app, console):
    app["--help"].group = "Admin"
    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app

        App Help String Line 1.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Admin ────────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_print_parameters_no_negative_from_default_parameter(app, console):
    app.default_parameter = Parameter(negative=())

    @app.command
    def foo(*, flag: bool):
        pass

    with console.capture() as capture:
        app.help_print(["foo"], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app foo --flag BOOL

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  --flag  [required]                                              │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_print_commands_plus_meta(console):
    app = App(
        name="app",
        help_flags=[],
        version_flags=[],
        help="App Help String Line 1.",
    )

    app.meta.group_arguments = "Session Arguments"
    app.meta.group_parameters = "Session Parameters"

    @app.command(help="Cmd1 help string.")
    def cmd1():
        pass

    @app.meta.command(help="Meta cmd help string.")
    def meta_cmd():
        pass

    @app.command(help="Cmd2 help string.")
    def cmd2():
        pass

    @app.meta.default
    def main(
        *tokens: Annotated[str, Parameter(show=False)],
        hostname: Annotated[str, Parameter(help="Hostname to connect to.")],
    ):
        pass

    app.meta.help_flags = "--help"
    app.meta["--help"].group = "Admin"

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app COMMAND

        App Help String Line 1.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ cmd1      Cmd1 help string.                                        │
        │ cmd2      Cmd2 help string.                                        │
        │ meta-cmd  Meta cmd help string.                                    │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Admin ────────────────────────────────────────────────────────────╮
        │ --help  Display this message and exit.                             │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Session Parameters ───────────────────────────────────────────────╮
        │ *  --hostname  Hostname to connect to. [required]                  │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_print_commands_sort_key(app, console):
    @app.command  # No user-specified sort_key; will go LAST (but before commands starting with --).
    def alice():
        pass

    @app.command
    def bob():
        pass

    app["bob"].sort_key = 2

    @app.command(sort_key=1)  # Since 1 < 2 (from bob), should go first
    def charlie():
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()

    expected = dedent(
        """\
        Usage: app COMMAND

        App Help String Line 1.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ charlie                                                            │
        │ bob                                                                │
        │ alice                                                              │
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_print_commands_sort_key_generator(app, console):
    """Test that App.sort_key accepts and processes generators."""

    def sort_key_gen():
        yield 2

    @app.command(sort_key=(x for x in [1]))  # Generator expression in constructor
    def alice():
        pass

    @app.command
    def bob():
        pass

    # Test setting via property setter with generator function
    app["bob"].sort_key = sort_key_gen()

    @app.command(sort_key=3)
    def charlie():
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()

    # Check that the commands are sorted correctly (alice=1, bob=2, charlie=3)
    assert "│ alice" in actual
    assert "│ bob" in actual
    assert "│ charlie" in actual

    # Verify the order by checking their positions
    alice_pos = actual.index("alice")
    bob_pos = actual.index("bob")
    charlie_pos = actual.index("charlie")

    assert alice_pos < bob_pos < charlie_pos, (
        f"Commands not in expected order. Positions: alice={alice_pos}, bob={bob_pos}, charlie={charlie_pos}"
    )


def test_help_print_commands_plus_meta_short(app, console):
    app.help = None

    @app.command(help="Cmd1 help string.")
    def cmd1():
        pass

    app.meta.group_arguments = "Session Arguments"
    app.meta.group_parameters = "Session Parameters"

    @app.meta.command(help="Meta cmd help string.")
    def meta_cmd(a: int):
        """

        Parameters
        ----------
        a
            Some value.
        """
        pass

    # Otherwise it will use the default meta
    app["meta-cmd"].group_parameters = app.group_parameters

    @app.command(help="Cmd2 help string.")
    def cmd2():
        pass

    @app.meta.default
    def main(
        *tokens: str,
        hostname: Annotated[str, Parameter(name=["--hostname", "-n"], help="Hostname to connect to.")],
    ):
        """App Help String Line 1 from meta."""
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app COMMAND

        App Help String Line 1 from meta.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ cmd1       Cmd1 help string.                                       │
        │ cmd2       Cmd2 help string.                                       │
        │ meta-cmd   Meta cmd help string.                                   │
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Session Arguments ────────────────────────────────────────────────╮
        │ TOKENS                                                             │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Session Parameters ───────────────────────────────────────────────╮
        │ *  --hostname -n  Hostname to connect to. [required]               │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected

    # Add in a default root app.
    @app.default
    def root_default_cmd(rdp):
        """Root Default Command Short Description.

        Parameters
        ----------
        rdp:
            RDP description.
        """
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app COMMAND RDP

        Root Default Command Short Description.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ cmd1       Cmd1 help string.                                       │
        │ cmd2       Cmd2 help string.                                       │
        │ meta-cmd   Meta cmd help string.                                   │
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  RDP --rdp  RDP description. [required]                          │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Session Arguments ────────────────────────────────────────────────╮
        │ TOKENS                                                             │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Session Parameters ───────────────────────────────────────────────╮
        │ *  --hostname -n  Hostname to connect to. [required]               │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected

    # Test that the meta command help parsing is correct.
    with console.capture() as capture:
        app.help_print(["meta-cmd"], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app meta-cmd A

        Meta cmd help string.

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  A --a  Some value. [required]                                   │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_restructuredtext(app, console, normalize_trailing_whitespace):
    description = dedent(
        """\
        This is a long sentence that
        is spread across
        three lines.

        This is a new paragraph.
        This is another sentence of that paragraph.
        `This is a hyperlink. <https://cyclopts.readthedocs.io>`_

        The following are bulletpoints:

        * bulletpoint 1
        * bulletpoint 2
        """
    )
    app = App(help=description, help_format="rst")

    @app.command
    def foo(bar):
        """This is **bold**."""

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()

    expected = dedent(
        """\
        Usage: test_help COMMAND

        This is a long sentence that is spread across three lines.

        This is a new paragraph. This is another sentence of that paragraph.
        This is a hyperlink.

        The following are bulletpoints:

         • bulletpoint 1
         • bulletpoint 2

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ foo        This is bold.                                           │
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    # Rich sticks a bunch of trailing spaces on lines.
    assert normalize_trailing_whitespace(actual) == expected


def test_help_markdown(app, console, normalize_trailing_whitespace):
    description = dedent(
        """\
        This is a long sentence that
        is spread across
        three lines.

        This is a new paragraph.
        This is another sentence of that paragraph.
        [This is a hyperlink.](https://cyclopts.readthedocs.io)

        The following are bulletpoints:

        * bulletpoint 1
        * bulletpoint 2
        """
    )
    app = App(help=description, help_format="markdown")

    @app.command
    def foo(bar):
        """This is **bold**."""

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()

    expected = dedent(
        """\
        Usage: test_help COMMAND

        This is a long sentence that is spread across three lines.

        This is a new paragraph. This is another sentence of that paragraph.
        This is a hyperlink.

        The following are bulletpoints:

         • bulletpoint 1
         • bulletpoint 2

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ foo        This is bold.                                           │
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    # Rich sticks a bunch of trailing spaces on lines.
    assert normalize_trailing_whitespace(actual) == expected


def test_help_rich(app, console, normalize_trailing_whitespace):
    """Newlines actually get interpreted with rich."""
    description = dedent(
        """\
        This is a short-description that
        is spread across
        three lines (against PEP0257).

        This is the first sentence of the long-description.
        This is another sentence of that paragraph.
        [red]This text is red.[/red]
        """
    )
    app = App(help=description, help_format="rich")

    @app.command
    def foo(bar):
        """This is [italic]italic[/italic]."""

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()

    expected = dedent(
        """\
        Usage: test_help COMMAND

        This is a short-description that is spread across three lines (against
        PEP0257).

        This is the first sentence of the long-description.
        This is another sentence of that paragraph.
        This text is red.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ foo        This is italic.                                         │
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_help_plaintext(app, console):
    """Tests that plaintext documents don't get interpreted otherwise."""
    description = dedent(
        """\
        This is the short description.

        This is a long sentence that
        is spread across
        three lines.

        This is a new paragraph.
        This is another sentence of that paragraph.
        [red]This text is red.[/red]

        These are bulletpoints:

        * point 1
        * point 2
        """
    )
    app = App(help=description, help_format="plaintext")

    @app.command
    def foo(bar):
        """This is [italic]italic[/italic]."""

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()

    expected = dedent(
        """\
        Usage: test_help COMMAND

        This is the short description.

        This is a long sentence that
        is spread across
        three lines.

        This is a new paragraph.
        This is another sentence of that paragraph.
        [red]This text is red.[/red]

        These are bulletpoints:

        * point 1
        * point 2

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ foo        This is [italic]italic[/italic].                        │
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_help_consistent_formatting(app, console):
    """Checks to make sure short-descriptions and full-descriptions
    are rendered using the same formatter.

    https://github.com/BrianPugh/cyclopts/issues/113
    """
    app.help_format = "markdown"

    @app.command
    def cmd():
        """[bold]Short description[/bold]."""

    with console.capture() as capture:
        app.help_print([], console=console)

    actual_help = capture.get()

    # Hack to extract out the short_description from the help-page
    actual_help = next(x for x in actual_help.split("\n") if "Short description" in x)
    actual_help = actual_help[5:-1].strip()

    with console.capture() as capture:
        app.help_print(["cmd"], console=console)

    # Hack to extract out the short_description from the help-page
    actual_cmd_help = capture.get()
    actual_cmd_help = next(x for x in actual_cmd_help.split("\n") if "Short description" in x)
    actual_cmd_help = actual_cmd_help.strip()

    assert actual_help == actual_cmd_help


def test_help_help_on_error(app, console):
    app.help = "This is the App's Help."
    app.help_on_error = True

    @app.command
    def foo(count: int):
        """This is Foo's Help."""
        pass

    with console.capture() as capture, pytest.raises(CoercionError):
        app(["foo", "bar"], error_console=console, exit_on_error=False)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app foo COUNT

        This is Foo's Help.

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  COUNT --count  [required]                                       │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Invalid value for "COUNT": unable to convert "bar" into int.       │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_issue_373_help_space_with_meta_app(app, console):
    @app.default
    def default(value: str):
        print(f"{value=}")

    @app.meta.default
    def meta(
        *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
        meta_value: int = 3,
    ):
        app(tokens)

    with console.capture() as capture:
        app("--help", console=console, exit_on_error=False)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app VALUE

        App Help String Line 1.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  VALUE --value  [required]                                       │
        │    --meta-value   [default: 3]                                     │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_format_plain_formatter(console):
    """Test that PlainFormatter produces correct plain text output."""
    app = App(
        name="test_app",
        help="Test application for PlainFormatter",
        help_formatter=PlainFormatter(),
    )

    @app.command
    def cmd1(arg: str = "default"):
        """First test command."""
        print(f"cmd1 with {arg}")

    @app.command
    def cmd2(required: int, optional: bool = False):
        """Second test command."""
        print(f"cmd2 with {required} and {optional}")

    @app.default
    def main(verbose: bool = False):
        """Main function with a parameter."""
        print(f"verbose={verbose}")

    # Capture the help output
    with console.capture() as capture:
        try:
            app(["--help"], console=console)
        except SystemExit:
            # Help normally exits, which is expected
            pass

    actual = capture.get()

    expected = dedent(
        """\
        Usage: test_app COMMAND [ARGS]

        Test application for PlainFormatter

        Commands:
          cmd1: First test command.
          cmd2: Second test command.
          --help, -h: Display this message and exit.
          --version: Display application version.

        Parameters:
          VERBOSE, --verbose, --no-verbose: [default: False]

        """
    )
    assert actual == expected


def test_help_format_group_parameters_sphinx_only_directives(capture_format_group_parameters):
    """Test parameters with only directives and no other text."""

    def cmd(foo: str):
        """
        Command with directive-only description.

        Parameters
        ----------
        foo: str
            .. versionadded:: 1.0
        """

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  FOO --foo  [Added in v1.0] [required]                           │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_sphinx_nested_indentation(capture_format_group_parameters):
    """Test directives with multi-level indented content."""

    def cmd(foo: str):
        """
        Command with nested indentation in directive.

        Parameters
        ----------
        foo: str
            Foo parameter

            .. note::
                This is a long note
                that spans multiple lines
                with consistent indentation
        """

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  FOO --foo  Foo parameter                                        │
        │                                                                    │
        │               Note: This is a long note that spans multiple lines  │
        │               with consistent indentation [required]               │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_sphinx_inline_directive_content(capture_format_group_parameters):
    """Test directive with inline content on same line."""

    def cmd(foo: str):
        """
        Command with inline directive content.

        Parameters
        ----------
        foo: str
            Foo parameter

            .. note:: Inline note content
        """

    actual = capture_format_group_parameters(cmd)
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  FOO --foo  Foo parameter                                        │
        │                                                                    │
        │               Note: Inline note content [required]                 │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_flag_after_end_of_options_delimiter(app):
    """Help flags after '--' should not trigger help display."""

    @app.default
    def main(*args: str):
        """Main function that accepts variadic arguments."""
        return args

    result = app(["--", "--help"])
    assert result == ("--help",)

    result = app(["foo", "--", "--help", "-h"])
    assert result == ("foo", "--help", "-h")


def test_help_epilogue_basic(app, console):
    """Test basic epilogue rendering."""
    app.help_epilogue = "This is an epilogue."
    with console.capture() as capture:
        app([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app

        App Help String Line 1.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯

        This is an epilogue.
        """
    )
    assert actual == expected


def test_help_epilogue_multiline(app, console):
    """Test epilogue with multiple lines using markdown double newlines."""
    app.help_epilogue = "Line 1\n\nLine 2\n\nLine 3"
    with console.capture() as capture:
        app([], console=console)

    actual = capture.get()
    # With markdown (default), double newlines create separate paragraphs
    assert "Line 1" in actual
    assert "Line 2" in actual
    assert "Line 3" in actual


def test_help_epilogue_none(app, console):
    """Test that None epilogue doesn't add extra lines."""
    app.help_epilogue = None
    with console.capture() as capture:
        app([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app

        App Help String Line 1.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_epilogue_empty_string(app, console):
    """Test that empty string epilogue doesn't render."""
    app.help_epilogue = ""
    with console.capture() as capture:
        app([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app

        App Help String Line 1.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_epilogue_markdown(app, console):
    """Test epilogue with markdown formatting."""
    app.help_epilogue = "**Version 1.0.0**\n\nFor more info, visit *https://example.com*"
    app.help_format = "markdown"
    with console.capture() as capture:
        app([], console=console)

    actual = capture.get()
    assert "Version 1.0.0" in actual
    assert "https://example.com" in actual


def test_help_epilogue_subcommand(app, console):
    """Test that subcommands can have their own epilogue."""
    subapp = App(
        name="sub",
        help="Subcommand help.",
        help_epilogue="Subcommand epilogue.",
    )
    app.command(subapp)

    with console.capture() as capture:
        app(["sub"], console=console)

    actual = capture.get()
    assert "Subcommand epilogue." in actual
    assert actual.endswith("Subcommand epilogue.\n")


def test_help_epilogue_with_parameters(app, console):
    """Test epilogue with parameters in help output."""

    @app.default
    def main(verbose: bool = False, count: int = 1):
        """Main function."""
        pass

    app.help_epilogue = "Footer text here."

    with console.capture() as capture:
        app(["--help"], console=console)

    actual = capture.get()
    assert "verbose" in actual.lower()
    assert "count" in actual.lower()
    assert "Footer text here." in actual
    # Note: With parameters, the epilogue should still appear at the end
    assert "Footer text here." in actual


def test_help_epilogue_inheritance(console):
    """Test that epilogue inherits from parent to child (like help_format)."""
    parent = App(
        name="parent",
        help="Parent help.",
        help_epilogue="Parent epilogue.",
        result_action="return_value",
    )

    child = App(
        name="child",
        help="Child help.",
        # No help_epilogue - should inherit parent's epilogue
    )

    parent.command(child)

    # Parent should show its epilogue
    with console.capture() as capture:
        parent(["--help"], console=console)

    actual = capture.get()
    assert "Parent epilogue." in actual

    # Child should inherit and show parent's epilogue
    with console.capture() as capture:
        parent(["child", "--help"], console=console)

    actual = capture.get()
    assert "Parent epilogue." in actual
    assert "Child help." in actual


def test_help_epilogue_override(console):
    """Test that child can override parent's epilogue."""
    parent = App(
        name="parent",
        help="Parent help.",
        help_epilogue="Parent epilogue.",
        result_action="return_value",
    )

    child = App(
        name="child",
        help="Child help.",
        help_epilogue="Child epilogue (overrides parent).",
    )

    parent.command(child)

    # Parent shows its epilogue
    with console.capture() as capture:
        parent(["--help"], console=console)

    actual = capture.get()
    assert "Parent epilogue." in actual
    assert "Child epilogue" not in actual

    # Child shows its own epilogue (not parent's)
    with console.capture() as capture:
        parent(["child", "--help"], console=console)

    actual = capture.get()
    assert "Child epilogue (overrides parent)." in actual
    assert "Parent epilogue." not in actual
