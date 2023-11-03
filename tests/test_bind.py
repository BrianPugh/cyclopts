import inspect

import pytest

import cyclopts
from cyclopts import MissingArgumentError
from cyclopts.exceptions import UnknownKeywordError


@pytest.fixture
def app():
    return cyclopts.App()


def test_missing_positional_type(app):
    with pytest.raises(cyclopts.MissingTypeError):

        @app.command
        def foo(a, b, c):
            pass


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1 2 3",
        "foo --a 1 --b 2 --c 3",
        "foo --c 3 1 2",
        "foo --c 3 --b=2 1",
        "foo --c 3 --b=2 --a 1",
        "foo 1 --b=2 3",
    ],
)
def test_basic_1(app, cmd_str):
    @app.command
    def foo(a: int, b: int, c: int):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(1, 2, 3)

    actual_command, actual_bind, unused_args = app.parse_known_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind
    assert unused_args == []


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

    actual_command, actual_bind, unused_args = app.parse_known_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind
    assert unused_args == []


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1 2 3",
    ],
)
def test_basic_pos_only(app, cmd_str):
    @app.command
    def foo(a: int, b: int, c: int, /):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(1, 2, 3)

    actual_command, actual_bind, unused_args = app.parse_known_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind
    assert unused_args == []


@pytest.mark.parametrize(
    "cmd_str_e",
    [
        ("foo 1 2 --c=3", UnknownKeywordError),
    ],
)
def test_basic_pos_only_exceptions(app, cmd_str_e):
    cmd_str, e = cmd_str_e

    @app.command
    def foo(a: int, b: int, c: int, /):
        pass

    with pytest.raises(e):
        app.parse_known_args(cmd_str)


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1 2 3 4",
        "foo 1 2 3 --d 4",
        "foo 1 2 --d=4 3",
    ],
)
def test_basic_pos_only_extended(app, cmd_str):
    @app.command
    def foo(a: int, b: int, c: int, /, d: int):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(1, 2, 3, 4)

    actual_command, actual_bind, unused_args = app.parse_known_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind
    assert unused_args == []


@pytest.mark.parametrize(
    "cmd_str_e",
    [
        ("foo 1 2 3", MissingArgumentError),
    ],
)
def test_basic_pos_only_extended_exceptions(app, cmd_str_e):
    cmd_str, e = cmd_str_e

    @app.command
    def foo(a: int, b: int, c: int, /, d: int):
        pass

    with pytest.raises(e):
        app.parse_known_args(cmd_str)
