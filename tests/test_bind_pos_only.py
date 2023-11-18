import inspect

import pytest

from cyclopts import CoercionError, MissingArgumentError
from cyclopts.exceptions import UnknownKeywordError


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1 2 3 4 5",
        "foo --a=1 --b=2 3 4 5",
        "foo 3 4 5 --b=2 --a=1",
    ],
)
def test_star_args(app, cmd_str):
    @app.command
    def foo(a: int, b: int, *args: int):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(1, 2, 3, 4, 5)

    actual_command, actual_bind = app.parse_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1 2 3",
    ],
)
def test_pos_only(app, cmd_str):
    @app.command
    def foo(a: int, b: int, c: int, /):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(1, 2, 3)

    actual_command, actual_bind = app.parse_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind


@pytest.mark.parametrize(
    "cmd_str_e",
    [
        ("foo 1 2 --c=3", UnknownKeywordError),
    ],
)
def test_pos_only_exceptions(app, cmd_str_e):
    cmd_str, e = cmd_str_e

    @app.command
    def foo(a: int, b: int, c: int, /):
        pass

    with pytest.raises(e):
        app.parse_args(cmd_str)


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1 2 3 4",
        "foo 1 2 3 --d 4",
        "foo 1 2 --d=4 3",
    ],
)
def test_pos_only_extended(app, cmd_str):
    @app.command
    def foo(a: int, b: int, c: int, /, d: int):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(1, 2, 3, 4)

    actual_command, actual_bind = app.parse_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind


@pytest.mark.parametrize(
    "cmd_str_e",
    [
        ("foo 1 2 3", MissingArgumentError),
    ],
)
def test_pos_only_extended_exceptions(app, cmd_str_e):
    cmd_str, e = cmd_str_e

    @app.command
    def foo(a: int, b: int, c: int, /, d: int):
        pass

    with pytest.raises(e):
        app.parse_args(cmd_str)
