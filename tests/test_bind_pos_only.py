import pytest

from cyclopts import MissingArgumentError, UnknownOptionError


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1 2 3 4 5",
    ],
)
def test_star_args(app, cmd_str, assert_parse_args):
    @app.command
    def foo(a: int, b: int, *args: int):
        pass

    assert_parse_args(foo, cmd_str, 1, 2, 3, 4, 5)


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1 2 3",
    ],
)
def test_pos_only(app, cmd_str, assert_parse_args):
    @app.command
    def foo(a: int, b: int, c: int, /):
        pass

    assert_parse_args(foo, cmd_str, 1, 2, 3)


@pytest.mark.parametrize(
    "cmd_str_e",
    [
        ("foo 1 2 --c=3", UnknownOptionError),  # Unknown option "--c"
    ],
)
def test_pos_only_exceptions(app, cmd_str_e):
    cmd_str, e = cmd_str_e

    @app.command
    def foo(a: int, b: int, c: int, /):
        pass

    with pytest.raises(e):
        app.parse_args(cmd_str, print_error=False, exit_on_error=False)


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo 1 2 3 4",
        "foo 1 2 3 --d 4",
        "foo 1 2 --d=4 3",
    ],
)
def test_pos_only_extended(app, cmd_str, assert_parse_args):
    @app.command
    def foo(a: int, b: int, c: int, /, d: int):
        pass

    assert_parse_args(foo, cmd_str, 1, 2, 3, 4)


@pytest.mark.parametrize(
    "cmd_str_e",
    [
        ("foo 1 2 3", MissingArgumentError),
        ("foo 1 2", MissingArgumentError),
    ],
)
def test_pos_only_extended_exceptions(app, cmd_str_e):
    cmd_str, e = cmd_str_e

    @app.command
    def foo(a: int, b: int, c: int, /, d: int):
        pass

    with pytest.raises(e):
        app.parse_args(cmd_str, print_error=False, exit_on_error=False)


@pytest.mark.parametrize(
    "cmd_str",
    [
        "foo a 2 3 4",
        "foo a 2 3 --d 4",
        "foo a 2 --d=4 3",
    ],
)
def test_pos_only_extended_str_type(app, cmd_str, assert_parse_args):
    @app.command
    def foo(a: "str", b: "int", c: int, /, d: "int"):
        pass

    assert_parse_args(foo, cmd_str, "a", 2, 3, 4)
