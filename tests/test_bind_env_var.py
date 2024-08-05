import sys

import pytest

from cyclopts import MissingArgumentError, Parameter

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated


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
