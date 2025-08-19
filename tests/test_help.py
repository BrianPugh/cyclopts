import sys
from dataclasses import dataclass
from enum import Enum
from functools import partial
from textwrap import dedent
from typing import Annotated, List, Literal, Optional, Sequence, Set, Tuple, Union

import pytest

from cyclopts import App, Group, Parameter
from cyclopts.argument import ArgumentCollection
from cyclopts.exceptions import CoercionError, MissingArgumentError
from cyclopts.help import (
    HelpPanel,
    create_parameter_help_panel,
    format_command_entries,
    format_usage,
)


@pytest.fixture
def app():
    return App(
        name="app",
        help="App Help String Line 1.",
    )


def test_empty_help_panel_rich_silent(console):
    help_panel = HelpPanel(format="command", title="test")

    with console.capture() as capture:
        console.print(help_panel)

    actual = capture.get()
    assert actual == ""


def test_help_mutable_default(app):
    """Ensures it doesn't crash; see issue #215."""

    @app.default
    def main(users: List[str] = ["a", "b"]) -> None:  # noqa: B006
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
    app = App(name="app", help="App Help String Line 1.")
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
    panel.entries.extend(format_command_entries((app["foo"],), format="restructuredtext"))
    with console.capture() as capture:
        console.print(panel)

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
    panel.entries.extend(format_command_entries((app["foo"],), format="restructuredtext"))
    with console.capture() as capture:
        console.print(panel)

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
    panel.entries.extend(format_command_entries((app["foo"],), format="restructuredtext"))
    with console.capture() as capture:
        console.print(panel)

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
    panel.entries.extend(format_command_entries((app["bar"],), format="restructuredtext"))
    with console.capture() as capture:
        console.print(panel)

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
        Usage: app foo [ARGS] [OPTIONS]

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
        Usage: app [ARGS] [OPTIONS]

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
            console.print(create_parameter_help_panel(group, group_argument_collection, "restructuredtext"))

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
        foo: Annotated[Optional[List[int]], Parameter(help="Docstring for foo.")] = None,
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
        Usage: app [ARGS] [OPTIONS]

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
        Usage: app [ARGS] [OPTIONS]

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
        foo: Annotated[
            Union[int, Literal["fizz", "buzz"], Literal["bar"]], Parameter(help="Docstring for foo.")
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


@pytest.mark.skipif(sys.version_info < (3, 10), reason="Pipe Typing Syntax")
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


@pytest.mark.skipif(sys.version_info < (3, 10), reason="Pipe Typing Syntax")
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
            Optional[list[CompSciProblem]],  # pyright: ignore
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
            Optional[List[CompSciProblem]],
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
            Optional[Sequence[CompSciProblem]],  # pyright: ignore
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
            Optional[Sequence[Literal["build", "deploy"]]],  # pyright: ignore
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
            Optional[set[Literal["build", "deploy"]]],  # pyright: ignore
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


@pytest.mark.skipif(
    sys.version_info < (3, 10), reason="https://peps.python.org/pep-0563/ Postponed Evaluation of Annotations"
)
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
            Optional[Set[Literal["build", "deploy"]]],
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
            Optional[tuple[Literal["build", "deploy"]]],  # pyright: ignore
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
            Tuple[Literal["build", "deploy"]],
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
            Tuple[Literal["build", "deploy"], ...],
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
        Usage: app cmd [ARGS] [OPTIONS]

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
        Usage: app cmd [ARGS] [OPTIONS]

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
        Usage: app cmd [ARGS] [OPTIONS]

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
        Usage: app cmd [ARGS] [OPTIONS]

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
        Usage: app cmd [ARGS] [OPTIONS]

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
        Usage: app cmd [ARGS] [OPTIONS]

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
        Usage: app [ARGS] [OPTIONS]

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
        Usage: app COMMAND [ARGS] [OPTIONS]

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
        Usage: app foo [OPTIONS]

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
        Usage: app COMMAND [ARGS] [OPTIONS]

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
        Usage: app meta-cmd [ARGS] [OPTIONS]

        Meta cmd help string.

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  A --a  Some value. [required]                                   │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_restructuredtext(app, console):
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
    expected = "\n".join(x.strip() for x in expected.split("\n"))
    actual = "\n".join(x.strip() for x in actual.split("\n"))

    assert actual == expected


def test_help_markdown(app, console):
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
    expected = "\n".join(x.strip() for x in expected.split("\n"))
    actual = "\n".join(x.strip() for x in actual.split("\n"))

    assert actual == expected


def test_help_rich(app, console):
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
        app(["foo", "bar"], console=console, exit_on_error=False)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app foo [ARGS] [OPTIONS]

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
        Usage: app [ARGS] [OPTIONS]

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
