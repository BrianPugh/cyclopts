import inspect
import os
import sys

import pytest

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated

from cyclopts import MissingArgumentError, Parameter


def test_env_var_unset_use_signature_default(app, assert_parse_args):
    @app.default
    def foo(bar: Annotated[int, Parameter(env_var="BAR")] = 123):
        pass

    os.environ.pop("BAR", None)
    assert_parse_args(foo, "")


def test_env_var_set_use_env_var(app, assert_parse_args):
    @app.default
    def foo(bar: Annotated[int, Parameter(env_var="BAR")] = 123):
        pass

    os.environ["BAR"] = "456"
    assert_parse_args(foo, "", 456)


def test_env_var_set_use_env_var_no_default(app, assert_parse_args):
    @app.default
    def foo(bar: Annotated[int, Parameter(env_var="BAR")]):
        pass

    os.environ["BAR"] = "456"
    assert_parse_args(foo, "", 456)

    os.environ.pop("BAR", None)
    with pytest.raises(MissingArgumentError):
        app.parse_args([], exit_on_error=False)


def test_env_var_list_set_use_env_var(app, assert_parse_args):
    @app.default
    def foo(bar: Annotated[int, Parameter(env_var=["BAR", "BAZ"])] = 123):
        pass

    os.environ.pop("BAR", None)
    os.environ["BAZ"] = "456"

    assert_parse_args(foo, [], 456)


def test_env_var_unset_list_use_signature_default(app, assert_parse_args):
    @app.default
    def foo(bar: Annotated[int, Parameter(env_var=["BAR", "BAZ"])] = 123):
        pass

    os.environ.pop("BAR", None)
    os.environ.pop("BAZ", None)

    assert_parse_args(foo, [])
