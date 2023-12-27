import inspect
import sys
from typing import Any, Optional

import pytest

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated

from cyclopts import Parameter
from cyclopts.exceptions import CoercionError, MissingArgumentError, RepeatArgumentError, UnusedCliTokensError


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
def test_basic_1(app, cmd_str):
    @app.command
    def foo(a: int, b: int, c: int):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(1, 2, 3)

    actual_command, actual_bind = app.parse_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1 2 3 --d 10 --some-flag",
        "foo --some-flag 1 --b=2 3 --d 10",
        "foo 1 2 --some-flag 3 --d 10",
    ],
)
def test_basic_2(app, cmd_str):
    @app.command
    def foo(a: int, b: int, c: int, d: int = 5, some_flag: bool = False):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(1, 2, 3, d=10, some_flag=True)

    actual_command, actual_bind = app.parse_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind


def test_command_rename(app):
    @app.command(name="bar")
    def foo():
        pass

    actual_command, _ = app.parse_args("bar")
    assert actual_command == foo


def test_command_multiple_alias(app):
    @app.command(name=["bar", "baz"])
    def foo():
        pass

    actual_command, _ = app.parse_args("bar")
    assert actual_command == foo

    actual_command, _ = app.parse_args("baz")
    assert actual_command == foo


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo --age 10",
        "foo --duration 10",
        "foo -a 10",
    ],
)
def test_multiple_names(app, cmd_str):
    @app.command
    def foo(age: Annotated[int, Parameter(name=["--age", "--duration", "-a"])]):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(age=10)

    actual_command, actual_bind = app.parse_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1",
        "foo --a=1",
        "foo --a 1",
    ],
)
@pytest.mark.parametrize("annotated", [False, True])
def test_optional_nonrequired_implicit_coercion(app, cmd_str, annotated):
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

    signature = inspect.signature(foo)
    expected_bind = signature.bind(1)

    actual_command, actual_bind = app.parse_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind
    assert isinstance(actual_bind.args[0], int)


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
def test_bind_any_hint(app, cmd_str, annotated):
    """The ``Any`` type hint should be treated as a ``str``."""
    if annotated:

        @app.command
        def foo(a: Annotated[Any, Parameter(help="help for a")] = None):
            pass

    else:

        @app.command
        def foo(a: Any = None):
            pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind("1")

    actual_command, actual_bind = app.parse_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind


@pytest.mark.parametrize(
    "cmd_str",
    [
        "1",
        "0b1",
        "0x01",
    ],
)
def test_bind_int_advanced(app, cmd_str):
    @app.default
    def foo(a: int):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(1)

    actual_command, actual_bind = app.parse_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind


def test_bind_int_advanced_coercion_error(app):
    @app.default
    def foo(a: int):
        pass

    with pytest.raises(CoercionError):
        app.parse_args("foo", exit_on_error=False)


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
