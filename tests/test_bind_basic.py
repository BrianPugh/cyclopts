import sys
from typing import Annotated, Any, Optional

import pytest

from cyclopts import Parameter
from cyclopts.exceptions import (
    CoercionError,
    InvalidCommandError,
    MissingArgumentError,
    RepeatArgumentError,
    UnusedCliTokensError,
)
from cyclopts.group import Group


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1 --b=2 3",
        "foo 1 2 3",
        "foo --a 1 --b 2 --c 3",
        "foo --c 3 1 2",
        "foo --c 3 --b=2 1",
        "foo --c 3 --b=2 --a 1",
    ],
)
def test_basic_1(app, cmd_str, assert_parse_args):
    @app.command
    def foo(a: int, b: int, c: int):
        pass

    assert_parse_args(foo, cmd_str, 1, 2, 3)


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1 2 3 --d 10 --some-flag",
        "foo --some-flag 1 --b=2 3 --d 10",
        "foo 1 2 --some-flag 3 --d 10",
    ],
)
def test_basic_2(app, cmd_str, assert_parse_args):
    @app.command
    def foo(a: int, b: int, c: int, d: int = 5, some_flag: bool = False):
        pass

    assert_parse_args(foo, cmd_str, 1, 2, 3, d=10, some_flag=True)


def test_command_rename(app, assert_parse_args):
    @app.command(name="bar")
    def foo():
        pass

    assert_parse_args(foo, "bar")


def test_command_delete(app, assert_parse_args):
    @app.command
    def foo():
        pass

    del app["foo"]

    with pytest.raises(InvalidCommandError):
        assert_parse_args(foo, "foo")


def test_command_multiple_alias(app, assert_parse_args):
    @app.command(name=["bar", "baz"])
    def foo():
        pass

    assert_parse_args(foo, "bar")
    assert_parse_args(foo, "baz")


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo --age 10",
        "foo --duration 10",
        "foo -a 10",
    ],
)
def test_multiple_names(app, cmd_str, assert_parse_args):
    @app.command
    def foo(age: Annotated[int, Parameter(name=["--age", "--duration", "-a"])]):
        pass

    assert_parse_args(foo, cmd_str, age=10)


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1",
        "foo --a=1",
        "foo --a 1",
    ],
)
@pytest.mark.parametrize("annotated", [False, True])
def test_optional_nonrequired_implicit_coercion(app, cmd_str, annotated, assert_parse_args):
    """
    For a union without an explicit coercion, the first non-None type annotation
    should be used. In this case, it's ``int``.
    """
    if annotated:

        @app.command
        def foo(a: Annotated[Optional[int], Parameter(help="help for a")] = None):
            pass

    else:

        @app.command
        def foo(a: Optional[int] = None):
            pass

    assert_parse_args(foo, cmd_str, 1)


@pytest.mark.skipif(sys.version_info < (3, 10), reason="Pipe Typing Syntax")
@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1",
        "foo --a=1",
        "foo --a 1",
    ],
)
@pytest.mark.parametrize("annotated", [False, True])
def test_optional_nonrequired_implicit_coercion_python310_syntax(app, cmd_str, annotated, assert_parse_args):
    """
    For a union without an explicit coercion, the first non-None type annotation
    should be used. In this case, it's ``int``.
    """
    if annotated:

        @app.command
        def foo(a: Annotated[int | None, Parameter(help="help for a")] = None):  # pyright: ignore
            pass

    else:

        @app.command
        def foo(a: int | None = None):  # pyright: ignore
            pass

    assert_parse_args(foo, cmd_str, 1)


@pytest.mark.parametrize(
    "cmd_str",
    [
        "--foo val1 --foo val2",
    ],
)
def test_exception_repeat_argument(app, cmd_str):
    @app.default
    def default(foo: str):
        pass

    with pytest.raises(RepeatArgumentError):
        app.parse_args(cmd_str, print_error=False, exit_on_error=False)


@pytest.mark.parametrize(
    "cmd_str",
    [
        "--foo val1 --foo val2",
    ],
)
def test_exception_repeat_argument_kwargs(app, cmd_str):
    @app.default
    def default(**kwargs: str):
        pass

    with pytest.raises(RepeatArgumentError):
        app.parse_args(cmd_str, print_error=False, exit_on_error=False)


def test_exception_unused_token(app):
    @app.default
    def default(foo: str):
        pass

    with pytest.raises(UnusedCliTokensError):
        app.parse_args("foo bar", print_error=False, exit_on_error=False)


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1",
        "foo --a=1",
        "foo --a 1",
    ],
)
@pytest.mark.parametrize("annotated", [False, True])
def test_bind_no_hint_no_default(app, cmd_str, annotated, assert_parse_args):
    """Parameter with no type hint & no default should be treated as a ``str``."""
    if annotated:

        @app.command
        def foo(a: Annotated[Any, Parameter(help="help for a")]):  # pyright: ignore[reportRedeclaration]
            pass

    else:

        @app.command
        def foo(a):  # pyright: ignore[reportRedeclaration]
            pass

    assert_parse_args(foo, cmd_str, "1")


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1",
        "foo --a=1",
        "foo --a 1",
    ],
)
@pytest.mark.parametrize("annotated", [False, True])
def test_bind_no_hint_none_default(app, cmd_str, annotated, assert_parse_args):
    """Parameter with no type hint & ``None`` default should be treated as a ``str``."""
    if annotated:

        @app.command
        def foo(a: Annotated[Any, Parameter(help="help for a")] = None):  # pyright: ignore[reportRedeclaration]
            pass

    else:

        @app.command
        def foo(a=None):  # pyright: ignore[reportRedeclaration]
            pass

    assert_parse_args(foo, cmd_str, "1")


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1",
        "foo --a=1",
        "foo --a 1",
    ],
)
@pytest.mark.parametrize("annotated", [False, True])
def test_bind_no_hint_typed_default(app, cmd_str, annotated, assert_parse_args):
    """Parameter with no type hint & typed default should be treated as a ``type(default)``."""
    if annotated:

        @app.command
        def foo(a: Annotated[Any, Parameter(help="help for a")] = 5):  # pyright: ignore[reportRedeclaration]
            pass

    else:

        @app.command
        def foo(a=5):  # pyright: ignore[reportRedeclaration]
            pass

    assert_parse_args(foo, cmd_str, 1)


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1",
        "foo --a=1",
        "foo --a 1",
    ],
)
@pytest.mark.parametrize("annotated", [False, True])
def test_bind_any_hint(app, cmd_str, annotated, assert_parse_args):
    """The ``Any`` type hint should be treated as a ``str``."""
    if annotated:

        @app.command
        def foo(a: Annotated[Any, Parameter(help="help for a")] = None):
            pass

    else:

        @app.command
        def foo(a: Any = None):
            pass

    assert_parse_args(foo, cmd_str, "1")


@pytest.mark.parametrize(
    "cmd_str",
    [
        "1",
        "0b1",
        "0x01",
        "1.0",
        "0.9",
    ],
)
def test_bind_int_advanced(app, cmd_str, assert_parse_args):
    @app.default
    def foo(a: int):
        pass

    assert_parse_args(foo, cmd_str, 1)


def test_bind_int_advanced_coercion_error(app):
    @app.default
    def foo(a: int):
        pass

    with pytest.raises(CoercionError):
        app.parse_args("foo", exit_on_error=False)


def test_bind_override_app_groups(app):
    g_commands = Group("Custom Commands")
    g_arguments = Group("Custom Arguments")
    g_parameters = Group("Custom Parameters")

    @app.command(group_commands=g_commands, group_arguments=g_arguments, group_parameters=g_parameters)
    def foo():
        pass

    assert app["foo"].group_commands == g_commands
    assert app["foo"].group_arguments == g_arguments
    assert app["foo"].group_parameters == g_parameters


def test_bind_version(app, capsys):
    app.version = "1.2.3"
    actual_command, actual_bind = app.parse_args("--version")
    assert actual_command == app.version_print

    actual_command(*actual_bind.args, **actual_bind.kwargs)
    captured = capsys.readouterr()
    assert captured.out == "1.2.3\n"


def test_bind_version_factory(app, capsys):
    app.version = lambda: "1.2.3"
    actual_command, actual_bind = app.parse_args("--version")
    assert actual_command == app.version_print

    actual_command(*actual_bind.args, **actual_bind.kwargs)
    captured = capsys.readouterr()
    assert captured.out == "1.2.3\n"


@pytest.mark.parametrize(
    "cmd_str_e",
    [
        ("foo 1 2 3", MissingArgumentError),
        ("foo 1 2", MissingArgumentError),
    ],
)
def test_missing_keyword_argument(app, cmd_str_e):
    cmd_str, e = cmd_str_e

    @app.command
    def foo(a: int, b: int, c: int, *, d: int):
        pass

    with pytest.raises(e):
        app.parse_args(cmd_str, print_error=False, exit_on_error=False)
