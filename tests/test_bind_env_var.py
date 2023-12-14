import inspect
import os

from typing_extensions import Annotated

from cyclopts import Parameter


def test_env_var_unset_use_signature_default(app):
    @app.default
    def foo(bar: Annotated[int, Parameter(env_var="BAR")] = 123):
        pass

    os.environ.pop("BAR", None)

    signature = inspect.signature(foo)
    expected_bind = signature.bind()

    actual_command, actual_bind = app.parse_args([])
    assert actual_command == foo
    assert actual_bind == expected_bind


def test_env_var_set_use_env_var(app):
    @app.default
    def foo(bar: Annotated[int, Parameter(env_var="BAR")] = 123):
        pass

    os.environ["BAR"] = "456"

    signature = inspect.signature(foo)
    expected_bind = signature.bind(456)

    actual_command, actual_bind = app.parse_args([])
    assert actual_command == foo
    assert actual_bind == expected_bind


def test_env_var_list_set_use_env_var(app):
    @app.default
    def foo(bar: Annotated[int, Parameter(env_var=["BAR", "BAZ"])] = 123):
        pass

    os.environ.pop("BAR", None)
    os.environ["BAZ"] = "456"

    signature = inspect.signature(foo)
    expected_bind = signature.bind(456)

    actual_command, actual_bind = app.parse_args([])
    assert actual_command == foo
    assert actual_bind == expected_bind


def test_env_var_unset_list_use_signature_default(app):
    @app.default
    def foo(bar: Annotated[int, Parameter(env_var=["BAR", "BAZ"])] = 123):
        pass

    os.environ.pop("BAR", None)
    os.environ.pop("BAZ", None)

    signature = inspect.signature(foo)
    expected_bind = signature.bind()

    actual_command, actual_bind = app.parse_args([])
    assert actual_command == foo
    assert actual_bind == expected_bind
