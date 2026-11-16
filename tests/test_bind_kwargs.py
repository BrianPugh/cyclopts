from datetime import timedelta
from typing import Annotated

import pytest

from cyclopts import Parameter
from cyclopts.exceptions import UnusedCliTokensError


def test_kwargs_list_int(app, assert_parse_args):
    @app.command
    def foo(a: int, **kwargs: list[int]):
        pass

    assert_parse_args(foo, "foo 1 --bar=2 --baz=4 --bar 3", 1, bar=[2, 3], baz=[4])


def test_kwargs_int(app, assert_parse_args):
    @app.command
    def foo(a: int, **kwargs: int):
        pass

    assert_parse_args(foo, "foo 1 --bar=2 --baz 3", 1, bar=2, baz=3)
    assert_parse_args(foo, "foo 1", 1)


def test_args_and_kwargs_int(app, assert_parse_args):
    @app.command
    def foo(a: int, *args: int, **kwargs: int):
        pass

    assert_parse_args(foo, "foo 1 2 3 4 5 --bar=2 --baz 3", 1, 2, 3, 4, 5, bar=2, baz=3)
    assert_parse_args(foo, "foo 1", 1)


@pytest.mark.parametrize(
    "cmd, args, kwargs",
    [
        ("-5 -6", (-5, -6), {}),
        ("-1 2", (-1, 2), {}),
        ("-1", (-1,), {}),
        ("-1.5 -1e3 -.5", (-1.5, -1000.0, -0.5), {}),
        ("1 --bar a -2", (1, -2), {"bar": "a"}),
        ("-5 --bar -6", (-5,), {"bar": "-6"}),
        # A hyphenated non-number is still a keyword.
        ("-5 -b a", (-5,), {"b": "a"}),
        ("--5 a", (), {"5": "a"}),
        ("-5=a", (), {"5": "a"}),
    ],
)
def test_kwargs_do_not_capture_negative_numbers(app, assert_parse_args, cmd, args, kwargs):
    """https://github.com/BrianPugh/cyclopts/issues/1068"""

    @app.default
    def foo(*args: float, **kwargs: str):
        pass

    assert_parse_args(foo, cmd, *args, **kwargs)


def test_kwargs_do_not_capture_negative_slice(app, assert_parse_args):
    @app.default
    def foo(a: slice, /, **kwargs: str):
        pass

    assert_parse_args(foo, "-3:-1 --bar baz", slice(-3, -1), bar="baz")


@pytest.mark.parametrize(
    "cmd, args, kwargs",
    [
        ("-1h30m", (timedelta(hours=-1, minutes=-30),), {}),
        ("-1h --bar baz -2d", (timedelta(hours=-1), timedelta(days=-2)), {"bar": "baz"}),
    ],
)
def test_kwargs_do_not_capture_negative_durations(app, assert_parse_args, cmd, args, kwargs):
    @app.default
    def foo(*args: timedelta, **kwargs: str):
        pass

    assert_parse_args(foo, cmd, *args, **kwargs)


def test_meta_child_kwargs_do_not_capture_negative_durations(app):
    @app.default
    def foo(*args: timedelta, **kwargs: str):
        return args, kwargs

    @app.meta.default
    def meta(
        *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
        verbose: Annotated[bool, Parameter(name="-v")] = False,
    ):
        return app(tokens, result_action="return_value"), verbose

    expected = (((timedelta(hours=-1),), {"bar": "baz"}), True)
    assert app.meta("-1h --bar baz -v", result_action="return_value") == expected


def test_kwargs_capture_duration_shaped_key_without_timedelta_positional(app, assert_parse_args):
    @app.default
    def foo(*args: str, **kwargs: str):
        pass

    assert_parse_args(foo, "-1h baz", **{"1h": "baz"})


def test_kwargs_explicit_numeric_option_still_matches(app, assert_parse_args):
    @app.default
    def foo(*args: int, one: Annotated[bool, Parameter(name="-1")] = False, **kwargs: str):
        pass

    assert_parse_args(foo, "-1 -2", -2, one=True)


def test_kwargs_negative_number_without_positional_is_unused(app):
    @app.default
    def foo(**kwargs: str):
        pass

    with pytest.raises(UnusedCliTokensError):
        app("-5 a", exit_on_error=False)


def test_meta_kwargs_do_not_capture_negative_numbers(app):
    @app.default
    def foo(*args: int):
        return args

    @app.meta.default
    def meta(*tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)], **kwargs: str):
        return app(tokens, result_action="return_value"), kwargs

    assert app.meta("-5 --bar baz -6", result_action="return_value") == ((-5, -6), {"bar": "baz"})
