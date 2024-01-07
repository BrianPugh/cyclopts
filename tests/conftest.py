import inspect

import pytest
from rich.console import Console

import cyclopts
from cyclopts import App, Group, Parameter


@pytest.fixture
def app():
    return cyclopts.App()


@pytest.fixture
def console():
    return Console(width=70, force_terminal=True, highlight=False, color_system=None, legacy_windows=False)


@pytest.fixture
def default_function_groups():
    return (Parameter(), Group("Arguments"), Group("Parameters"))


@pytest.fixture
def assert_parse_args(app):
    def inner(f, cmd: str, *args, **kwargs):
        signature = inspect.signature(f)
        expected_bind = signature.bind(*args, **kwargs)
        actual_command, actual_bind = app.parse_args(cmd)
        assert actual_command == f
        assert actual_bind == expected_bind

    return inner
