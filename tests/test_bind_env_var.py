from typing import Annotated

import pytest

from cyclopts import MissingArgumentError, Parameter


def test_env_var_unset_use_signature_default(app, assert_parse_args, monkeypatch):
    @app.default
    def foo(bar: Annotated[int, Parameter(env_var="BAR")] = 123):
        pass

    monkeypatch.delenv("BAR", raising=False)
    assert_parse_args(foo, "")


def test_env_var_set_use_env_var(app, assert_parse_args, monkeypatch):
    @app.default
    def foo(bar: Annotated[int, Parameter(env_var="BAR")] = 123):
        pass

    monkeypatch.setenv("BAR", "456")
    assert_parse_args(foo, "", 456)


def test_env_var_set_use_env_var_no_default(app, assert_parse_args, monkeypatch):
    @app.default
    def foo(bar: Annotated[int, Parameter(env_var="BAR")]):
        pass

    monkeypatch.setenv("BAR", "456")
    assert_parse_args(foo, "", 456)

    monkeypatch.delenv("BAR")
    with pytest.raises(MissingArgumentError):
        app.parse_args([], exit_on_error=False)


def test_env_var_list_set_use_env_var(app, assert_parse_args, monkeypatch):
    @app.default
    def foo(bar: Annotated[int, Parameter(env_var=["BAR", "BAZ"])] = 123):
        pass

    monkeypatch.setenv("BAR", "456")

    assert_parse_args(foo, [], 456)


def test_env_var_unset_list_use_signature_default(app, assert_parse_args, monkeypatch):
    @app.default
    def foo(bar: Annotated[int, Parameter(env_var=["BAR", "BAZ"])] = 123):
        pass

    monkeypatch.delenv("BAR", raising=False)
    monkeypatch.delenv("BAZ", raising=False)

    assert_parse_args(foo, [])


def test_env_var_list_value_whitespace_split(app, assert_parse_args, monkeypatch):
    """An iterable-typed ``Parameter(env_var=...)`` value is split by ``env_var_split``.

    ``Parameter.env_var_split`` is documented as the function that "splits up the
    read-in ``Parameter.env_var`` value"; its default splits iterables on
    whitespace.  Regression: the env-sourcing path appended the raw value as a
    single token without splitting, so ``list[int]`` from ``"1 2 3"`` raised a
    CoercionError instead of yielding ``[1, 2, 3]``.
    """

    @app.default
    def foo(bar: Annotated[list[int], Parameter(env_var="BAR")] = []):  # noqa: B006
        pass

    monkeypatch.setenv("BAR", "1 2 3")
    assert_parse_args(foo, [], [1, 2, 3])


def test_env_var_tuple_value_whitespace_split(app, assert_parse_args, monkeypatch):
    """A multi-token (``tuple[int, int]``) env value is whitespace-split into elements."""

    @app.default
    def foo(bar: Annotated[tuple[int, int], Parameter(env_var="BAR")] = (0, 0)):
        pass

    monkeypatch.setenv("BAR", "5 6")
    assert_parse_args(foo, [], (5, 6))


def test_env_var_path_list_value_pathsep_split(app, assert_parse_args, monkeypatch, mocker):
    """A ``list[Path]`` env value is split on ``os.pathsep`` (mirrors PATH-style vars)."""
    from pathlib import Path

    mocker.patch("cyclopts._env_var.os.pathsep", ":")

    @app.default
    def foo(bar: Annotated[list[Path], Parameter(env_var="BAR")] = []):  # noqa: B006
        pass

    monkeypatch.setenv("BAR", "/a/b:/c/d")
    assert_parse_args(foo, [], [Path("/a/b"), Path("/c/d")])
